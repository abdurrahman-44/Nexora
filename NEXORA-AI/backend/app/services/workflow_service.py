"""NEXORA ERP — Reusable Multi-Level Workflow & Approval Engine."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.models.entities import (
    ApprovalAction,
    ApprovalRequest,
    ApprovalStep,
    ApprovalWorkflow,
    Notification,
    new_uuid,
)
from app.services.accounting_service import quantize_money


def ensure_default_workflow(
    db: Session,
    organization_id: str,
    document_type: str,
) -> ApprovalWorkflow:
    stmt = select(ApprovalWorkflow).where(
        ApprovalWorkflow.organization_id == organization_id,
        ApprovalWorkflow.document_type == document_type,
        ApprovalWorkflow.is_active.is_(True),
    )
    wf = db.execute(stmt).scalar_one_or_none()
    if wf:
        return wf

    wf = ApprovalWorkflow(
        id=new_uuid(),
        organization_id=organization_id,
        name=f"Standard {document_type.replace('_', ' ').title()} Approval Workflow",
        document_type=document_type,
        is_active=True,
    )
    db.add(wf)
    db.flush()

    # Step 1: Department Manager approval for all amounts
    db.add(
        ApprovalStep(
            id=new_uuid(),
            workflow_id=wf.id,
            step_order=1,
            step_name="Department Manager Review",
            min_amount=Decimal("0.00"),
            max_amount=None,
            required_role_code="DEPARTMENT_MANAGER",
            required_permission_code="approvals.act",
            approval_mode="SEQUENTIAL",
        )
    )
    # Step 2: Finance Manager / Executive approval for amounts > LKR 50,000
    db.add(
        ApprovalStep(
            id=new_uuid(),
            workflow_id=wf.id,
            step_order=2,
            step_name="Finance Manager High-Value Authorization (> LKR 50,000)",
            min_amount=Decimal(str(settings.po_dual_approval_threshold_lkr)),
            max_amount=None,
            required_role_code="FINANCE_MANAGER",
            required_permission_code="approvals.act",
            approval_mode="SEQUENTIAL",
        )
    )
    db.flush()
    return wf


def initiate_approval_request(
    db: Session,
    *,
    organization_id: str,
    document_type: str,
    document_id: str,
    document_number: str,
    amount: Decimal | float | str,
    requested_by_id: str,
) -> ApprovalRequest:
    """Create a workflow approval request and compute required approval steps based on LKR threshold."""
    wf = ensure_default_workflow(db, organization_id, document_type)
    amt = quantize_money(amount)
    threshold = quantize_money(settings.po_dual_approval_threshold_lkr)
    total_steps = 2 if amt > threshold and document_type in {"PURCHASE_REQUEST", "PURCHASE_ORDER", "EXPENSE"} else 1

    req = ApprovalRequest(
        id=new_uuid(),
        organization_id=organization_id,
        workflow_id=wf.id,
        document_type=document_type,
        document_id=document_id,
        document_number=document_number,
        amount=amt,
        current_step_order=1,
        total_steps_required=total_steps,
        status="PENDING",
        requested_by_id=requested_by_id,
    )
    db.add(req)
    db.add(
        Notification(
            id=new_uuid(),
            organization_id=organization_id,
            user_id=None,
            title=f"Approval Required: {document_number}",
            message=f"{document_type.replace('_', ' ').title()} {document_number} (LKR {amt:,.2f}) awaits Step 1 approval.",
            category="APPROVAL",
            severity="INFO",
            action_url="/approvals",
        )
    )
    db.flush()
    return req


def process_approval_decision(
    db: Session,
    *,
    organization_id: str,
    approval_request_id: str,
    actor_user_id: str,
    action: str,
    comments: str | None = None,
) -> ApprovalRequest:
    """Process an approval or rejection action, strictly enforcing Separation of Duties."""
    req = db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.id == approval_request_id,
            ApprovalRequest.organization_id == organization_id,
        )
    ).scalar_one_or_none()
    if not req:
        raise NotFoundError("Approval request not found.")
    if req.status not in {"PENDING", "ESCALATED"}:
        raise BusinessRuleError(f"Approval request is already {req.status}.")

    # Separation of Duties invariant: A user must NEVER approve their own restricted transaction
    if req.requested_by_id == actor_user_id and action.upper() == "APPROVE":
        raise ForbiddenError(
            "Separation of Duties violation: You cannot approve a transaction that you initiated.",
            code="SELF_APPROVAL_FORBIDDEN",
        )

    act_upper = action.upper()
    if act_upper not in {"APPROVE", "REJECT", "ESCALATE"}:
        raise BusinessRuleError("Action must be APPROVE, REJECT, or ESCALATE.")

    if act_upper == "REJECT" and not (comments and comments.strip()):
        raise BusinessRuleError("A rejection reason is required when rejecting an approval request.")

    db.add(
        ApprovalAction(
            id=new_uuid(),
            approval_request_id=req.id,
            step_order=req.current_step_order,
            actor_user_id=actor_user_id,
            action=act_upper,
            comments=comments,
        )
    )

    if act_upper == "REJECT":
        req.status = "REJECTED"
    elif act_upper == "ESCALATE":
        req.status = "ESCALATED"
    elif act_upper == "APPROVE":
        if req.current_step_order < req.total_steps_required:
            req.current_step_order += 1
            req.status = "PENDING"
        else:
            req.status = "APPROVED"

    db.flush()
    return req
