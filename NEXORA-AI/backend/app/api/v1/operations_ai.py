"""NEXORA ERP — Projects, Approvals, Executive Analytics, BI Reports, Notifications & AI Engine Router."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    AuthContext,
    get_current_context,
    record_audit_log,
    require_permissions,
)
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.entities import (
    AIInsight,
    AnomalyEvent,
    ApprovalAction,
    ApprovalRequest,
    Customer,
    Department,
    Employee,
    Expense,
    Invoice,
    Milestone,
    Notification,
    Product,
    Project,
    PurchaseOrder,
    StockBalance,
    Supplier,
    Task,
    User,
    new_uuid,
)
from app.services.accounting_service import compute_financial_statements, compute_trial_balance
from app.services.ai_service import (
    handle_copilot_chat,
    run_business_anomaly_detection,
    run_inventory_demand_forecast,
    run_sales_revenue_forecast,
)
from app.services.workflow_service import process_approval_decision

router = APIRouter(tags=["Projects, Workflows, Analytics & AI"])


class ProjectCreateSchema(BaseModel):
    name: str
    description: Optional[str] = None
    budget: float = 2500000.0
    priority: str = "HIGH"
    end_date: Optional[date] = None


class TaskCreateSchema(BaseModel):
    project_id: str
    title: str
    description: Optional[str] = None
    priority: str = "HIGH"
    status: str = "TODO"
    due_date: Optional[date] = None
    estimated_hours: float = 12.0


class TaskStatusUpdateSchema(BaseModel):
    status: str


class WorkflowActionSchema(BaseModel):
    action: str = "APPROVE"
    comments: Optional[str] = None


class ForecastInventoryRequest(BaseModel):
    model_choice: str = "XGBOOST"


class ForecastSalesRequest(BaseModel):
    horizon_months: int = 6


class AnomalyStatusUpdateSchema(BaseModel):
    status: str = "RESOLVED"


class CopilotChatRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None


# ============================================================================
# PROJECTS, MILESTONES & KANBAN TASKS
# ============================================================================

@router.get("/projects")
def list_projects(
    ctx: AuthContext = Depends(require_permissions("projects.view")),
    db: Session = Depends(get_db),
) -> dict:
    projects = list(
        db.execute(
            select(Project)
            .where(Project.organization_id == ctx.organization.id)
            .order_by(Project.project_code)
        ).scalars()
    )
    tasks = list(
        db.execute(
            select(Task)
            .where(Task.organization_id == ctx.organization.id)
            .order_by(Task.task_code)
        ).scalars()
    )
    milestones = list(
        db.execute(
            select(Milestone).where(Milestone.project_id.in_([p.id for p in projects]))
        ).scalars()
    ) if projects else []

    tasks_by_proj: dict[str, list] = {}
    for t in tasks:
        tasks_by_proj.setdefault(t.project_id, []).append(
            {
                "id": t.id,
                "project_id": t.project_id,
                "task_code": t.task_code,
                "title": t.title,
                "description": t.description,
                "status": t.status,
                "priority": t.priority,
                "due_date": t.due_date.isoformat(),
                "estimated_hours": float(t.estimated_hours),
                "logged_hours": float(t.logged_hours),
            }
        )

    ms_by_proj: dict[str, list] = {}
    for m in milestones:
        ms_by_proj.setdefault(m.project_id, []).append(
            {"id": m.id, "title": m.title, "due_date": m.due_date.isoformat(), "status": m.status}
        )

    return {
        "items": [
            {
                "id": p.id,
                "project_code": p.project_code,
                "name": p.name,
                "description": p.description,
                "start_date": p.start_date.isoformat(),
                "end_date": p.end_date.isoformat(),
                "budget": float(p.budget),
                "spent_amount": float(p.spent_amount),
                "budget_utilization_percent": round(
                    (float(p.spent_amount) / float(p.budget) * 100.0) if p.budget > 0 else 0.0, 1
                ),
                "progress_percent": p.progress_percent,
                "status": p.status,
                "priority": p.priority,
                "tasks": tasks_by_proj.get(p.id, []),
                "milestones": ms_by_proj.get(p.id, []),
            }
            for p in projects
        ]
    }


@router.post("/projects", status_code=201)
def create_project(
    payload: ProjectCreateSchema,
    ctx: AuthContext = Depends(require_permissions("projects.manage")),
    db: Session = Depends(get_db),
) -> dict:
    cnt = (
        db.execute(
            select(func.count(Project.id)).where(Project.organization_id == ctx.organization.id)
        ).scalar_one()
        or 0
    )
    prj = Project(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        project_code=f"PRJ-2026-{cnt + 1:02d}",
        name=payload.name,
        description=payload.description,
        start_date=date.today(),
        end_date=payload.end_date or (date.today() + timedelta(days=60)),
        budget=Decimal(str(payload.budget)),
        spent_amount=Decimal("0.00"),
        progress_percent=10,
        status="IN_PROGRESS",
        priority=payload.priority.upper(),
    )
    db.add(prj)
    db.commit()
    return {"id": prj.id, "project_code": prj.project_code, "name": prj.name}


@router.get("/tasks")
def list_tasks(
    ctx: AuthContext = Depends(require_permissions("projects.view")),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.execute(
        select(Task, Project.name, Project.project_code)
        .join(Project, Project.id == Task.project_id)
        .where(Task.organization_id == ctx.organization.id)
        .order_by(Task.created_at.desc())
    ).all()
    return {
        "items": [
            {
                "id": t.id,
                "project_id": t.project_id,
                "project_code": p_code,
                "project_name": p_name,
                "task_code": t.task_code,
                "title": t.title,
                "description": t.description,
                "status": t.status,
                "priority": t.priority,
                "due_date": t.due_date.isoformat(),
                "estimated_hours": float(t.estimated_hours),
                "logged_hours": float(t.logged_hours),
            }
            for t, p_name, p_code in rows
        ]
    }


@router.post("/tasks", status_code=201)
def create_task(
    payload: TaskCreateSchema,
    ctx: AuthContext = Depends(require_permissions("projects.manage")),
    db: Session = Depends(get_db),
) -> dict:
    cnt = (
        db.execute(
            select(func.count(Task.id)).where(Task.organization_id == ctx.organization.id)
        ).scalar_one()
        or 0
    )
    t = Task(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        project_id=payload.project_id,
        task_code=f"TSK-{101 + cnt}",
        title=payload.title,
        description=payload.description,
        status=payload.status.upper(),
        priority=payload.priority.upper(),
        start_date=date.today(),
        due_date=payload.due_date or (date.today() + timedelta(days=14)),
        estimated_hours=Decimal(str(payload.estimated_hours)),
    )
    db.add(t)
    db.commit()
    return {"id": t.id, "task_code": t.task_code, "title": t.title, "status": t.status}


@router.patch("/tasks/{task_id}/status")
def update_task_status(
    task_id: str,
    payload: TaskStatusUpdateSchema,
    ctx: AuthContext = Depends(require_permissions("projects.view")),
    db: Session = Depends(get_db),
) -> dict:
    t = db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.organization_id == ctx.organization.id,
        )
    ).scalar_one_or_none()
    if not t:
        raise NotFoundError("Task not found.")
    t.status = payload.status.upper()
    db.commit()
    return {"id": t.id, "status": t.status}


# ============================================================================
# WORKFLOW & APPROVAL CENTER
# ============================================================================

@router.get("/workflows/approvals")
def list_workflow_approvals(
    ctx: AuthContext = Depends(require_permissions("approvals.view")),
    db: Session = Depends(get_db),
) -> dict:
    reqs = list(
        db.execute(
            select(ApprovalRequest, User.full_name)
            .join(User, User.id == ApprovalRequest.requested_by_id)
            .where(ApprovalRequest.organization_id == ctx.organization.id)
            .order_by(ApprovalRequest.created_at.desc())
        ).all()
    )
    items = []
    for r, req_name in reqs:
        actions = list(
            db.execute(
                select(ApprovalAction, User.full_name)
                .join(User, User.id == ApprovalAction.actor_user_id)
                .where(ApprovalAction.approval_request_id == r.id)
                .order_by(ApprovalAction.acted_at)
            ).all()
        )
        items.append(
            {
                "id": r.id,
                "document_type": r.document_type,
                "document_id": r.document_id,
                "document_number": r.document_number,
                "amount": float(r.amount),
                "current_step_order": r.current_step_order,
                "total_steps_required": r.total_steps_required,
                "status": r.status,
                "requested_by_id": r.requested_by_id,
                "requested_by_name": req_name,
                "can_current_user_approve": r.requested_by_id != ctx.user.id and r.status == "PENDING",
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "history": [
                    {
                        "step_order": a.step_order,
                        "actor_name": act_name,
                        "action": a.action,
                        "comments": a.comments,
                        "acted_at": a.acted_at.isoformat() if a.acted_at else None,
                    }
                    for a, act_name in actions
                ],
            }
        )
    return {"items": items}


@router.post("/workflows/approvals/{approval_id}/act")
def act_on_workflow_approval(
    approval_id: str,
    payload: WorkflowActionSchema,
    ctx: AuthContext = Depends(require_permissions("approvals.act")),
    db: Session = Depends(get_db),
) -> dict:
    req = process_approval_decision(
        db,
        organization_id=ctx.organization.id,
        approval_request_id=approval_id,
        actor_user_id=ctx.user.id,
        action=payload.action,
        comments=payload.comments,
    )

    # Synchronize target document status when workflow reaches terminal state
    if req.document_type == "PURCHASE_ORDER":
        po = db.execute(select(PurchaseOrder).where(PurchaseOrder.id == req.document_id)).scalar_one_or_none()
        if po:
            po.approval_step_completed = req.current_step_order
            if req.status == "APPROVED":
                po.status = "APPROVED"
                po.approved_by_id = ctx.user.id
            elif req.status == "REJECTED":
                po.status = "REJECTED"
                po.rejection_reason = payload.comments

    record_audit_log(
        db,
        ctx=ctx,
        action=f"WORKFLOW_{req.status}",
        entity_type="ApprovalRequest",
        entity_id=req.id,
    )
    db.commit()
    return {
        "id": req.id,
        "document_number": req.document_number,
        "status": req.status,
        "current_step_order": req.current_step_order,
    }


# ============================================================================
# EXECUTIVE DASHBOARD ANALYTICS & BI REPORTS (Database-Derived Only)
# ============================================================================

@router.get("/analytics/dashboard")
def get_executive_dashboard(
    branch_id: Optional[str] = Query(default=None),
    ctx: AuthContext = Depends(require_permissions("dashboard.view")),
    db: Session = Depends(get_db),
) -> dict:
    org_id = ctx.organization.id
    fin = compute_financial_statements(db, org_id)
    pnl = fin["profit_and_loss"]
    bs = fin["balance_sheet"]
    cf = fin["cash_flow"]

    ar_balance = next(
        (a["amount"] for a in bs["assets"] if a["account_subtype"] == "ACCOUNTS_RECEIVABLE"),
        0.0,
    )
    ap_balance = next(
        (l["amount"] for l in bs["liabilities"] if l["account_subtype"] == "ACCOUNTS_PAYABLE"),
        0.0,
    )

    total_employees = (
        db.execute(
            select(func.count(Employee.id)).where(
                Employee.organization_id == org_id,
                Employee.employment_status == "ACTIVE",
            )
        ).scalar_one()
        or 0
    )
    active_projects = (
        db.execute(
            select(func.count(Project.id)).where(
                Project.organization_id == org_id,
                Project.status == "IN_PROGRESS",
            )
        ).scalar_one()
        or 0
    )
    inventory_valuation = float(
        db.execute(
            select(func.coalesce(func.sum(StockBalance.total_valuation), 0)).where(
                StockBalance.organization_id == org_id
            )
        ).scalar_one()
        or 0.0
    )

    # Low-stock count
    products = list(db.execute(select(Product).where(Product.organization_id == org_id)).scalars())
    avail_rows = db.execute(
        select(
            StockBalance.product_id,
            func.coalesce(func.sum(StockBalance.quantity_available), 0),
        )
        .where(StockBalance.organization_id == org_id)
        .group_by(StockBalance.product_id)
    ).all()
    avail_map = {r[0]: float(r[1]) for r in avail_rows}
    low_stock_count = sum(1 for p in products if avail_map.get(p.id, 0.0) <= float(p.reorder_level))

    pending_approvals = (
        db.execute(
            select(func.count(ApprovalRequest.id)).where(
                ApprovalRequest.organization_id == org_id,
                ApprovalRequest.status == "PENDING",
            )
        ).scalar_one()
        or 0
    )

    # Monthly Revenue vs Expenses Chart Series (Derived from Invoices & Expenses)
    invoices = list(
        db.execute(
            select(Invoice).where(
                Invoice.organization_id == org_id,
                Invoice.invoice_type == "CUSTOMER_INVOICE",
            )
        ).scalars()
    )
    expenses = list(
        db.execute(select(Expense).where(Expense.organization_id == org_id)).scalars()
    )
    pos = list(
        db.execute(select(PurchaseOrder).where(PurchaseOrder.organization_id == org_id)).scalars()
    )

    today = date.today()
    monthly_map: dict[str, dict[str, float]] = {}
    for m_back in range(5, -1, -1):
        dt = (today.replace(day=1) - timedelta(days=m_back * 28)).replace(day=1)
        k = dt.strftime("%Y-%m")
        monthly_map[k] = {
            "month": dt.strftime("%b %Y"),
            "revenue": 0.0,
            "expenses": 0.0,
            "purchases": 0.0,
            "cash_flow": 0.0,
        }

    for inv in invoices:
        k = inv.issue_date.strftime("%Y-%m")
        if k in monthly_map:
            monthly_map[k]["revenue"] = round(monthly_map[k]["revenue"] + float(inv.total_amount), 2)

    for exp in expenses:
        k = exp.expense_date.strftime("%Y-%m")
        if k in monthly_map:
            monthly_map[k]["expenses"] = round(monthly_map[k]["expenses"] + float(exp.total_amount), 2)

    for po in pos:
        k = po.order_date.strftime("%Y-%m")
        if k in monthly_map:
            monthly_map[k]["purchases"] = round(monthly_map[k]["purchases"] + float(po.total_amount), 2)

    for k, bucket in monthly_map.items():
        bucket["cash_flow"] = round(bucket["revenue"] - bucket["expenses"], 2)

    # Department Performance Distribution
    depts = list(
        db.execute(select(Department).where(Department.organization_id == org_id)).scalars()
    )
    emp_by_dept = dict(
        db.execute(
            select(Employee.department_id, func.count(Employee.id))
            .where(Employee.organization_id == org_id)
            .group_by(Employee.department_id)
        ).all()
    )
    department_performance = [
        {
            "department": d.name,
            "code": d.code,
            "budget_lkr": float(d.budget_allocated),
            "headcount": int(emp_by_dept.get(d.id, 0)),
        }
        for d in depts
    ]

    return {
        "organization": {
            "id": ctx.organization.id,
            "name": ctx.organization.name,
            "currency": ctx.organization.default_currency,
            "timezone": ctx.organization.timezone,
            "is_demo_data": ctx.organization.is_demo,
        },
        "kpis": {
            "total_revenue": pnl["total_revenue"],
            "total_expenses": pnl["total_expenses"],
            "net_profit": pnl["net_profit"],
            "net_margin_percent": round(pnl["net_margin_percent"], 2),
            "outstanding_receivables": ar_balance,
            "outstanding_payables": ap_balance,
            "cash_and_bank_balance": cf["cash_and_bank_ending_balance"],
            "total_employees": total_employees,
            "active_projects": active_projects,
            "inventory_valuation": round(inventory_valuation, 2),
            "low_stock_products": low_stock_count,
            "pending_approvals": pending_approvals,
        },
        "charts": {
            "monthly_trends": list(monthly_map.values()),
            "department_performance": department_performance,
        },
    }


@router.get("/analytics/reports/{report_type}")
def generate_bi_report(
    report_type: str,
    ctx: AuthContext = Depends(require_permissions("reports.view")),
    db: Session = Depends(get_db),
) -> dict:
    org_id = ctx.organization.id
    rt = report_type.lower()

    if rt in {"trial-balance", "financial"}:
        tb = compute_trial_balance(db, org_id)
        return {"report_type": "Trial Balance", "columns": ["code", "name", "account_type", "debit_balance", "credit_balance"], "rows": tb["accounts"]}
    if rt == "invoice-aging":
        invs = list(db.execute(select(Invoice, Customer.name).outerjoin(Customer, Customer.id == Invoice.customer_id).where(Invoice.organization_id == org_id)).all())
        return {
            "report_type": "Customer Invoice Aging Schedule",
            "columns": ["invoice_number", "customer_name", "issue_date", "due_date", "total_amount", "amount_paid", "balance_due", "status"],
            "rows": [
                {
                    "invoice_number": i.invoice_number,
                    "customer_name": c_name or "Corporate Client",
                    "issue_date": i.issue_date.isoformat(),
                    "due_date": i.due_date.isoformat(),
                    "total_amount": float(i.total_amount),
                    "amount_paid": float(i.amount_paid),
                    "balance_due": float(i.balance_due),
                    "status": i.status,
                }
                for i, c_name in invs
            ],
        }
    if rt == "supplier-performance":
        sups = list(db.execute(select(Supplier).where(Supplier.organization_id == org_id)).scalars())
        return {
            "report_type": "Supplier Performance & Lead-Time Report",
            "columns": ["supplier_code", "name", "rating", "on_time_delivery_rate", "payment_terms_days"],
            "rows": [
                {
                    "supplier_code": s.supplier_code,
                    "name": s.name,
                    "rating": float(s.rating),
                    "on_time_delivery_rate": float(s.on_time_delivery_rate),
                    "payment_terms_days": s.payment_terms_days,
                }
                for s in sups
            ],
        }

    # Default Stock Valuation report
    prods = list(db.execute(select(Product).where(Product.organization_id == org_id)).scalars())
    return {
        "report_type": "Inventory Weighted Average Cost Valuation",
        "columns": ["sku", "name", "uom", "cost_price", "weighted_avg_cost", "selling_price", "reorder_level"],
        "rows": [
            {
                "sku": p.sku,
                "name": p.name,
                "uom": p.uom,
                "cost_price": float(p.cost_price),
                "weighted_avg_cost": float(p.weighted_avg_cost),
                "selling_price": float(p.selling_price),
                "reorder_level": float(p.reorder_level),
            }
            for p in prods
        ],
    }


@router.get("/search")
def global_search(
    q: str = Query(..., min_length=1),
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    """Global permission-aware search across Employees, Products, Customers, Suppliers & Invoices."""
    term = q.strip().lower()
    org_id = ctx.organization.id
    results = []

    for p in db.execute(select(Product).where(Product.organization_id == org_id)).scalars():
        if term in p.name.lower() or term in p.sku.lower():
            results.append({"type": "Product", "code": p.sku, "title": p.name, "url": "/inventory"})

    for c in db.execute(select(Customer).where(Customer.organization_id == org_id)).scalars():
        if term in c.name.lower() or term in c.customer_code.lower():
            results.append({"type": "Customer", "code": c.customer_code, "title": c.name, "url": "/sales"})

    for s in db.execute(select(Supplier).where(Supplier.organization_id == org_id)).scalars():
        if term in s.name.lower() or term in s.supplier_code.lower():
            results.append({"type": "Supplier", "code": s.supplier_code, "title": s.name, "url": "/procurement"})

    for e in db.execute(select(Employee).where(Employee.organization_id == org_id)).scalars():
        full = f"{e.first_name} {e.last_name}"
        if term in full.lower() or term in e.employee_code.lower():
            results.append({"type": "Employee", "code": e.employee_code, "title": full, "url": "/hr"})

    return {"query": q, "results": results[:20]}


# ============================================================================
# NOTIFICATIONS
# ============================================================================

@router.get("/notifications")
def list_notifications(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    notifs = list(
        db.execute(
            select(Notification)
            .where(Notification.organization_id == ctx.organization.id)
            .order_by(Notification.created_at.desc())
            .limit(40)
        ).scalars()
    )
    return {
        "unread_count": sum(1 for n in notifs if not n.is_read),
        "items": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "category": n.category,
                "severity": n.severity,
                "action_url": n.action_url,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifs
        ],
    }


@router.post("/notifications/{notif_id}/read")
def mark_notification_read(
    notif_id: str,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    n = db.execute(
        select(Notification).where(
            Notification.id == notif_id,
            Notification.organization_id == ctx.organization.id,
        )
    ).scalar_one_or_none()
    if n:
        n.is_read = True
        db.commit()
    return {"status": "ok"}


# ============================================================================
# NEXORA INTELLIGENCE — AI ENGINE ENDPOINTS
# ============================================================================

@router.get("/ai/insights")
def list_ai_insights(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    insights = list(
        db.execute(
            select(AIInsight)
            .where(AIInsight.organization_id == ctx.organization.id)
            .order_by(AIInsight.created_at.desc())
        ).scalars()
    )
    return {
        "items": [
            {
                "id": i.id,
                "category": i.category,
                "title": i.title,
                "summary": i.summary,
                "impact_estimate": i.impact_estimate,
                "confidence_score": float(i.confidence_score),
                "source_references": i.source_references or [],
            }
            for i in insights
        ]
    }


@router.post("/ai/forecast/inventory")
def api_forecast_inventory(
    payload: ForecastInventoryRequest,
    ctx: AuthContext = Depends(require_permissions("ai.forecast.view")),
    db: Session = Depends(get_db),
) -> dict:
    return run_inventory_demand_forecast(
        db,
        organization_id=ctx.organization.id,
        model_choice=payload.model_choice,
        executed_by_id=ctx.user.id,
    )


@router.post("/ai/forecast/sales")
def api_forecast_sales(
    payload: ForecastSalesRequest,
    ctx: AuthContext = Depends(require_permissions("ai.forecast.view")),
    db: Session = Depends(get_db),
) -> dict:
    return run_sales_revenue_forecast(
        db,
        organization_id=ctx.organization.id,
        horizon_months=payload.horizon_months,
        executed_by_id=ctx.user.id,
    )


@router.post("/ai/anomalies/analyze")
def api_analyze_anomalies(
    ctx: AuthContext = Depends(require_permissions("ai.anomalies.view")),
    db: Session = Depends(get_db),
) -> dict:
    return run_business_anomaly_detection(db, organization_id=ctx.organization.id)


@router.patch("/ai/anomalies/{anomaly_id}")
def update_anomaly_status(
    anomaly_id: str,
    payload: AnomalyStatusUpdateSchema,
    ctx: AuthContext = Depends(require_permissions("ai.anomalies.view")),
    db: Session = Depends(get_db),
) -> dict:
    ev = db.execute(
        select(AnomalyEvent).where(
            AnomalyEvent.id == anomaly_id,
            AnomalyEvent.organization_id == ctx.organization.id,
        )
    ).scalar_one_or_none()
    if not ev:
        raise NotFoundError("Anomaly event not found.")
    ev.status = payload.status.upper()
    ev.reviewed_by_id = ctx.user.id
    db.commit()
    return {"id": ev.id, "status": ev.status}


@router.post("/ai/copilot/chat")
def api_copilot_chat(
    payload: CopilotChatRequest,
    ctx: AuthContext = Depends(require_permissions("ai.copilot.use")),
    db: Session = Depends(get_db),
) -> dict:
    return handle_copilot_chat(
        db,
        organization_id=ctx.organization.id,
        user_id=ctx.user.id,
        user_permissions=ctx.permissions,
        question=payload.question,
        conversation_id=payload.conversation_id,
    )
