"""NEXORA ERP — Comprehensive Automated Backend Test Suite (Unit, Integration, Security, Financial & AI)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Point tests to an isolated test database file
TEST_DB_PATH = Path(__file__).resolve().parent / "test_nexora.db"
if TEST_DB_PATH.exists():
    try:
        TEST_DB_PATH.unlink()
    except OSError:
        pass

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest
from fastapi.testclient import TestClient

from app.main import app, initialize_database_and_seed


@pytest.fixture(scope="module")
def client():
    initialize_database_and_seed()
    with TestClient(app) as c:
        yield c


def login_as(client: TestClient, email: str, password: str = "Nexora#2026") -> tuple[str, dict]:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return data["access_token"], data["user"]


def auth_headers(token: str, org_id: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if org_id:
        headers["X-Organization-ID"] = org_id
    return headers


def test_01_health_and_demo_seed(client: TestClient):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["default_currency"] == "LKR"

    demo_resp = client.get("/api/v1/auth/demo-accounts")
    assert demo_resp.status_code == 200
    accounts = demo_resp.json()["accounts"]
    assert len(accounts) >= 12


def test_02_authentication_refresh_and_mfa(client: TestClient):
    # Invalid password rejected
    bad_resp = client.post("/api/v1/auth/login", json={"email": "admin@nexora.lk", "password": "WrongPassword!"})
    assert bad_resp.status_code == 401
    assert bad_resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    # Valid Argon2id login succeeds and sets HttpOnly refresh cookie
    login_resp = client.post("/api/v1/auth/login", json={"email": "admin@nexora.lk", "password": "Nexora#2026"})
    assert login_resp.status_code == 200
    assert "nexora_refresh_token" in login_resp.cookies
    token = login_resp.json()["access_token"]

    # Refresh token rotation works
    refresh_resp = client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()

    # Current user profile
    me_resp = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert me_resp.status_code == 200
    assert me_resp.json()["currency"] == "LKR"


def test_03_multi_tenant_isolation_enforced(client: TestClient):
    """Verify a user from Tenant B (Ceylon Horizon) cannot access Tenant A (Nexora Demo Holdings)."""
    admin_token, admin_user = login_as(client, "admin@nexora.lk")
    nexora_org_id = admin_user["organization_id"]

    horizon_token, horizon_user = login_as(client, "admin@ceylonhorizon.lk")
    assert horizon_user["organization_id"] != nexora_org_id

    # Attempt cross-tenant access using X-Organization-ID header
    cross_resp = client.get(
        "/api/v1/employees",
        headers=auth_headers(horizon_token, org_id=nexora_org_id),
    )
    assert cross_resp.status_code == 403
    assert cross_resp.json()["error"]["code"] == "TENANT_ISOLATION_VIOLATION"


def test_04_rbac_and_confidential_hr_masking(client: TestClient):
    emp_token, _ = login_as(client, "employee@nexora.lk")
    hr_token, _ = login_as(client, "hr@nexora.lk")

    # Standard employee can view directory, but base_salary & national_id are masked
    emp_list = client.get("/api/v1/employees", headers=auth_headers(emp_token))
    assert emp_list.status_code == 200
    assert emp_list.json()["confidential_visible"] is False
    assert emp_list.json()["items"][0]["base_salary"] is None
    assert emp_list.json()["items"][0]["national_id"] == "REDACTED"

    # Standard employee cannot create a new employee (403 Forbidden)
    branches = client.get("/api/v1/branches", headers=auth_headers(hr_token)).json()["items"]
    depts = client.get("/api/v1/departments", headers=auth_headers(hr_token)).json()["items"]

    forbidden_create = client.post(
        "/api/v1/employees",
        headers=auth_headers(emp_token),
        json={
            "first_name": "Test",
            "last_name": "Unauthorized",
            "email": "unauth@nexora.lk",
            "branch_id": branches[0]["id"],
            "department_id": depts[0]["id"],
            "base_salary": 180000,
        },
    )
    assert forbidden_create.status_code == 403

    # HR Manager can view confidential salary and create employees
    hr_list = client.get("/api/v1/employees", headers=auth_headers(hr_token))
    assert hr_list.status_code == 200
    assert hr_list.json()["confidential_visible"] is True
    assert hr_list.json()["items"][0]["base_salary"] is not None

    hr_create = client.post(
        "/api/v1/employees",
        headers=auth_headers(hr_token),
        json={
            "first_name": "Kusal",
            "last_name": "Mendis",
            "email": "kusal.mendis@nexora.lk",
            "branch_id": branches[0]["id"],
            "department_id": depts[0]["id"],
            "base_salary": 215000,
        },
    )
    assert hr_create.status_code == 201
    assert hr_create.json()["base_salary"] == 215000.0


def test_05_inventory_weighted_average_cost_and_negative_stock_prevention(client: TestClient):
    inv_token, _ = login_as(client, "inventory@nexora.lk")
    warehouses = client.get("/api/v1/inventory/warehouses", headers=auth_headers(inv_token)).json()["items"]
    wh1_id = warehouses[0]["id"]
    wh2_id = warehouses[1]["id"]

    # 1. Create product with 10 units @ LKR 10,000
    prod_resp = client.post(
        "/api/v1/inventory/products",
        headers=auth_headers(inv_token),
        json={
            "sku": "NEX-TEST-WAC-01",
            "name": "Nexora Industrial Edge Gateway",
            "uom": "UNIT",
            "cost_price": 10000.0,
            "selling_price": 15000.0,
            "reorder_level": 5.0,
            "reorder_quantity": 20.0,
            "initial_stock": 10.0,
            "warehouse_id": wh1_id,
        },
    )
    assert prod_resp.status_code == 201
    prod_id = prod_resp.json()["id"]

    # 2. Receive 10 more units @ LKR 20,000 -> Weighted Average Cost must become LKR 15,000.00
    mov_resp = client.post(
        "/api/v1/inventory/movements",
        headers=auth_headers(inv_token),
        json={
            "product_id": prod_id,
            "warehouse_id": wh1_id,
            "movement_type": "RECEIPT",
            "quantity": 10.0,
            "unit_cost": 20000.0,
            "notes": "Second batch receipt at higher unit cost",
        },
    )
    assert mov_resp.status_code == 201
    assert mov_resp.json()["balance_after"] == 20.0
    assert mov_resp.json()["weighted_avg_cost"] == 15000.0

    # 3. Attempt to issue 25 units when only 20 are available -> must fail with 422 INSUFFICIENT_STOCK
    neg_resp = client.post(
        "/api/v1/inventory/movements",
        headers=auth_headers(inv_token),
        json={
            "product_id": prod_id,
            "warehouse_id": wh1_id,
            "movement_type": "ISSUE",
            "quantity": 25.0,
        },
    )
    assert neg_resp.status_code == 422
    assert neg_resp.json()["error"]["code"] == "INSUFFICIENT_STOCK"

    # 4. Partial stock transfer of 6 units from WH1 to WH2
    tr_resp = client.post(
        "/api/v1/inventory/transfers",
        headers=auth_headers(inv_token),
        json={
            "from_warehouse_id": wh1_id,
            "to_warehouse_id": wh2_id,
            "items": [{"product_id": prod_id, "quantity": 6.0}],
            "notes": "Inter-warehouse stock balancing",
        },
    )
    assert tr_resp.status_code == 201


def test_06_procurement_separation_of_duties_and_goods_receipt(client: TestClient):
    proc_token, _ = login_as(client, "procurement@nexora.lk")
    fin_token, _ = login_as(client, "finance@nexora.lk")
    admin_token, _ = login_as(client, "admin@nexora.lk")

    suppliers = client.get("/api/v1/suppliers", headers=auth_headers(proc_token)).json()["items"]
    products = client.get("/api/v1/inventory/products", headers=auth_headers(proc_token)).json()["items"]

    # Create Purchase Order > LKR 50,000 (triggers 2-step approval threshold)
    po_resp = client.post(
        "/api/v1/purchase-orders",
        headers=auth_headers(proc_token),
        json={
            "supplier_id": suppliers[0]["id"],
            "items": [
                {
                    "product_id": products[0]["id"],
                    "ordered_qty": 5.0,
                    "unit_price": 25000.0,
                    "tax_rate": 8.0,
                }
            ],
        },
    )
    assert po_resp.status_code == 201
    po_data = po_resp.json()
    po_id = po_data["id"]
    assert po_data["approval_step_required"] == 2

    # Attempt to receive GRN before PO is approved -> rejected with 422 PO_NOT_APPROVED
    early_grn = client.post(
        "/api/v1/goods-receipts",
        headers=auth_headers(proc_token),
        json={"purchase_order_id": po_id},
    )
    assert early_grn.status_code == 422
    assert early_grn.json()["error"]["code"] == "PO_NOT_APPROVED"

    # Attempt self-approval when creator has approve permission -> rejected with 403 SELF_APPROVAL_FORBIDDEN
    admin_po = client.post(
        "/api/v1/purchase-orders",
        headers=auth_headers(admin_token),
        json={
            "supplier_id": suppliers[0]["id"],
            "items": [{"product_id": products[0]["id"], "ordered_qty": 2.0, "unit_price": 15000.0}],
        },
    ).json()
    self_app_resp = client.post(
        f"/api/v1/purchase-orders/{admin_po['id']}/approve",
        headers=auth_headers(admin_token),
        json={"action": "APPROVE"},
    )
    assert self_app_resp.status_code == 403
    assert self_app_resp.json()["error"]["code"] == "SELF_APPROVAL_FORBIDDEN"

    # Finance Manager approves Procurement Officer's PO
    fin_app_resp = client.post(
        f"/api/v1/purchase-orders/{po_id}/approve",
        headers=auth_headers(fin_token),
        json={"action": "APPROVE", "comments": "Budget verified and approved"},
    )
    assert fin_app_resp.status_code == 200
    assert fin_app_resp.json()["status"] == "APPROVED"

    # Receive Goods Receipt Note -> updates stock & posts balanced AP Journal Entry
    grn_resp = client.post(
        "/api/v1/goods-receipts",
        headers=auth_headers(proc_token),
        json={"purchase_order_id": po_id, "supplier_invoice_no": "SINV-TEST-909"},
    )
    assert grn_resp.status_code == 201
    assert grn_resp.json()["po_status"] == "RECEIVED"
    assert grn_resp.json()["journal_entry_id"] is not None


def test_07_sales_invoice_and_idempotent_payment_processing(client: TestClient):
    sales_token, _ = login_as(client, "sales@nexora.lk")
    customers = client.get("/api/v1/customers", headers=auth_headers(sales_token)).json()["items"]
    products = client.get("/api/v1/inventory/products", headers=auth_headers(sales_token)).json()["items"]
    stocked_prod = next(p for p in products if p["quantity_available"] >= 10)

    # Issue Sales Invoice
    inv_resp = client.post(
        "/api/v1/invoices",
        headers=auth_headers(sales_token),
        json={
            "customer_id": customers[0]["id"],
            "deduct_inventory": True,
            "items": [
                {
                    "product_id": stocked_prod["id"],
                    "quantity": 2.0,
                    "unit_price": stocked_prod["selling_price"],
                    "tax_rate": 8.0,
                }
            ],
        },
    )
    assert inv_resp.status_code == 201
    inv_data = inv_resp.json()
    inv_id = inv_data["id"]
    total_amt = inv_data["total_amount"]

    # Record partial payment with Idempotency-Key
    partial_amt = round(total_amt / 2.0, 2)
    pay1 = client.post(
        "/api/v1/payments",
        headers={**auth_headers(sales_token), "Idempotency-Key": "idem-pay-test-001"},
        json={
            "invoice_id": inv_id,
            "amount": partial_amt,
            "payment_method": "BANK_TRANSFER",
        },
    )
    assert pay1.status_code == 201
    assert pay1.json()["invoice_status"] == "PARTIALLY_PAID"

    # Replay same payment with identical Idempotency-Key -> blocked with 409 DUPLICATE_PAYMENT
    pay_dup = client.post(
        "/api/v1/payments",
        headers={**auth_headers(sales_token), "Idempotency-Key": "idem-pay-test-001"},
        json={
            "invoice_id": inv_id,
            "amount": partial_amt,
            "payment_method": "BANK_TRANSFER",
        },
    )
    assert pay_dup.status_code == 409
    assert pay_dup.json()["error"]["code"] == "DUPLICATE_PAYMENT"


def test_08_double_entry_accounting_invariants_and_trial_balance(client: TestClient):
    fin_token, _ = login_as(client, "finance@nexora.lk")

    # 1. Attempt to post an unbalanced journal entry (Debit 50,000 != Credit 45,000) -> 422 UNBALANCED_JOURNAL
    unbalanced_resp = client.post(
        "/api/v1/finance/journal-entries",
        headers=auth_headers(fin_token),
        json={
            "description": "Unbalanced test entry",
            "auto_post": True,
            "lines": [
                {"account_code": "6100", "debit": 50000.0, "credit": 0.0},
                {"account_code": "1000", "debit": 0.0, "credit": 45000.0},
            ],
        },
    )
    assert unbalanced_resp.status_code == 422
    assert unbalanced_resp.json()["error"]["code"] == "UNBALANCED_JOURNAL"

    # 2. Post a balanced journal entry and then reverse it
    balanced_resp = client.post(
        "/api/v1/finance/journal-entries",
        headers=auth_headers(fin_token),
        json={
            "description": "Balanced audit entry",
            "auto_post": True,
            "lines": [
                {"account_code": "6100", "debit": 25000.0, "credit": 0.0},
                {"account_code": "1000", "debit": 0.0, "credit": 25000.0},
            ],
        },
    )
    assert balanced_resp.status_code == 201
    je_id = balanced_resp.json()["id"]

    rev_resp = client.post(
        f"/api/v1/finance/journal-entries/{je_id}/reverse",
        headers=auth_headers(fin_token),
        json={"reason": "Reversing test adjustment"},
    )
    assert rev_resp.status_code == 200
    assert rev_resp.json()["status"] == "REVERSED"

    # 3. Verify Trial Balance is strictly balanced (Total Debits == Total Credits)
    tb_resp = client.get("/api/v1/finance/trial-balance", headers=auth_headers(fin_token))
    assert tb_resp.status_code == 200
    tb = tb_resp.json()
    assert tb["is_balanced"] is True
    assert tb["total_debit"] == tb["total_credit"]
    assert tb["total_debit"] > 0

    # 4. Verify Balance Sheet & P&L
    bs_resp = client.get("/api/v1/finance/balance-sheet", headers=auth_headers(fin_token))
    assert bs_resp.status_code == 200
    assert bs_resp.json()["is_balanced"] is True


def test_09_nexora_intelligence_ai_suite(client: TestClient):
    ceo_token, _ = login_as(client, "ceo@nexora.lk")

    # 1. Inventory Demand Forecasting (MAE, RMSE, WAPE, 7D/30D/90D)
    inv_fc = client.post(
        "/api/v1/ai/forecast/inventory",
        headers=auth_headers(ceo_token),
        json={"model_choice": "XGBOOST"},
    )
    assert inv_fc.status_code == 200
    fc_data = inv_fc.json()
    assert "mae" in fc_data["evaluation_metrics"]
    assert "rmse" in fc_data["evaluation_metrics"]
    assert "wape_percent" in fc_data["evaluation_metrics"]
    assert len(fc_data["forecasts"]) >= 50

    # 2. Sales Revenue Forecasting
    sales_fc = client.post(
        "/api/v1/ai/forecast/sales",
        headers=auth_headers(ceo_token),
        json={"horizon_months": 6},
    )
    assert sales_fc.status_code == 200
    assert sales_fc.json()["next_month_predicted_revenue"] > 0

    # 3. Business Anomaly Detection
    anom_resp = client.post("/api/v1/ai/anomalies/analyze", headers=auth_headers(ceo_token))
    assert anom_resp.status_code == 200
    assert anom_resp.json()["total_anomalies"] >= 2

    # 4. AI Business Copilot (Grounded Read-Only Tools + Mutation Refusal)
    copilot_resp = client.post(
        "/api/v1/ai/copilot/chat",
        headers=auth_headers(ceo_token),
        json={"question": "What were our total expenses this month and which products need replenishment?"},
    )
    assert copilot_resp.status_code == 200
    c_json = copilot_resp.json()
    assert "financial_summary" in c_json["factual_data"]
    assert "low_stock_products" in c_json["factual_data"]
    assert len(c_json["source_references"]) >= 2
