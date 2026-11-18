"""NEXORA ERP — Procurement, Suppliers, Purchase Orders & Goods Receipts API Router."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, record_audit_log, require_permissions
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.models.entities import (
    ApprovalRequest,
    GoodsReceipt,
    GoodsReceiptItem,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseRequest,
    PurchaseRequestItem,
    Supplier,
    SupplierQuotation,
    Warehouse,
    new_uuid,
)
from app.services.accounting_service import create_journal_entry, quantize_money
from app.services.inventory_service import record_stock_movement
from app.services.workflow_service import (
    initiate_approval_request,
    process_approval_decision,
)

router = APIRouter(tags=["Procurement & Suppliers"])


class SupplierCreateSchema(BaseModel):
    name: str
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    payment_terms_days: int = 30


class PRItemSchema(BaseModel):
    product_id: str
    quantity: float
    estimated_unit_price: float


class PurchaseRequestCreateSchema(BaseModel):
    required_date: Optional[date] = None
    justification: str
    items: list[PRItemSchema]


class POItemSchema(BaseModel):
    product_id: str
    ordered_qty: float
    unit_price: float
    tax_rate: float = 8.0


class PurchaseOrderCreateSchema(BaseModel):
    supplier_id: str
    warehouse_id: Optional[str] = None
    purchase_request_id: Optional[str] = None
    expected_delivery_date: Optional[date] = None
    items: list[POItemSchema]


class POApprovalSchema(BaseModel):
    action: str = "APPROVE"  # APPROVE or REJECT
    comments: Optional[str] = None


class GRNItemSchema(BaseModel):
    product_id: str
    received_qty: float
    unit_cost: float


class GoodsReceiptCreateSchema(BaseModel):
    purchase_order_id: str
    supplier_invoice_no: Optional[str] = None
    notes: Optional[str] = None
    items: Optional[list[GRNItemSchema]] = None


@router.get("/suppliers")
def list_suppliers(
    ctx: AuthContext = Depends(require_permissions("procurement.view")),
    db: Session = Depends(get_db),
) -> dict:
    sups = list(
        db.execute(
            select(Supplier)
            .where(Supplier.organization_id == ctx.organization.id)
            .order_by(Supplier.supplier_code)
        ).scalars()
    )
    return {
        "items": [
            {
                "id": s.id,
                "supplier_code": s.supplier_code,
                "name": s.name,
                "contact_person": s.contact_person,
                "email": s.email,
                "phone": s.phone,
                "tax_id": s.tax_id,
                "address": s.address,
                "payment_terms_days": s.payment_terms_days,
                "rating": float(s.rating),
                "on_time_delivery_rate": float(s.on_time_delivery_rate),
                "is_active": s.is_active,
            }
            for s in sups
        ]
    }


@router.post("/suppliers", status_code=201)
def create_supplier(
    payload: SupplierCreateSchema,
    ctx: AuthContext = Depends(require_permissions("procurement.manage")),
    db: Session = Depends(get_db),
) -> dict:
    cnt = (
        db.execute(
            select(func.count(Supplier.id)).where(Supplier.organization_id == ctx.organization.id)
        ).scalar_one()
        or 0
    )
    s = Supplier(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        supplier_code=f"SUP-{cnt + 1:03d}",
        name=payload.name,
        contact_person=payload.contact_person,
        email=payload.email,
        phone=payload.phone,
        tax_id=payload.tax_id,
        address=payload.address,
        payment_terms_days=payload.payment_terms_days,
    )
    db.add(s)
    record_audit_log(db, ctx=ctx, action="SUPPLIER_CREATED", entity_type="Supplier", entity_id=s.id)
    db.commit()
    return {"id": s.id, "supplier_code": s.supplier_code, "name": s.name}


@router.get("/purchase-requests")
def list_purchase_requests(
    ctx: AuthContext = Depends(require_permissions("procurement.view")),
    db: Session = Depends(get_db),
) -> dict:
    prs = list(
        db.execute(
            select(PurchaseRequest)
            .where(PurchaseRequest.organization_id == ctx.organization.id)
            .order_by(PurchaseRequest.created_at.desc())
        ).scalars()
    )
    quotations = list(
        db.execute(
            select(SupplierQuotation, Supplier.name)
            .join(Supplier, Supplier.id == SupplierQuotation.supplier_id)
            .where(SupplierQuotation.organization_id == ctx.organization.id)
        ).all()
    )
    q_by_pr: dict[str, list] = {}
    for q, s_name in quotations:
        q_by_pr.setdefault(q.purchase_request_id, []).append(
            {
                "id": q.id,
                "quotation_number": q.quotation_number,
                "supplier_name": s_name,
                "quoted_total": float(q.quoted_total),
                "lead_time_days": q.lead_time_days,
                "is_selected": q.is_selected,
            }
        )

    return {
        "items": [
            {
                "id": pr.id,
                "pr_number": pr.pr_number,
                "required_date": pr.required_date.isoformat(),
                "estimated_total": float(pr.estimated_total),
                "status": pr.status,
                "justification": pr.justification,
                "quotations": q_by_pr.get(pr.id, []),
                "created_at": pr.created_at.isoformat() if pr.created_at else None,
            }
            for pr in prs
        ]
    }


@router.post("/purchase-requests", status_code=201)
def create_purchase_request(
    payload: PurchaseRequestCreateSchema,
    ctx: AuthContext = Depends(require_permissions("purchase_requests.create")),
    db: Session = Depends(get_db),
) -> dict:
    if not payload.items:
        raise BusinessRuleError("At least one item is required for a Purchase Request.")

    cnt = (
        db.execute(
            select(func.count(PurchaseRequest.id)).where(
                PurchaseRequest.organization_id == ctx.organization.id
            )
        ).scalar_one()
        or 0
    )
    pr_num = f"PR-{datetime.now(timezone.utc).year}-{101 + cnt:03d}"
    est_tot = sum(
        (quantize_money(i.quantity) * quantize_money(i.estimated_unit_price) for i in payload.items),
        Decimal("0.00"),
    )

    pr = PurchaseRequest(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        pr_number=pr_num,
        requested_by_id=ctx.user.id,
        required_date=payload.required_date or (date.today() + timedelta(days=14)),
        estimated_total=quantize_money(est_tot),
        status="PENDING_APPROVAL",
        justification=payload.justification,
    )
    db.add(pr)
    db.flush()

    for i in payload.items:
        line_t = quantize_money(Decimal(str(i.quantity)) * Decimal(str(i.estimated_unit_price)))
        db.add(
            PurchaseRequestItem(
                id=new_uuid(),
                purchase_request_id=pr.id,
                product_id=i.product_id,
                quantity=quantize_money(i.quantity),
                estimated_unit_price=quantize_money(i.estimated_unit_price),
                line_total=line_t,
            )
        )

    initiate_approval_request(
        db,
        organization_id=ctx.organization.id,
        document_type="PURCHASE_REQUEST",
        document_id=pr.id,
        document_number=pr.pr_number,
        amount=pr.estimated_total,
        requested_by_id=ctx.user.id,
    )
    db.commit()
    return {"id": pr.id, "pr_number": pr.pr_number, "estimated_total": float(pr.estimated_total), "status": pr.status}


@router.get("/purchase-orders")
def list_purchase_orders(
    ctx: AuthContext = Depends(require_permissions("procurement.view")),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.execute(
        select(PurchaseOrder, Supplier.name, Warehouse.name)
        .join(Supplier, Supplier.id == PurchaseOrder.supplier_id)
        .join(Warehouse, Warehouse.id == PurchaseOrder.warehouse_id)
        .where(PurchaseOrder.organization_id == ctx.organization.id)
        .order_by(PurchaseOrder.created_at.desc())
    ).all()
    items = []
    for po, sup_name, wh_name in rows:
        line_rows = db.execute(
            select(PurchaseOrderItem, Product.sku, Product.name)
            .join(Product, Product.id == PurchaseOrderItem.product_id)
            .where(PurchaseOrderItem.purchase_order_id == po.id)
        ).all()
        items.append(
            {
                "id": po.id,
                "po_number": po.po_number,
                "supplier_id": po.supplier_id,
                "supplier_name": sup_name,
                "warehouse_id": po.warehouse_id,
                "warehouse_name": wh_name,
                "order_date": po.order_date.isoformat(),
                "expected_delivery_date": po.expected_delivery_date.isoformat(),
                "subtotal": float(po.subtotal),
                "tax_amount": float(po.tax_amount),
                "total_amount": float(po.total_amount),
                "status": po.status,
                "approval_step_required": po.approval_step_required,
                "approval_step_completed": po.approval_step_completed,
                "created_by_id": po.created_by_id,
                "rejection_reason": po.rejection_reason,
                "items": [
                    {
                        "id": li.id,
                        "product_id": li.product_id,
                        "sku": sku,
                        "product_name": p_name,
                        "ordered_qty": float(li.ordered_qty),
                        "received_qty": float(li.received_qty),
                        "unit_price": float(li.unit_price),
                        "line_total": float(li.line_total),
                    }
                    for li, sku, p_name in line_rows
                ],
            }
        )
    return {"items": items}


@router.post("/purchase-orders", status_code=201)
def create_purchase_order(
    payload: PurchaseOrderCreateSchema,
    ctx: AuthContext = Depends(require_permissions("purchase_orders.create")),
    db: Session = Depends(get_db),
) -> dict:
    if not payload.items:
        raise BusinessRuleError("At least one line item is required for a Purchase Order.")

    wh_id = payload.warehouse_id
    if not wh_id:
        wh = db.execute(
            select(Warehouse).where(Warehouse.organization_id == ctx.organization.id)
        ).scalars().first()
        if not wh:
            raise NotFoundError("No warehouse configured for organization.")
        wh_id = wh.id

    cnt = (
        db.execute(
            select(func.count(PurchaseOrder.id)).where(
                PurchaseOrder.organization_id == ctx.organization.id
            )
        ).scalar_one()
        or 0
    )
    po_num = f"PO-{datetime.now(timezone.utc).year}-{301 + cnt:03d}"

    subtotal = Decimal("0.00")
    tax_total = Decimal("0.00")
    for item in payload.items:
        l_sub = quantize_money(Decimal(str(item.ordered_qty)) * Decimal(str(item.unit_price)))
        l_tax = quantize_money(l_sub * Decimal(str(item.tax_rate)) / Decimal("100.0"))
        subtotal += l_sub
        tax_total += l_tax

    grand_total = quantize_money(subtotal + tax_total)
    steps_req = 2 if grand_total > Decimal(str(settings.po_dual_approval_threshold_lkr)) else 1

    po = PurchaseOrder(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        po_number=po_num,
        supplier_id=payload.supplier_id,
        purchase_request_id=payload.purchase_request_id,
        warehouse_id=wh_id,
        order_date=date.today(),
        expected_delivery_date=payload.expected_delivery_date or (date.today() + timedelta(days=10)),
        subtotal=subtotal,
        tax_amount=tax_total,
        total_amount=grand_total,
        status="PENDING_APPROVAL",
        approval_step_required=steps_req,
        approval_step_completed=0,
        created_by_id=ctx.user.id,
    )
    db.add(po)
    db.flush()

    for item in payload.items:
        l_sub = quantize_money(Decimal(str(item.ordered_qty)) * Decimal(str(item.unit_price)))
        db.add(
            PurchaseOrderItem(
                id=new_uuid(),
                purchase_order_id=po.id,
                product_id=item.product_id,
                ordered_qty=quantize_money(item.ordered_qty),
                received_qty=Decimal("0.00"),
                unit_price=quantize_money(item.unit_price),
                tax_rate=quantize_money(item.tax_rate),
                line_total=l_sub,
            )
        )

    initiate_approval_request(
        db,
        organization_id=ctx.organization.id,
        document_type="PURCHASE_ORDER",
        document_id=po.id,
        document_number=po.po_number,
        amount=po.total_amount,
        requested_by_id=ctx.user.id,
    )
    record_audit_log(
        db,
        ctx=ctx,
        action="PURCHASE_ORDER_CREATED",
        entity_type="PurchaseOrder",
        entity_id=po.id,
        after_state={"po_number": po.po_number, "total_amount": float(po.total_amount)},
    )
    db.commit()
    return {
        "id": po.id,
        "po_number": po.po_number,
        "total_amount": float(po.total_amount),
        "status": po.status,
        "approval_step_required": po.approval_step_required,
    }


@router.post("/purchase-orders/{po_id}/approve")
def approve_purchase_order(
    po_id: str,
    payload: POApprovalSchema,
    ctx: AuthContext = Depends(require_permissions("purchase_orders.approve")),
    db: Session = Depends(get_db),
) -> dict:
    po = db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == po_id,
            PurchaseOrder.organization_id == ctx.organization.id,
        )
    ).scalar_one_or_none()
    if not po:
        raise NotFoundError("Purchase order not found.")
    if po.status not in {"PENDING_APPROVAL", "DRAFT"}:
        raise BusinessRuleError(f"Purchase order is already in status '{po.status}'.")

    # Separation of Duties invariant: Creator cannot approve their own Purchase Order
    if po.created_by_id == ctx.user.id and payload.action.upper() == "APPROVE":
        raise ForbiddenError(
            "Separation of Duties violation: You cannot approve a Purchase Order that you created.",
            code="SELF_APPROVAL_FORBIDDEN",
        )

    app_req = db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.organization_id == ctx.organization.id,
            ApprovalRequest.document_type == "PURCHASE_ORDER",
            ApprovalRequest.document_id == po.id,
        )
    ).scalar_one_or_none()

    if app_req:
        process_approval_decision(
            db,
            organization_id=ctx.organization.id,
            approval_request_id=app_req.id,
            actor_user_id=ctx.user.id,
            action=payload.action,
            comments=payload.comments,
        )

    if payload.action.upper() == "REJECT":
        if not (payload.comments and payload.comments.strip()):
            raise BusinessRuleError("Rejection reason is mandatory when rejecting a Purchase Order.")
        po.status = "REJECTED"
        po.rejection_reason = payload.comments
    else:
        po.approval_step_completed = po.approval_step_required
        po.status = "APPROVED"
        po.approved_by_id = ctx.user.id

    record_audit_log(
        db,
        ctx=ctx,
        action=f"PURCHASE_ORDER_{po.status}",
        entity_type="PurchaseOrder",
        entity_id=po.id,
    )
    db.commit()
    return {
        "id": po.id,
        "po_number": po.po_number,
        "status": po.status,
        "approved_by_id": po.approved_by_id,
    }


@router.get("/goods-receipts")
def list_goods_receipts(
    ctx: AuthContext = Depends(require_permissions("procurement.view")),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.execute(
        select(GoodsReceipt, PurchaseOrder.po_number, Supplier.name, Warehouse.name)
        .join(PurchaseOrder, PurchaseOrder.id == GoodsReceipt.purchase_order_id)
        .join(Supplier, Supplier.id == GoodsReceipt.supplier_id)
        .join(Warehouse, Warehouse.id == GoodsReceipt.warehouse_id)
        .where(GoodsReceipt.organization_id == ctx.organization.id)
        .order_by(GoodsReceipt.created_at.desc())
    ).all()
    return {
        "items": [
            {
                "id": g.id,
                "grn_number": g.grn_number,
                "po_number": po_num,
                "supplier_name": sup_name,
                "warehouse_name": wh_name,
                "received_date": g.received_date.isoformat(),
                "supplier_invoice_no": g.supplier_invoice_no,
                "total_received_value": float(g.total_received_value),
                "status": g.status,
            }
            for g, po_num, sup_name, wh_name in rows
        ]
    }


@router.post("/goods-receipts", status_code=201)
def create_goods_receipt(
    payload: GoodsReceiptCreateSchema,
    ctx: AuthContext = Depends(require_permissions("goods_receipts.create")),
    db: Session = Depends(get_db),
) -> dict:
    """Receive full or partial PO delivery -> update inventory WAC -> post AP Journal Entry."""
    po = db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == payload.purchase_order_id,
            PurchaseOrder.organization_id == ctx.organization.id,
        )
    ).scalar_one_or_none()
    if not po:
        raise NotFoundError("Purchase Order not found.")
    if po.status not in {"APPROVED", "PARTIALLY_RECEIVED"}:
        raise BusinessRuleError(
            f"Cannot receive goods against Purchase Order {po.po_number} in status '{po.status}'. PO must be APPROVED first.",
            code="PO_NOT_APPROVED",
        )

    po_items = list(
        db.execute(
            select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == po.id)
        ).scalars()
    )

    cnt = (
        db.execute(
            select(func.count(GoodsReceipt.id)).where(
                GoodsReceipt.organization_id == ctx.organization.id
            )
        ).scalar_one()
        or 0
    )
    grn_num = f"GRN-{datetime.now(timezone.utc).year}-{401 + cnt:03d}"

    grn = GoodsReceipt(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        grn_number=grn_num,
        purchase_order_id=po.id,
        supplier_id=po.supplier_id,
        warehouse_id=po.warehouse_id,
        received_date=date.today(),
        received_by_id=ctx.user.id,
        supplier_invoice_no=payload.supplier_invoice_no or f"SINV-{grn_num}",
        total_received_value=Decimal("0.00"),
        status="POSTED",
        notes=payload.notes,
    )
    db.add(grn)
    db.flush()

    total_val = Decimal("0.00")
    all_fulfilled = True

    for poi in po_items:
        remaining = quantize_money(poi.ordered_qty - poi.received_qty)
        if remaining <= Decimal("0.00"):
            continue

        rec_qty = remaining
        rec_cost = poi.unit_price
        if payload.items:
            matched = next((x for x in payload.items if x.product_id == poi.product_id), None)
            if matched:
                rec_qty = quantize_money(matched.received_qty)
                rec_cost = quantize_money(matched.unit_cost)
            else:
                all_fulfilled = False
                continue

        if rec_qty < remaining:
            all_fulfilled = False

        poi.received_qty = quantize_money(poi.received_qty + rec_qty)
        line_val = quantize_money(rec_qty * rec_cost)
        total_val += line_val

        db.add(
            GoodsReceiptItem(
                id=new_uuid(),
                goods_receipt_id=grn.id,
                purchase_order_item_id=poi.id,
                product_id=poi.product_id,
                received_qty=rec_qty,
                rejected_qty=Decimal("0.00"),
                unit_cost=rec_cost,
                line_total=line_val,
            )
        )

        record_stock_movement(
            db,
            organization_id=ctx.organization.id,
            product_id=poi.product_id,
            warehouse_id=po.warehouse_id,
            movement_type="RECEIPT",
            quantity=rec_qty,
            unit_cost=rec_cost,
            reference_type="GOODS_RECEIPT",
            reference_id=grn.id,
            reference_number=grn.grn_number,
            performed_by_id=ctx.user.id,
            notes=f"GRN against {po.po_number}",
        )

    if total_val <= Decimal("0.00"):
        raise BusinessRuleError("Goods Receipt must receive a positive quantity.")

    grn.total_received_value = total_val
    po.status = "RECEIVED" if all_fulfilled else "PARTIALLY_RECEIVED"

    # Auto-post Double-Entry Accounting Entry: Debit Inventory (1200), Credit Accounts Payable (2000)
    je = create_journal_entry(
        db,
        organization_id=ctx.organization.id,
        entry_date=date.today(),
        reference_type="GOODS_RECEIPT",
        reference_id=grn.id,
        reference_number=grn.grn_number,
        description=f"Goods Receipt {grn.grn_number} against {po.po_number}",
        lines=[
            {"account_code": "1200", "debit": total_val, "credit": Decimal("0.00")},
            {"account_code": "2000", "debit": Decimal("0.00"), "credit": total_val},
        ],
        created_by_id=ctx.user.id,
        auto_post=True,
    )
    grn.journal_entry_id = je.id

    record_audit_log(
        db,
        ctx=ctx,
        action="GOODS_RECEIPT_POSTED",
        entity_type="GoodsReceipt",
        entity_id=grn.id,
        after_state={"grn_number": grn.grn_number, "total_received_value": float(total_val)},
    )
    db.commit()
    return {
        "id": grn.id,
        "grn_number": grn.grn_number,
        "po_status": po.status,
        "total_received_value": float(total_val),
        "journal_entry_id": je.id,
    }
