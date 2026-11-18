"""NEXORA ERP — Inventory & Weighted Average Costing Service Layer."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.entities import (
    Notification,
    Product,
    StockBalance,
    StockMovement,
    StockTransfer,
    StockTransferItem,
    Warehouse,
    new_uuid,
)
from app.services.accounting_service import quantize_money


def get_or_create_stock_balance(
    db: Session,
    *,
    organization_id: str,
    product_id: str,
    warehouse_id: str,
) -> StockBalance:
    stmt = select(StockBalance).where(
        StockBalance.organization_id == organization_id,
        StockBalance.product_id == product_id,
        StockBalance.warehouse_id == warehouse_id,
    )
    bal = db.execute(stmt).scalar_one_or_none()
    if not bal:
        product = db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.organization_id == organization_id,
            )
        ).scalar_one_or_none()
        if not product:
            raise NotFoundError("Product not found in organization.")

        warehouse = db.execute(
            select(Warehouse).where(
                Warehouse.id == warehouse_id,
                Warehouse.organization_id == organization_id,
            )
        ).scalar_one_or_none()
        if not warehouse:
            raise NotFoundError("Warehouse not found in organization.")

        bal = StockBalance(
            id=new_uuid(),
            organization_id=organization_id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity_on_hand=Decimal("0.00"),
            quantity_reserved=Decimal("0.00"),
            quantity_available=Decimal("0.00"),
            unit_cost=product.weighted_avg_cost or product.cost_price,
            total_valuation=Decimal("0.00"),
        )
        db.add(bal)
        db.flush()
    return bal


def record_stock_movement(
    db: Session,
    *,
    organization_id: str,
    product_id: str,
    warehouse_id: str,
    movement_type: str,
    quantity: Decimal | float | str,
    unit_cost: Decimal | float | str | None,
    reference_type: str,
    reference_id: str | None,
    reference_number: str,
    performed_by_id: str,
    notes: str | None = None,
) -> StockMovement:
    """Execute an atomic inventory movement with Weighted Average Costing and Negative Stock Prevention."""
    qty = quantize_money(quantity)
    if qty <= Decimal("0.00"):
        raise BusinessRuleError("Stock movement quantity must be strictly positive.", code="INVALID_QUANTITY")

    product = db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.organization_id == organization_id,
        )
    ).scalar_one_or_none()
    if not product:
        raise NotFoundError("Product not found in organization.")

    bal = get_or_create_stock_balance(
        db,
        organization_id=organization_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
    )

    inbound_types = {"RECEIPT", "ADJUSTMENT_IN", "TRANSFER_IN", "RETURN"}
    outbound_types = {"ISSUE", "ADJUSTMENT_OUT", "TRANSFER_OUT"}

    effective_cost = (
        quantize_money(unit_cost)
        if unit_cost is not None
        else quantize_money(product.weighted_avg_cost or product.cost_price)
    )

    if movement_type in inbound_types:
        old_qty = quantize_money(bal.quantity_on_hand)
        old_cost = quantize_money(bal.unit_cost or product.weighted_avg_cost)
        new_qty = old_qty + qty

        if new_qty > Decimal("0.00"):
            new_wac = quantize_money(((old_qty * old_cost) + (qty * effective_cost)) / new_qty)
        else:
            new_wac = effective_cost

        bal.quantity_on_hand = new_qty
        bal.quantity_available = new_qty - quantize_money(bal.quantity_reserved)
        bal.unit_cost = new_wac
        bal.total_valuation = quantize_money(new_qty * new_wac)
        product.weighted_avg_cost = new_wac

    elif movement_type in outbound_types:
        available = quantize_money(bal.quantity_available)
        if available < qty:
            raise BusinessRuleError(
                f"Insufficient stock for SKU '{product.sku}' ({product.name}): "
                f"requested {qty}, available {available}. Negative stock is prohibited.",
                code="INSUFFICIENT_STOCK",
                details={
                    "sku": product.sku,
                    "requested": float(qty),
                    "available": float(available),
                },
            )
        new_qty = quantize_money(bal.quantity_on_hand) - qty
        bal.quantity_on_hand = new_qty
        bal.quantity_available = new_qty - quantize_money(bal.quantity_reserved)
        effective_cost = quantize_money(bal.unit_cost or product.weighted_avg_cost)
        bal.total_valuation = quantize_money(new_qty * effective_cost)

        # Trigger Low-Stock Alert notification if stock falls at or below reorder_level
        if new_qty <= quantize_money(product.reorder_level):
            db.add(
                Notification(
                    id=new_uuid(),
                    organization_id=organization_id,
                    user_id=None,
                    title=f"Low Stock Alert: {product.sku}",
                    message=(
                        f"{product.name} ({product.sku}) has dropped to {new_qty} {product.uom} "
                        f"(Reorder Level: {product.reorder_level} {product.uom})."
                    ),
                    category="INVENTORY",
                    severity="WARNING" if new_qty > 0 else "CRITICAL",
                    action_url="/inventory",
                )
            )
    else:
        raise BusinessRuleError(f"Unsupported stock movement type: {movement_type}")

    movement = StockMovement(
        id=new_uuid(),
        organization_id=organization_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
        reference_type=reference_type,
        reference_id=reference_id,
        reference_number=reference_number,
        quantity=qty,
        balance_after=bal.quantity_on_hand,
        unit_cost=effective_cost,
        performed_by_id=performed_by_id,
        notes=notes,
    )
    db.add(movement)
    db.flush()
    return movement


def execute_stock_transfer(
    db: Session,
    *,
    organization_id: str,
    from_warehouse_id: str,
    to_warehouse_id: str,
    items: list[dict],
    initiated_by_id: str,
    notes: str | None = None,
) -> StockTransfer:
    """Transfer stock between two warehouses (supports full or partial transfer quantities)."""
    if from_warehouse_id == to_warehouse_id:
        raise BusinessRuleError("Source and destination warehouses must be different.", code="INVALID_TRANSFER")
    if not items:
        raise BusinessRuleError("At least one product item is required for a stock transfer.")

    count = (
        db.execute(
            select(func.count(StockTransfer.id)).where(
                StockTransfer.organization_id == organization_id
            )
        ).scalar_one()
        or 0
    )
    transfer_number = f"STR-{datetime.now(timezone.utc).year}-{count + 1:04d}"

    transfer = StockTransfer(
        id=new_uuid(),
        organization_id=organization_id,
        transfer_number=transfer_number,
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
        status="COMPLETED",
        initiated_by_id=initiated_by_id,
        completed_by_id=initiated_by_id,
        notes=notes,
    )
    db.add(transfer)
    db.flush()

    for item in items:
        product_id = item["product_id"]
        req_qty = quantize_money(item.get("requested_qty", item.get("quantity", 0)))
        trans_qty = quantize_money(item.get("transferred_qty", req_qty))

        out_mov = record_stock_movement(
            db,
            organization_id=organization_id,
            product_id=product_id,
            warehouse_id=from_warehouse_id,
            movement_type="TRANSFER_OUT",
            quantity=trans_qty,
            unit_cost=None,
            reference_type="STOCK_TRANSFER",
            reference_id=transfer.id,
            reference_number=transfer_number,
            performed_by_id=initiated_by_id,
            notes=f"Transfer out to warehouse {to_warehouse_id}",
        )
        record_stock_movement(
            db,
            organization_id=organization_id,
            product_id=product_id,
            warehouse_id=to_warehouse_id,
            movement_type="TRANSFER_IN",
            quantity=trans_qty,
            unit_cost=out_mov.unit_cost,
            reference_type="STOCK_TRANSFER",
            reference_id=transfer.id,
            reference_number=transfer_number,
            performed_by_id=initiated_by_id,
            notes=f"Transfer in from warehouse {from_warehouse_id}",
        )

        db.add(
            StockTransferItem(
                id=new_uuid(),
                transfer_id=transfer.id,
                product_id=product_id,
                requested_qty=req_qty,
                transferred_qty=trans_qty,
                unit_cost=out_mov.unit_cost,
            )
        )

    db.flush()
    return transfer
