"""NEXORA ERP — Inventory & Multi-Warehouse Management API Router (/api/v1/inventory)."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, record_audit_log, require_permissions
from app.core.database import get_db
from app.core.exceptions import ConflictError, NotFoundError
from app.models.entities import (
    Product,
    ProductCategory,
    StockBalance,
    StockMovement,
    StockTransfer,
    Warehouse,
    new_uuid,
)
from app.services.inventory_service import (
    execute_stock_transfer,
    record_stock_movement,
)

router = APIRouter(prefix="/inventory", tags=["Inventory & Warehouses"])


class ProductCreateSchema(BaseModel):
    sku: str
    name: str
    category_id: Optional[str] = None
    uom: str = "PCS"
    cost_price: float
    selling_price: float
    reorder_level: float = 10.0
    reorder_quantity: float = 25.0
    lead_time_days: int = 7
    barcode: Optional[str] = None
    description: Optional[str] = None
    initial_stock: float = 0.0
    warehouse_id: Optional[str] = None


class WarehouseCreateSchema(BaseModel):
    name: str
    code: str
    branch_id: Optional[str] = None
    address: Optional[str] = None
    manager_name: Optional[str] = None
    capacity_units: int = 10000


class StockMovementCreateSchema(BaseModel):
    product_id: str
    warehouse_id: str
    movement_type: str  # RECEIPT, ISSUE, ADJUSTMENT_IN, ADJUSTMENT_OUT
    quantity: float
    unit_cost: Optional[float] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class TransferItemSchema(BaseModel):
    product_id: str
    quantity: float


class StockTransferCreateSchema(BaseModel):
    from_warehouse_id: str
    to_warehouse_id: str
    items: list[TransferItemSchema]
    notes: Optional[str] = None


@router.get("/categories")
def list_categories(
    ctx: AuthContext = Depends(require_permissions("inventory.view")),
    db: Session = Depends(get_db),
) -> dict:
    cats = list(
        db.execute(
            select(ProductCategory)
            .where(ProductCategory.organization_id == ctx.organization.id)
            .order_by(ProductCategory.name)
        ).scalars()
    )
    return {"items": [{"id": c.id, "code": c.code, "name": c.name} for c in cats]}


@router.get("/products")
def list_products(
    search: Optional[str] = Query(default=None),
    category_id: Optional[str] = Query(default=None),
    low_stock_only: bool = Query(default=False),
    ctx: AuthContext = Depends(require_permissions("inventory.view")),
    db: Session = Depends(get_db),
) -> dict:
    stmt = (
        select(Product, ProductCategory.name)
        .join(ProductCategory, ProductCategory.id == Product.category_id)
        .where(Product.organization_id == ctx.organization.id)
        .order_by(Product.sku)
    )
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)

    rows = db.execute(stmt).all()
    stock_rows = db.execute(
        select(
            StockBalance.product_id,
            func.coalesce(func.sum(StockBalance.quantity_on_hand), 0),
            func.coalesce(func.sum(StockBalance.quantity_available), 0),
            func.coalesce(func.sum(StockBalance.total_valuation), 0),
        )
        .where(StockBalance.organization_id == ctx.organization.id)
        .group_by(StockBalance.product_id)
    ).all()
    stock_map = {r[0]: (float(r[1]), float(r[2]), float(r[3])) for r in stock_rows}

    items = []
    for prod, cat_name in rows:
        if search and search.lower() not in prod.name.lower() and search.lower() not in prod.sku.lower():
            continue
        on_hand, avail, val = stock_map.get(prod.id, (0.0, 0.0, 0.0))
        is_low = avail <= float(prod.reorder_level)
        if low_stock_only and not is_low:
            continue

        items.append(
            {
                "id": prod.id,
                "sku": prod.sku,
                "barcode": prod.barcode,
                "qr_code": prod.qr_code,
                "name": prod.name,
                "category_id": prod.category_id,
                "category_name": cat_name,
                "uom": prod.uom,
                "cost_price": float(prod.cost_price),
                "weighted_avg_cost": float(prod.weighted_avg_cost),
                "selling_price": float(prod.selling_price),
                "reorder_level": float(prod.reorder_level),
                "reorder_quantity": float(prod.reorder_quantity),
                "lead_time_days": prod.lead_time_days,
                "quantity_on_hand": on_hand,
                "quantity_available": avail,
                "total_valuation": val,
                "is_low_stock": is_low,
                "is_out_of_stock": avail <= 0.0,
            }
        )

    return {"items": items, "total": len(items)}


@router.post("/products", status_code=201)
def create_product(
    payload: ProductCreateSchema,
    ctx: AuthContext = Depends(require_permissions("inventory.manage")),
    db: Session = Depends(get_db),
) -> dict:
    existing = db.execute(
        select(Product).where(
            Product.organization_id == ctx.organization.id,
            Product.sku == payload.sku.upper(),
        )
    ).scalar_one_or_none()
    if existing:
        raise ConflictError(f"Product with SKU '{payload.sku}' already exists.")

    cat_id = payload.category_id
    if not cat_id:
        cat = db.execute(
            select(ProductCategory).where(ProductCategory.organization_id == ctx.organization.id)
        ).scalars().first()
        if not cat:
            cat = ProductCategory(
                id=new_uuid(),
                organization_id=ctx.organization.id,
                code="CAT-GEN",
                name="General Merchandise",
            )
            db.add(cat)
            db.flush()
        cat_id = cat.id

    cost_dec = Decimal(str(payload.cost_price))
    prod = Product(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        category_id=cat_id,
        sku=payload.sku.upper(),
        barcode=payload.barcode or f"4792026{int(datetime.now(timezone.utc).timestamp()) % 100000:05d}",
        qr_code=f"NEXORA://{payload.sku.upper()}",
        name=payload.name,
        description=payload.description,
        uom=payload.uom.upper(),
        cost_price=cost_dec,
        weighted_avg_cost=cost_dec,
        selling_price=Decimal(str(payload.selling_price)),
        reorder_level=Decimal(str(payload.reorder_level)),
        reorder_quantity=Decimal(str(payload.reorder_quantity)),
        lead_time_days=payload.lead_time_days,
    )
    db.add(prod)
    db.flush()

    if payload.initial_stock and payload.initial_stock > 0:
        wh_id = payload.warehouse_id
        if not wh_id:
            wh = db.execute(
                select(Warehouse).where(Warehouse.organization_id == ctx.organization.id)
            ).scalars().first()
            if wh:
                wh_id = wh.id
        if wh_id:
            record_stock_movement(
                db,
                organization_id=ctx.organization.id,
                product_id=prod.id,
                warehouse_id=wh_id,
                movement_type="RECEIPT",
                quantity=payload.initial_stock,
                unit_cost=cost_dec,
                reference_type="INITIAL_STOCK",
                reference_id=prod.id,
                reference_number=f"INIT-{prod.sku}",
                performed_by_id=ctx.user.id,
                notes="Initial stock registration",
            )

    record_audit_log(db, ctx=ctx, action="PRODUCT_CREATED", entity_type="Product", entity_id=prod.id)
    db.commit()
    return {
        "id": prod.id,
        "sku": prod.sku,
        "name": prod.name,
        "cost_price": float(prod.cost_price),
        "weighted_avg_cost": float(prod.weighted_avg_cost),
        "selling_price": float(prod.selling_price),
    }


@router.get("/warehouses")
def list_warehouses(
    ctx: AuthContext = Depends(require_permissions("inventory.view")),
    db: Session = Depends(get_db),
) -> dict:
    warehouses = list(
        db.execute(
            select(Warehouse)
            .where(Warehouse.organization_id == ctx.organization.id)
            .order_by(Warehouse.code)
        ).scalars()
    )
    wh_stats = db.execute(
        select(
            StockBalance.warehouse_id,
            func.count(StockBalance.product_id),
            func.coalesce(func.sum(StockBalance.quantity_on_hand), 0),
            func.coalesce(func.sum(StockBalance.total_valuation), 0),
        )
        .where(StockBalance.organization_id == ctx.organization.id)
        .group_by(StockBalance.warehouse_id)
    ).all()
    stat_map = {r[0]: (int(r[1]), float(r[2]), float(r[3])) for r in wh_stats}

    items = []
    for w in warehouses:
        sku_cnt, tot_qty, tot_val = stat_map.get(w.id, (0, 0.0, 0.0))
        items.append(
            {
                "id": w.id,
                "code": w.code,
                "name": w.name,
                "branch_id": w.branch_id,
                "address": w.address,
                "manager_name": w.manager_name,
                "capacity_units": w.capacity_units,
                "sku_count": sku_cnt,
                "total_units": tot_qty,
                "total_valuation": tot_val,
                "utilization_percent": round(min(100.0, (tot_qty / max(1, w.capacity_units)) * 100.0), 1),
            }
        )
    return {"items": items}


@router.get("/movements")
def list_movements(
    ctx: AuthContext = Depends(require_permissions("inventory.view")),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.execute(
        select(StockMovement, Product.sku, Product.name, Warehouse.name)
        .join(Product, Product.id == StockMovement.product_id)
        .join(Warehouse, Warehouse.id == StockMovement.warehouse_id)
        .where(StockMovement.organization_id == ctx.organization.id)
        .order_by(StockMovement.created_at.desc())
        .limit(100)
    ).all()
    return {
        "items": [
            {
                "id": m.id,
                "product_id": m.product_id,
                "sku": sku,
                "product_name": p_name,
                "warehouse_id": m.warehouse_id,
                "warehouse_name": w_name,
                "movement_type": m.movement_type,
                "reference_type": m.reference_type,
                "reference_number": m.reference_number,
                "quantity": float(m.quantity),
                "balance_after": float(m.balance_after),
                "unit_cost": float(m.unit_cost),
                "notes": m.notes,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m, sku, p_name, w_name in rows
        ]
    }


@router.post("/movements", status_code=201)
def create_movement(
    payload: StockMovementCreateSchema,
    ctx: AuthContext = Depends(require_permissions("inventory.adjust")),
    db: Session = Depends(get_db),
) -> dict:
    ref_no = payload.reference_number or f"MOV-{int(datetime.now(timezone.utc).timestamp())}"
    mov = record_stock_movement(
        db,
        organization_id=ctx.organization.id,
        product_id=payload.product_id,
        warehouse_id=payload.warehouse_id,
        movement_type=payload.movement_type.upper(),
        quantity=payload.quantity,
        unit_cost=payload.unit_cost,
        reference_type="MANUAL_MOVEMENT",
        reference_id=None,
        reference_number=ref_no,
        performed_by_id=ctx.user.id,
        notes=payload.notes,
    )
    record_audit_log(
        db,
        ctx=ctx,
        action=f"STOCK_{mov.movement_type}",
        entity_type="StockMovement",
        entity_id=mov.id,
        after_state={"quantity": float(mov.quantity), "balance_after": float(mov.balance_after)},
    )
    prod = db.execute(select(Product).where(Product.id == mov.product_id)).scalar_one()
    db.commit()
    return {
        "id": mov.id,
        "movement_type": mov.movement_type,
        "quantity": float(mov.quantity),
        "balance_after": float(mov.balance_after),
        "unit_cost": float(mov.unit_cost),
        "weighted_avg_cost": float(prod.weighted_avg_cost),
        "reference_number": mov.reference_number,
    }


@router.post("/transfers", status_code=201)
def create_transfer(
    payload: StockTransferCreateSchema,
    ctx: AuthContext = Depends(require_permissions("inventory.transfer")),
    db: Session = Depends(get_db),
) -> dict:
    transfer = execute_stock_transfer(
        db,
        organization_id=ctx.organization.id,
        from_warehouse_id=payload.from_warehouse_id,
        to_warehouse_id=payload.to_warehouse_id,
        items=[{"product_id": i.product_id, "quantity": i.quantity} for i in payload.items],
        initiated_by_id=ctx.user.id,
        notes=payload.notes,
    )
    record_audit_log(
        db,
        ctx=ctx,
        action="STOCK_TRANSFER_COMPLETED",
        entity_type="StockTransfer",
        entity_id=transfer.id,
    )
    db.commit()
    return {
        "id": transfer.id,
        "transfer_number": transfer.transfer_number,
        "status": transfer.status,
    }


@router.get("/stock-summary")
def get_stock_summary(
    ctx: AuthContext = Depends(require_permissions("inventory.view")),
    db: Session = Depends(get_db),
) -> dict:
    products_resp = list_products(search=None, category_id=None, low_stock_only=False, ctx=ctx, db=db)
    warehouses_resp = list_warehouses(ctx=ctx, db=db)
    items = products_resp["items"]

    total_valuation = round(sum(p["total_valuation"] for p in items), 2)
    low_stock_count = sum(1 for p in items if p["is_low_stock"])
    out_of_stock_count = sum(1 for p in items if p["is_out_of_stock"])

    return {
        "total_products": len(items),
        "total_inventory_valuation_lkr": total_valuation,
        "low_stock_products_count": low_stock_count,
        "out_of_stock_products_count": out_of_stock_count,
        "warehouses": warehouses_resp["items"],
        "low_stock_items": [p for p in items if p["is_low_stock"]][:15],
    }
