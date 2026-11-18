"""NEXORA ERP — Dedicated Double-Entry Accounting & General Ledger Service Layer."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.entities import (
    Account,
    JournalEntry,
    JournalLine,
    new_uuid,
)

TWOPLACES = Decimal("0.01")


def quantize_money(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES)


def get_account_by_code(db: Session, organization_id: str, code: str) -> Account:
    stmt = select(Account).where(
        Account.organization_id == organization_id,
        Account.code == code,
    )
    acc = db.execute(stmt).scalar_one_or_none()
    if not acc:
        raise NotFoundError(f"GL Account code '{code}' not found for organization.")
    return acc


def next_journal_number(db: Session, organization_id: str) -> str:
    count = (
        db.execute(
            select(func.count(JournalEntry.id)).where(
                JournalEntry.organization_id == organization_id
            )
        ).scalar_one()
        or 0
    )
    return f"JE-{datetime.now(timezone.utc).year}-{count + 1:05d}"


def create_journal_entry(
    db: Session,
    *,
    organization_id: str,
    entry_date: date,
    reference_type: str,
    reference_id: str | None,
    reference_number: str,
    description: str,
    lines: list[dict[str, Any]],
    created_by_id: str,
    auto_post: bool = True,
    idempotency_key: str | None = None,
) -> JournalEntry:
    """Create (and optionally post) a double-entry journal entry.

    Enforces:
    1. At least 2 journal lines.
    2. Every line has non-negative debit/credit and not both > 0 on the same line.
    3. Total Debits == Total Credits > 0 before posting.
    4. Idempotency check if idempotency_key is provided.
    """
    if idempotency_key:
        existing = db.execute(
            select(JournalEntry).where(JournalEntry.idempotency_key == idempotency_key)
        ).scalar_one_or_none()
        if existing:
            return existing

    if len(lines) < 2:
        raise BusinessRuleError(
            "A double-entry journal entry requires at least two lines.",
            code="UNBALANCED_JOURNAL",
        )

    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")
    validated_lines: list[dict[str, Any]] = []

    for idx, line in enumerate(lines, start=1):
        debit = quantize_money(line.get("debit", 0))
        credit = quantize_money(line.get("credit", 0))
        if debit < Decimal("0.00") or credit < Decimal("0.00"):
            raise BusinessRuleError(
                f"Line {idx}: Debit and credit amounts must be non-negative.",
                code="INVALID_JOURNAL_LINE",
            )
        if debit > Decimal("0.00") and credit > Decimal("0.00"):
            raise BusinessRuleError(
                f"Line {idx}: A single journal line cannot have both debit and credit.",
                code="INVALID_JOURNAL_LINE",
            )
        if debit == Decimal("0.00") and credit == Decimal("0.00"):
            raise BusinessRuleError(
                f"Line {idx}: Journal line must have a non-zero debit or credit.",
                code="ZERO_JOURNAL_LINE",
            )

        account_id = line.get("account_id")
        account_code = line.get("account_code")
        if account_id:
            acc = db.execute(
                select(Account).where(
                    Account.id == account_id,
                    Account.organization_id == organization_id,
                )
            ).scalar_one_or_none()
            if not acc:
                raise NotFoundError(f"Line {idx}: GL Account '{account_id}' not found in tenant.")
        elif account_code:
            acc = get_account_by_code(db, organization_id, str(account_code))
        else:
            raise BusinessRuleError(f"Line {idx}: Missing account_id or account_code.")

        total_debit += debit
        total_credit += credit
        validated_lines.append(
            {
                "account": acc,
                "description": line.get("description") or description,
                "debit": debit,
                "credit": credit,
                "department_id": line.get("department_id"),
                "branch_id": line.get("branch_id"),
            }
        )

    if auto_post and total_debit != total_credit:
        raise BusinessRuleError(
            f"Unbalanced journal entry rejected: Total Debits ({total_debit}) != Total Credits ({total_credit}).",
            code="UNBALANCED_JOURNAL",
            details={"total_debit": str(total_debit), "total_credit": str(total_credit)},
        )

    entry = JournalEntry(
        id=new_uuid(),
        organization_id=organization_id,
        entry_number=next_journal_number(db, organization_id),
        entry_date=entry_date,
        reference_type=reference_type,
        reference_id=reference_id,
        reference_number=reference_number,
        description=description,
        status="DRAFT",
        total_debit=total_debit,
        total_credit=total_credit,
        idempotency_key=idempotency_key,
        created_by_id=created_by_id,
    )
    db.add(entry)
    db.flush()

    for vl in validated_lines:
        jl = JournalLine(
            id=new_uuid(),
            journal_entry_id=entry.id,
            organization_id=organization_id,
            account_id=vl["account"].id,
            description=vl["description"],
            debit=vl["debit"],
            credit=vl["credit"],
            department_id=vl["department_id"],
            branch_id=vl["branch_id"],
        )
        db.add(jl)

    db.flush()

    if auto_post:
        post_journal_entry(db, organization_id=organization_id, entry_id=entry.id, posted_by_id=created_by_id)

    return entry


def post_journal_entry(
    db: Session,
    *,
    organization_id: str,
    entry_id: str,
    posted_by_id: str,
) -> JournalEntry:
    """Validate and post a DRAFT journal entry, updating GL account balances atomically."""
    entry = db.execute(
        select(JournalEntry).where(
            JournalEntry.id == entry_id,
            JournalEntry.organization_id == organization_id,
        )
    ).scalar_one_or_none()
    if not entry:
        raise NotFoundError("Journal entry not found.")
    if entry.status == "POSTED":
        raise BusinessRuleError(
            "Journal entry is already posted and immutable. Use a reversal entry for corrections.",
            code="JOURNAL_ALREADY_POSTED",
        )
    if entry.status == "REVERSED":
        raise BusinessRuleError("Reversed journal entry cannot be reposted.", code="JOURNAL_REVERSED")

    lines = list(
        db.execute(
            select(JournalLine).where(JournalLine.journal_entry_id == entry.id)
        ).scalars()
    )
    if len(lines) < 2:
        raise BusinessRuleError("Journal entry must have at least 2 lines.", code="UNBALANCED_JOURNAL")

    sum_debit = sum((quantize_money(l.debit) for l in lines), Decimal("0.00"))
    sum_credit = sum((quantize_money(l.credit) for l in lines), Decimal("0.00"))

    if sum_debit <= Decimal("0.00") or sum_debit != sum_credit:
        raise BusinessRuleError(
            f"Cannot post unbalanced journal entry: Debits ({sum_debit}) != Credits ({sum_credit}).",
            code="UNBALANCED_JOURNAL",
        )

    for line in lines:
        acc = db.execute(select(Account).where(Account.id == line.account_id)).scalar_one()
        if acc.normal_balance == "DEBIT":
            acc.current_balance = quantize_money(acc.current_balance + line.debit - line.credit)
        else:
            acc.current_balance = quantize_money(acc.current_balance + line.credit - line.debit)

    entry.total_debit = sum_debit
    entry.total_credit = sum_credit
    entry.status = "POSTED"
    entry.posted_by_id = posted_by_id
    entry.posted_at = datetime.now(timezone.utc)
    db.flush()
    return entry


def reverse_journal_entry(
    db: Session,
    *,
    organization_id: str,
    entry_id: str,
    actor_user_id: str,
    reason: str,
) -> JournalEntry:
    """Create and post an inverting reversal journal entry for an immutable posted entry."""
    original = db.execute(
        select(JournalEntry).where(
            JournalEntry.id == entry_id,
            JournalEntry.organization_id == organization_id,
        )
    ).scalar_one_or_none()
    if not original:
        raise NotFoundError("Original journal entry not found.")
    if original.status != "POSTED":
        raise BusinessRuleError(
            "Only POSTED journal entries can be reversed.",
            code="INVALID_JOURNAL_STATE",
        )

    orig_lines = list(
        db.execute(
            select(JournalLine).where(JournalLine.journal_entry_id == original.id)
        ).scalars()
    )
    inverted_lines = [
        {
            "account_id": line.account_id,
            "description": f"Reversal of {original.entry_number}: {line.description or ''}",
            "debit": line.credit,
            "credit": line.debit,
            "department_id": line.department_id,
            "branch_id": line.branch_id,
        }
        for line in orig_lines
    ]

    reversal = create_journal_entry(
        db,
        organization_id=organization_id,
        entry_date=date.today(),
        reference_type="JOURNAL_REVERSAL",
        reference_id=original.id,
        reference_number=original.entry_number,
        description=f"Reversal of {original.entry_number} — {reason}",
        lines=inverted_lines,
        created_by_id=actor_user_id,
        auto_post=True,
    )
    reversal.reversal_of_id = original.id
    original.status = "REVERSED"
    db.flush()
    return reversal


def compute_trial_balance(db: Session, organization_id: str) -> dict[str, Any]:
    """Compute live Trial Balance from posted journal lines."""
    accounts = list(
        db.execute(
            select(Account)
            .where(Account.organization_id == organization_id)
            .order_by(Account.code)
        ).scalars()
    )
    sums = db.execute(
        select(
            JournalLine.account_id,
            func.coalesce(func.sum(JournalLine.debit), 0),
            func.coalesce(func.sum(JournalLine.credit), 0),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            JournalLine.organization_id == organization_id,
            JournalEntry.status.in_(["POSTED", "REVERSED"]),
        )
        .group_by(JournalLine.account_id)
    ).all()
    sum_map = {row[0]: (quantize_money(row[1]), quantize_money(row[2])) for row in sums}

    rows = []
    grand_debit = Decimal("0.00")
    grand_credit = Decimal("0.00")

    for acc in accounts:
        raw_debit, raw_credit = sum_map.get(acc.id, (Decimal("0.00"), Decimal("0.00")))
        net = raw_debit - raw_credit
        debit_bal = net if net > Decimal("0.00") else Decimal("0.00")
        credit_bal = -net if net < Decimal("0.00") else Decimal("0.00")
        grand_debit += debit_bal
        grand_credit += credit_bal
        rows.append(
            {
                "account_id": acc.id,
                "code": acc.code,
                "name": acc.name,
                "account_type": acc.account_type,
                "account_subtype": acc.account_subtype,
                "period_debit": float(raw_debit),
                "period_credit": float(raw_credit),
                "debit_balance": float(debit_bal),
                "credit_balance": float(credit_bal),
            }
        )

    return {
        "accounts": rows,
        "total_debit": float(grand_debit),
        "total_credit": float(grand_credit),
        "is_balanced": grand_debit == grand_credit,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def compute_financial_statements(db: Session, organization_id: str) -> dict[str, Any]:
    """Compute Income Statement (P&L), Balance Sheet, and Cash Flow from posted ledger lines."""
    tb = compute_trial_balance(db, organization_id)
    revenues = []
    cogs = []
    operating_expenses = []
    assets = []
    liabilities = []
    equity = []

    total_revenue = Decimal("0.00")
    total_cogs = Decimal("0.00")
    total_opex = Decimal("0.00")
    total_assets = Decimal("0.00")
    total_liabilities = Decimal("0.00")
    total_equity = Decimal("0.00")
    cash_and_bank = Decimal("0.00")

    for item in tb["accounts"]:
        acc_type = item["account_type"]
        subtype = item["account_subtype"]
        debit_bal = quantize_money(item["debit_balance"])
        credit_bal = quantize_money(item["credit_balance"])

        if acc_type == "REVENUE":
            amt = credit_bal - debit_bal
            total_revenue += amt
            revenues.append({**item, "amount": float(amt)})
        elif acc_type == "EXPENSE":
            amt = debit_bal - credit_bal
            if subtype == "COGS":
                total_cogs += amt
                cogs.append({**item, "amount": float(amt)})
            else:
                total_opex += amt
                operating_expenses.append({**item, "amount": float(amt)})
        elif acc_type == "ASSET":
            amt = debit_bal - credit_bal
            total_assets += amt
            if subtype == "CASH_BANK":
                cash_and_bank += amt
            assets.append({**item, "amount": float(amt)})
        elif acc_type == "LIABILITY":
            amt = credit_bal - debit_bal
            total_liabilities += amt
            liabilities.append({**item, "amount": float(amt)})
        elif acc_type == "EQUITY":
            amt = credit_bal - debit_bal
            total_equity += amt
            equity.append({**item, "amount": float(amt)})

    gross_profit = total_revenue - total_cogs
    net_profit = gross_profit - total_opex
    total_equity_with_earnings = total_equity + net_profit

    return {
        "profit_and_loss": {
            "revenues": revenues,
            "cogs": cogs,
            "operating_expenses": operating_expenses,
            "total_revenue": float(total_revenue),
            "total_cogs": float(total_cogs),
            "gross_profit": float(gross_profit),
            "gross_margin_percent": float(
                (gross_profit / total_revenue * 100) if total_revenue > 0 else Decimal("0.00")
            ),
            "total_operating_expenses": float(total_opex),
            "total_expenses": float(total_cogs + total_opex),
            "net_profit": float(net_profit),
            "net_margin_percent": float(
                (net_profit / total_revenue * 100) if total_revenue > 0 else Decimal("0.00")
            ),
        },
        "balance_sheet": {
            "assets": assets,
            "liabilities": liabilities,
            "equity": equity,
            "current_period_net_profit": float(net_profit),
            "total_assets": float(total_assets),
            "total_liabilities": float(total_liabilities),
            "total_equity": float(total_equity_with_earnings),
            "total_liabilities_and_equity": float(total_liabilities + total_equity_with_earnings),
            "is_balanced": total_assets == (total_liabilities + total_equity_with_earnings),
        },
        "cash_flow": {
            "cash_and_bank_ending_balance": float(cash_and_bank),
            "operating_cash_flow": float(net_profit),
            "investing_cash_flow": 0.0,
            "financing_cash_flow": float(total_equity),
        },
    }
