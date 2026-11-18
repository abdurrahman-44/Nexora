"""NEXORA ERP — Sales, Customers, Invoices, Payments & Double-Entry Finance API Router."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    AuthContext,
    record_audit_log,
    require_any_permission,
    require_permissions,
)
from app.core.database import get_db
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.entities import (
    Account,
    BankAccount,
    Customer,
    Expense,
    Invoice,
    InvoiceItem,
    JournalEntry,
    JournalLine,
    Payment,
    Product,
    SalesOrder,
    SalesOrderItem,
    SalesQuotation,
    Warehouse,
    new_uuid,
)
from app.services.accounting_service import (
    compute_financial_statements,
    compute_trial_balance,
    create_journal_entry,
    post_journal_entry,
    quantize_money,
    reverse_journal_entry,
)
from app.services.inventory_service import record_stock_movement

router = APIRouter(tags=["Sales & Finance"])


class CustomerCreateSchema(BaseModel):
    name: str
    customer_type: str = "CORPORATE"
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    tax_id: Optional[str] = None
    billing_address: Optional[str] = None
    credit_limit: float = 1000000.0
    payment_terms_days: int = 30


class SalesItemSchema(BaseModel):
    product_id: str
    quantity: float
    unit_price: Optional[float] = None
    discount_amount: float = 0.0
    tax_rate: float = 8.0


class SalesOrderCreateSchema(BaseModel):
    customer_id: str
    warehouse_id: Optional[str] = None
    items: list[SalesItemSchema]


class InvoiceCreateSchema(BaseModel):
    customer_id: str
    sales_order_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    due_days: int = 30
    deduct_inventory: bool = True
    items: list[SalesItemSchema]


class PaymentCreateSchema(BaseModel):
    invoice_id: str
    amount: float
    payment_method: str = "BANK_TRANSFER"
    reference_no: Optional[str] = None
    idempotency_key: Optional[str] = None


class AccountCreateSchema(BaseModel):
    code: str
    name: str
    account_type: str  # ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE
    account_subtype: str = "OPERATING_EXPENSE"
    normal_balance: str = "DEBIT"


class JournalLineInputSchema(BaseModel):
    account_id: Optional[str] = None
    account_code: Optional[str] = None
    description: Optional[str] = None
    debit: float = 0.0
    credit: float = 0.0
    department_id: Optional[str] = None


class JournalEntryCreateSchema(BaseModel):
    entry_date: Optional[date] = None
    reference_number: Optional[str] = None
    description: str
    auto_post: bool = True
    lines: list[JournalLineInputSchema]


class JournalReverseSchema(BaseModel):
    reason: str = "Audit adjustment / reversal"


class ExpenseCreateSchema(BaseModel):
    category: str
    vendor_name: str
    amount: float
    expense_account_code: str = "6100"
    department_id: Optional[str] = None
    description: Optional[str] = None


# ============================================================================
# CUSTOMERS & SALES
# ============================================================================

@router.get("/customers")
def list_customers(
    ctx: AuthContext = Depends(require_any_permission("sales.view", "invoices.view", "finance.view")),
    db: Session = Depends(get_db),
) -> dict:
    custs = list(
        db.execute(
            select(Customer)
            .where(Customer.organization_id == ctx.organization.id)
            .order_by(Customer.customer_code)
        ).scalars()
    )
    return {
        "items": [
            {
                "id": c.id,
                "customer_code": c.customer_code,
                "name": c.name,
                "customer_type": c.customer_type,
                "contact_person": c.contact_person,
                "email": c.email,
                "phone": c.phone,
                "tax_id": c.tax_id,
                "billing_address": c.billing_address,
                "credit_limit": float(c.credit_limit),
                "outstanding_balance": float(c.outstanding_balance),
                "payment_terms_days": c.payment_terms_days,
            }
            for c in custs
        ]
    }


@router.post("/customers", status_code=201)
def create_customer(
    payload: CustomerCreateSchema,
    ctx: AuthContext = Depends(require_permissions("sales.manage")),
    db: Session = Depends(get_db),
) -> dict:
    cnt = (
        db.execute(
            select(func.count(Customer.id)).where(Customer.organization_id == ctx.organization.id)
        ).scalar_one()
        or 0
    )
    c = Customer(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        customer_code=f"CUS-{cnt + 1:03d}",
        name=payload.name,
        customer_type=payload.customer_type.upper(),
        contact_person=payload.contact_person,
        email=payload.email,
        phone=payload.phone,
        tax_id=payload.tax_id,
        billing_address=payload.billing_address,
        credit_limit=Decimal(str(payload.credit_limit)),
        outstanding_balance=Decimal("0.00"),
        payment_terms_days=payload.payment_terms_days,
    )
    db.add(c)
    record_audit_log(db, ctx=ctx, action="CUSTOMER_CREATED", entity_type="Customer", entity_id=c.id)
    db.commit()
    return {"id": c.id, "customer_code": c.customer_code, "name": c.name}


@router.get("/sales/quotations")
def list_sales_quotations(
    ctx: AuthContext = Depends(require_permissions("sales.view")),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.execute(
        select(SalesQuotation, Customer.name)
        .join(Customer, Customer.id == SalesQuotation.customer_id)
        .where(SalesQuotation.organization_id == ctx.organization.id)
        .order_by(SalesQuotation.created_at.desc())
    ).all()
    return {
        "items": [
            {
                "id": sq.id,
                "quotation_number": sq.quotation_number,
                "customer_name": c_name,
                "valid_until": sq.valid_until.isoformat(),
                "subtotal": float(sq.subtotal),
                "discount_amount": float(sq.discount_amount),
                "tax_amount": float(sq.tax_amount),
                "total_amount": float(sq.total_amount),
                "status": sq.status,
            }
            for sq, c_name in rows
        ]
    }


@router.get("/sales/orders")
def list_sales_orders(
    ctx: AuthContext = Depends(require_permissions("sales.view")),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.execute(
        select(SalesOrder, Customer.name, Warehouse.name)
        .join(Customer, Customer.id == SalesOrder.customer_id)
        .join(Warehouse, Warehouse.id == SalesOrder.warehouse_id)
        .where(SalesOrder.organization_id == ctx.organization.id)
        .order_by(SalesOrder.created_at.desc())
    ).all()
    return {
        "items": [
            {
                "id": so.id,
                "so_number": so.so_number,
                "customer_id": so.customer_id,
                "customer_name": c_name,
                "warehouse_name": w_name,
                "order_date": so.order_date.isoformat(),
                "subtotal": float(so.subtotal),
                "discount_amount": float(so.discount_amount),
                "tax_amount": float(so.tax_amount),
                "total_amount": float(so.total_amount),
                "status": so.status,
            }
            for so, c_name, w_name in rows
        ]
    }


@router.post("/sales/orders", status_code=201)
def create_sales_order(
    payload: SalesOrderCreateSchema,
    ctx: AuthContext = Depends(require_permissions("sales.manage")),
    db: Session = Depends(get_db),
) -> dict:
    if not payload.items:
        raise BusinessRuleError("At least one item is required for a Sales Order.")

    wh_id = payload.warehouse_id
    if not wh_id:
        wh = db.execute(
            select(Warehouse).where(Warehouse.organization_id == ctx.organization.id)
        ).scalars().first()
        if not wh:
            raise NotFoundError("No warehouse configured.")
        wh_id = wh.id

    cnt = (
        db.execute(
            select(func.count(SalesOrder.id)).where(SalesOrder.organization_id == ctx.organization.id)
        ).scalar_one()
        or 0
    )
    so_num = f"SO-{datetime.now(timezone.utc).year}-{501 + cnt:04d}"

    subtotal = Decimal("0.00")
    disc_total = Decimal("0.00")
    tax_total = Decimal("0.00")

    so = SalesOrder(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        so_number=so_num,
        customer_id=payload.customer_id,
        warehouse_id=wh_id,
        order_date=date.today(),
        status="CONFIRMED",
        subtotal=Decimal("0.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("0.00"),
        created_by_id=ctx.user.id,
    )
    db.add(so)
    db.flush()

    for i in payload.items:
        prod = db.execute(
            select(Product).where(
                Product.id == i.product_id,
                Product.organization_id == ctx.organization.id,
            )
        ).scalar_one_or_none()
        if not prod:
            raise NotFoundError(f"Product {i.product_id} not found.")

        qty = quantize_money(i.quantity)
        unit_p = quantize_money(i.unit_price) if i.unit_price is not None else prod.selling_price
        disc = quantize_money(i.discount_amount)
        line_sub = quantize_money(qty * unit_p - disc)
        line_tax = quantize_money(line_sub * Decimal(str(i.tax_rate)) / Decimal("100.0"))
        line_tot = quantize_money(line_sub + line_tax)

        subtotal += quantize_money(qty * unit_p)
        disc_total += disc
        tax_total += line_tax

        db.add(
            SalesOrderItem(
                id=new_uuid(),
                sales_order_id=so.id,
                product_id=prod.id,
                quantity=qty,
                unit_price=unit_p,
                discount_amount=disc,
                tax_amount=line_tax,
                line_total=line_tot,
            )
        )

    so.subtotal = subtotal
    so.discount_amount = disc_total
    so.tax_amount = tax_total
    so.total_amount = quantize_money(subtotal - disc_total + tax_total)

    record_audit_log(db, ctx=ctx, action="SALES_ORDER_CREATED", entity_type="SalesOrder", entity_id=so.id)
    db.commit()
    return {
        "id": so.id,
        "so_number": so.so_number,
        "total_amount": float(so.total_amount),
        "status": so.status,
    }


# ============================================================================
# INVOICES & PAYMENTS (Synchronized with Double-Entry Accounting & Inventory)
# ============================================================================

@router.get("/invoices")
def list_invoices(
    ctx: AuthContext = Depends(require_any_permission("invoices.view", "sales.view", "finance.view")),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.execute(
        select(Invoice, Customer.name)
        .outerjoin(Customer, Customer.id == Invoice.customer_id)
        .where(Invoice.organization_id == ctx.organization.id)
        .order_by(Invoice.issue_date.desc(), Invoice.created_at.desc())
    ).all()
    today = date.today()
    items = []
    for inv, cust_name in rows:
        days_overdue = max(0, (today - inv.due_date).days) if inv.balance_due > 0 and inv.due_date < today else 0
        line_items = list(
            db.execute(select(InvoiceItem).where(InvoiceItem.invoice_id == inv.id)).scalars()
        )
        items.append(
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "invoice_type": inv.invoice_type,
                "customer_id": inv.customer_id,
                "customer_name": cust_name or "Corporate Partner",
                "issue_date": inv.issue_date.isoformat(),
                "due_date": inv.due_date.isoformat(),
                "subtotal": float(inv.subtotal),
                "discount_amount": float(inv.discount_amount),
                "tax_amount": float(inv.tax_amount),
                "total_amount": float(inv.total_amount),
                "amount_paid": float(inv.amount_paid),
                "balance_due": float(inv.balance_due),
                "status": inv.status,
                "days_overdue": days_overdue,
                "journal_entry_id": inv.journal_entry_id,
                "items": [
                    {
                        "id": li.id,
                        "product_id": li.product_id,
                        "description": li.description,
                        "quantity": float(li.quantity),
                        "unit_price": float(li.unit_price),
                        "line_total": float(li.line_total),
                    }
                    for li in line_items
                ],
            }
        )
    return {"items": items}


@router.post("/invoices", status_code=201)
def create_invoice(
    payload: InvoiceCreateSchema,
    ctx: AuthContext = Depends(require_permissions("invoices.create")),
    db: Session = Depends(get_db),
) -> dict:
    """Issue a customer invoice -> allocate/deduct stock -> post balanced GL Journal Entry."""
    if not payload.items:
        raise BusinessRuleError("At least one invoice item is required.")

    cust = db.execute(
        select(Customer).where(
            Customer.id == payload.customer_id,
            Customer.organization_id == ctx.organization.id,
        )
    ).scalar_one_or_none()
    if not cust:
        raise NotFoundError("Customer not found in organization.")

    wh_id = payload.warehouse_id
    if not wh_id:
        wh = db.execute(
            select(Warehouse).where(Warehouse.organization_id == ctx.organization.id)
        ).scalars().first()
        wh_id = wh.id if wh else None

    cnt = (
        db.execute(
            select(func.count(Invoice.id)).where(Invoice.organization_id == ctx.organization.id)
        ).scalar_one()
        or 0
    )
    inv_num = f"INV-{datetime.now(timezone.utc).year}-{1001 + cnt:04d}"

    subtotal = Decimal("0.00")
    disc_total = Decimal("0.00")
    tax_total = Decimal("0.00")
    total_cogs = Decimal("0.00")

    inv = Invoice(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        invoice_number=inv_num,
        invoice_type="CUSTOMER_INVOICE",
        customer_id=cust.id,
        sales_order_id=payload.sales_order_id,
        warehouse_id=wh_id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=payload.due_days),
        subtotal=Decimal("0.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("0.00"),
        amount_paid=Decimal("0.00"),
        balance_due=Decimal("0.00"),
        status="ISSUED",
        created_by_id=ctx.user.id,
    )
    db.add(inv)
    db.flush()

    for i in payload.items:
        prod = db.execute(
            select(Product).where(
                Product.id == i.product_id,
                Product.organization_id == ctx.organization.id,
            )
        ).scalar_one_or_none()
        if not prod:
            raise NotFoundError(f"Product {i.product_id} not found.")

        qty = quantize_money(i.quantity)
        unit_p = quantize_money(i.unit_price) if i.unit_price is not None else prod.selling_price
        disc = quantize_money(i.discount_amount)
        line_net = quantize_money(qty * unit_p - disc)
        line_tax = quantize_money(line_net * Decimal(str(i.tax_rate)) / Decimal("100.0"))
        line_tot = quantize_money(line_net + line_tax)

        subtotal += line_net
        disc_total += disc
        tax_total += line_tax

        if payload.deduct_inventory and wh_id:
            mov = record_stock_movement(
                db,
                organization_id=ctx.organization.id,
                product_id=prod.id,
                warehouse_id=wh_id,
                movement_type="ISSUE",
                quantity=qty,
                unit_cost=prod.weighted_avg_cost,
                reference_type="SALES_INVOICE",
                reference_id=inv.id,
                reference_number=inv_num,
                performed_by_id=ctx.user.id,
                notes=f"Invoice {inv_num} stock issue",
            )
            total_cogs += quantize_money(qty * mov.unit_cost)

        db.add(
            InvoiceItem(
                id=new_uuid(),
                invoice_id=inv.id,
                product_id=prod.id,
                description=prod.name,
                quantity=qty,
                unit_price=unit_p,
                discount_amount=disc,
                tax_amount=line_tax,
                line_total=line_tot,
            )
        )

    grand_total = quantize_money(subtotal + tax_total)
    inv.subtotal = subtotal
    inv.discount_amount = disc_total
    inv.tax_amount = tax_total
    inv.total_amount = grand_total
    inv.balance_due = grand_total
    cust.outstanding_balance = quantize_money(cust.outstanding_balance + grand_total)

    # Build balanced double-entry journal lines
    j_lines = [
        {"account_code": "1100", "debit": grand_total, "credit": Decimal("0.00")},
        {"account_code": "4000", "debit": Decimal("0.00"), "credit": subtotal},
    ]
    if tax_total > Decimal("0.00"):
        j_lines.append({"account_code": "2100", "debit": Decimal("0.00"), "credit": tax_total})
    if total_cogs > Decimal("0.00"):
        j_lines.append({"account_code": "5000", "debit": total_cogs, "credit": Decimal("0.00")})
        j_lines.append({"account_code": "1200", "debit": Decimal("0.00"), "credit": total_cogs})

    je = create_journal_entry(
        db,
        organization_id=ctx.organization.id,
        entry_date=date.today(),
        reference_type="SALES_INVOICE",
        reference_id=inv.id,
        reference_number=inv.invoice_number,
        description=f"Customer Invoice {inv.invoice_number} — {cust.name}",
        lines=j_lines,
        created_by_id=ctx.user.id,
        auto_post=True,
    )
    inv.journal_entry_id = je.id

    record_audit_log(
        db,
        ctx=ctx,
        action="INVOICE_ISSUED",
        entity_type="Invoice",
        entity_id=inv.id,
        after_state={"invoice_number": inv.invoice_number, "total_amount": float(grand_total)},
    )
    db.commit()
    return {
        "id": inv.id,
        "invoice_number": inv.invoice_number,
        "total_amount": float(inv.total_amount),
        "balance_due": float(inv.balance_due),
        "status": inv.status,
        "journal_entry_id": je.id,
    }


@router.get("/payments")
def list_payments(
    ctx: AuthContext = Depends(require_any_permission("payments.view", "finance.view")),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.execute(
        select(Payment, Invoice.invoice_number, Customer.name)
        .join(Invoice, Invoice.id == Payment.invoice_id)
        .outerjoin(Customer, Customer.id == Payment.customer_id)
        .where(Payment.organization_id == ctx.organization.id)
        .order_by(Payment.payment_date.desc(), Payment.created_at.desc())
    ).all()
    return {
        "items": [
            {
                "id": p.id,
                "payment_number": p.payment_number,
                "payment_type": p.payment_type,
                "invoice_id": p.invoice_id,
                "invoice_number": inv_num,
                "customer_name": cust_name or "Vendor / Partner",
                "payment_date": p.payment_date.isoformat(),
                "amount": float(p.amount),
                "payment_method": p.payment_method,
                "reference_no": p.reference_no,
                "journal_entry_id": p.journal_entry_id,
            }
            for p, inv_num, cust_name in rows
        ]
    }


@router.post("/payments", status_code=201)
def record_payment(
    payload: PaymentCreateSchema,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    ctx: AuthContext = Depends(require_permissions("payments.create")),
    db: Session = Depends(get_db),
) -> dict:
    """Record a payment with idempotency protection, preventing duplicate or over-payment."""
    idem_key = payload.idempotency_key or idempotency_key
    if idem_key:
        existing_pay = db.execute(
            select(Payment).where(Payment.idempotency_key == idem_key)
        ).scalar_one_or_none()
        if existing_pay:
            raise ConflictError(
                f"Duplicate payment request blocked by idempotency key '{idem_key}'.",
                code="DUPLICATE_PAYMENT",
            )

    inv = db.execute(
        select(Invoice).where(
            Invoice.id == payload.invoice_id,
            Invoice.organization_id == ctx.organization.id,
        )
    ).scalar_one_or_none()
    if not inv:
        raise NotFoundError("Invoice not found in organization.")

    pay_amt = quantize_money(payload.amount)
    if pay_amt <= Decimal("0.00"):
        raise BusinessRuleError("Payment amount must be strictly positive.")
    if pay_amt > quantize_money(inv.balance_due):
        raise BusinessRuleError(
            f"Payment amount (LKR {pay_amt}) exceeds invoice balance due (LKR {inv.balance_due}).",
            code="OVERPAYMENT_FORBIDDEN",
        )

    cnt = (
        db.execute(
            select(func.count(Payment.id)).where(Payment.organization_id == ctx.organization.id)
        ).scalar_one()
        or 0
    )
    pay_num = f"PAY-{datetime.now(timezone.utc).year}-{2001 + cnt:04d}"

    inv.amount_paid = quantize_money(inv.amount_paid + pay_amt)
    inv.balance_due = quantize_money(inv.total_amount - inv.amount_paid)
    inv.status = "PAID" if inv.balance_due == Decimal("0.00") else "PARTIALLY_PAID"

    if inv.customer_id:
        cust = db.execute(select(Customer).where(Customer.id == inv.customer_id)).scalar_one_or_none()
        if cust:
            cust.outstanding_balance = max(Decimal("0.00"), quantize_money(cust.outstanding_balance - pay_amt))

    je = create_journal_entry(
        db,
        organization_id=ctx.organization.id,
        entry_date=date.today(),
        reference_type="CUSTOMER_PAYMENT",
        reference_id=inv.id,
        reference_number=pay_num,
        description=f"Payment {pay_num} against Invoice {inv.invoice_number}",
        lines=[
            {"account_code": "1000", "debit": pay_amt, "credit": Decimal("0.00")},
            {"account_code": "1100", "debit": Decimal("0.00"), "credit": pay_amt},
        ],
        created_by_id=ctx.user.id,
        auto_post=True,
    )

    pay = Payment(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        payment_number=pay_num,
        payment_type="CUSTOMER_RECEIPT",
        invoice_id=inv.id,
        customer_id=inv.customer_id,
        payment_date=date.today(),
        amount=pay_amt,
        payment_method=payload.payment_method.upper(),
        reference_no=payload.reference_no or f"REF-{pay_num}",
        idempotency_key=idem_key,
        journal_entry_id=je.id,
        recorded_by_id=ctx.user.id,
    )
    db.add(pay)
    record_audit_log(
        db,
        ctx=ctx,
        action="PAYMENT_RECORDED",
        entity_type="Payment",
        entity_id=pay.id,
        after_state={"payment_number": pay.payment_number, "amount": float(pay_amt)},
    )
    db.commit()
    return {
        "id": pay.id,
        "payment_number": pay.payment_number,
        "amount": float(pay_amt),
        "invoice_status": inv.status,
        "invoice_balance_due": float(inv.balance_due),
        "journal_entry_id": je.id,
    }


# ============================================================================
# FINANCE & DOUBLE-ENTRY ACCOUNTING
# ============================================================================

@router.get("/finance/accounts")
def list_accounts(
    ctx: AuthContext = Depends(require_permissions("finance.view")),
    db: Session = Depends(get_db),
) -> dict:
    tb = compute_trial_balance(db, ctx.organization.id)
    bank_accs = list(
        db.execute(select(BankAccount).where(BankAccount.organization_id == ctx.organization.id)).scalars()
    )
    return {
        "items": tb["accounts"],
        "bank_accounts": [
            {
                "id": b.id,
                "account_name": b.account_name,
                "bank_name": b.bank_name,
                "account_number": b.account_number,
                "currency": b.currency,
            }
            for b in bank_accs
        ],
    }


@router.post("/finance/accounts", status_code=201)
def create_account(
    payload: AccountCreateSchema,
    ctx: AuthContext = Depends(require_permissions("finance.manage")),
    db: Session = Depends(get_db),
) -> dict:
    acc = Account(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        code=payload.code,
        name=payload.name,
        account_type=payload.account_type.upper(),
        account_subtype=payload.account_subtype.upper(),
        normal_balance=payload.normal_balance.upper(),
        current_balance=Decimal("0.00"),
    )
    db.add(acc)
    db.commit()
    return {"id": acc.id, "code": acc.code, "name": acc.name}


@router.get("/finance/journal-entries")
def list_journal_entries(
    ctx: AuthContext = Depends(require_permissions("finance.view")),
    db: Session = Depends(get_db),
) -> dict:
    entries = list(
        db.execute(
            select(JournalEntry)
            .where(JournalEntry.organization_id == ctx.organization.id)
            .order_by(JournalEntry.entry_date.desc(), JournalEntry.created_at.desc())
            .limit(100)
        ).scalars()
    )
    items = []
    for e in entries:
        l_rows = db.execute(
            select(JournalLine, Account.code, Account.name)
            .join(Account, Account.id == JournalLine.account_id)
            .where(JournalLine.journal_entry_id == e.id)
        ).all()
        items.append(
            {
                "id": e.id,
                "entry_number": e.entry_number,
                "entry_date": e.entry_date.isoformat(),
                "reference_type": e.reference_type,
                "reference_number": e.reference_number,
                "description": e.description,
                "status": e.status,
                "total_debit": float(e.total_debit),
                "total_credit": float(e.total_credit),
                "is_balanced": e.total_debit == e.total_credit,
                "lines": [
                    {
                        "id": jl.id,
                        "account_id": jl.account_id,
                        "account_code": a_code,
                        "account_name": a_name,
                        "description": jl.description,
                        "debit": float(jl.debit),
                        "credit": float(jl.credit),
                    }
                    for jl, a_code, a_name in l_rows
                ],
            }
        )
    return {"items": items}


@router.post("/finance/journal-entries", status_code=201)
def create_manual_journal_entry(
    payload: JournalEntryCreateSchema,
    ctx: AuthContext = Depends(require_permissions("finance.manage")),
    db: Session = Depends(get_db),
) -> dict:
    je = create_journal_entry(
        db,
        organization_id=ctx.organization.id,
        entry_date=payload.entry_date or date.today(),
        reference_type="MANUAL_JOURNAL",
        reference_id=None,
        reference_number=payload.reference_number or f"MJE-{int(datetime.now(timezone.utc).timestamp())}",
        description=payload.description,
        lines=[l.model_dump() for l in payload.lines],
        created_by_id=ctx.user.id,
        auto_post=payload.auto_post,
    )
    record_audit_log(
        db,
        ctx=ctx,
        action=f"JOURNAL_ENTRY_{je.status}",
        entity_type="JournalEntry",
        entity_id=je.id,
        after_state={"entry_number": je.entry_number, "total_debit": float(je.total_debit)},
    )
    db.commit()
    return {
        "id": je.id,
        "entry_number": je.entry_number,
        "status": je.status,
        "total_debit": float(je.total_debit),
        "total_credit": float(je.total_credit),
    }


@router.post("/finance/journal-entries/{entry_id}/post")
def post_existing_journal_entry(
    entry_id: str,
    ctx: AuthContext = Depends(require_permissions("finance.post")),
    db: Session = Depends(get_db),
) -> dict:
    je = post_journal_entry(
        db,
        organization_id=ctx.organization.id,
        entry_id=entry_id,
        posted_by_id=ctx.user.id,
    )
    record_audit_log(db, ctx=ctx, action="JOURNAL_ENTRY_POSTED", entity_type="JournalEntry", entity_id=je.id)
    db.commit()
    return {"id": je.id, "entry_number": je.entry_number, "status": je.status}


@router.post("/finance/journal-entries/{entry_id}/reverse")
def reverse_existing_journal_entry(
    entry_id: str,
    payload: JournalReverseSchema,
    ctx: AuthContext = Depends(require_permissions("finance.post")),
    db: Session = Depends(get_db),
) -> dict:
    rev = reverse_journal_entry(
        db,
        organization_id=ctx.organization.id,
        entry_id=entry_id,
        actor_user_id=ctx.user.id,
        reason=payload.reason,
    )
    record_audit_log(db, ctx=ctx, action="JOURNAL_ENTRY_REVERSED", entity_type="JournalEntry", entity_id=entry_id)
    db.commit()
    return {
        "original_entry_id": entry_id,
        "reversal_entry_id": rev.id,
        "reversal_entry_number": rev.entry_number,
        "status": "REVERSED",
    }


@router.get("/finance/expenses")
def list_expenses(
    ctx: AuthContext = Depends(require_any_permission("finance.view", "expenses.create")),
    db: Session = Depends(get_db),
) -> dict:
    exps = list(
        db.execute(
            select(Expense)
            .where(Expense.organization_id == ctx.organization.id)
            .order_by(Expense.expense_date.desc())
        ).scalars()
    )
    return {
        "items": [
            {
                "id": e.id,
                "expense_number": e.expense_number,
                "category": e.category,
                "vendor_name": e.vendor_name,
                "expense_date": e.expense_date.isoformat(),
                "amount": float(e.amount),
                "total_amount": float(e.total_amount),
                "status": e.status,
                "description": e.description,
                "journal_entry_id": e.journal_entry_id,
            }
            for e in exps
        ]
    }


@router.post("/finance/expenses", status_code=201)
def create_expense(
    payload: ExpenseCreateSchema,
    ctx: AuthContext = Depends(require_permissions("expenses.create")),
    db: Session = Depends(get_db),
) -> dict:
    cnt = (
        db.execute(
            select(func.count(Expense.id)).where(Expense.organization_id == ctx.organization.id)
        ).scalar_one()
        or 0
    )
    exp_no = f"EXP-{datetime.now(timezone.utc).year}-{cnt + 1:03d}"
    amt = quantize_money(payload.amount)

    acc = db.execute(
        select(Account).where(
            Account.organization_id == ctx.organization.id,
            Account.code == payload.expense_account_code,
        )
    ).scalar_one_or_none()
    if not acc:
        acc = db.execute(
            select(Account).where(
                Account.organization_id == ctx.organization.id,
                Account.account_type == "EXPENSE",
            )
        ).scalars().first()
    if not acc:
        raise NotFoundError("Expense GL account not found.")

    je = create_journal_entry(
        db,
        organization_id=ctx.organization.id,
        entry_date=date.today(),
        reference_type="OPERATING_EXPENSE",
        reference_id=None,
        reference_number=exp_no,
        description=f"Expense {exp_no} — {payload.vendor_name}",
        lines=[
            {"account_id": acc.id, "debit": amt, "credit": Decimal("0.00"), "department_id": payload.department_id},
            {"account_code": "1000", "debit": Decimal("0.00"), "credit": amt, "department_id": payload.department_id},
        ],
        created_by_id=ctx.user.id,
        auto_post=True,
    )

    exp = Expense(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        expense_number=exp_no,
        department_id=payload.department_id,
        expense_account_id=acc.id,
        submitted_by_id=ctx.user.id,
        category=payload.category,
        vendor_name=payload.vendor_name,
        expense_date=date.today(),
        amount=amt,
        tax_amount=Decimal("0.00"),
        total_amount=amt,
        status="PAID",
        journal_entry_id=je.id,
        description=payload.description,
    )
    db.add(exp)
    db.commit()
    return {
        "id": exp.id,
        "expense_number": exp.expense_number,
        "total_amount": float(exp.total_amount),
        "journal_entry_id": je.id,
    }


@router.get("/finance/trial-balance")
def get_trial_balance(
    ctx: AuthContext = Depends(require_permissions("finance.reports.view")),
    db: Session = Depends(get_db),
) -> dict:
    return compute_trial_balance(db, ctx.organization.id)


@router.get("/finance/profit-loss")
def get_profit_and_loss(
    ctx: AuthContext = Depends(require_permissions("finance.reports.view")),
    db: Session = Depends(get_db),
) -> dict:
    return compute_financial_statements(db, ctx.organization.id)["profit_and_loss"]


@router.get("/finance/balance-sheet")
def get_balance_sheet(
    ctx: AuthContext = Depends(require_permissions("finance.reports.view")),
    db: Session = Depends(get_db),
) -> dict:
    return compute_financial_statements(db, ctx.organization.id)["balance_sheet"]


@router.get("/finance/cash-flow")
def get_cash_flow(
    ctx: AuthContext = Depends(require_permissions("finance.reports.view")),
    db: Session = Depends(get_db),
) -> dict:
    return compute_financial_statements(db, ctx.organization.id)["cash_flow"]
