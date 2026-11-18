# NEXORA ERP — AI-Powered Enterprise Resource Planning Platform

> *"One intelligent platform. Every business operation. Better decisions."*

**NEXORA ERP** is a production-minded, multi-tenant Enterprise Resource Planning (ERP) platform engineered with a **FastAPI + SQLAlchemy 2.x** modular monolith backend, a **PostgreSQL** normalized relational database, a **Double-Entry General Ledger**, a **Weighted-Average-Cost Multi-Warehouse Inventory Engine**, a **Reusable Multi-Tier Workflow & Approval Engine**, an **AI & Machine Learning Intelligence Suite**, and a **React + TypeScript + Tailwind CSS Glassmorphism Interface**.

---

## 1. Core Enterprise Capabilities

| Module | Key Capabilities |
| :--- | :--- |
| **Multi-Tenant Organization & RBAC** | Multi-organization isolation (`organization_id` + PostgreSQL RLS support), Branches, Departments, 12 Enterprise Roles, 40+ Granular Permissions, Argon2id password hashing, JWT + HttpOnly Refresh Token rotation, TOTP MFA (`RFC 6238`), and account lockout protection. |
| **Executive Command Dashboard** | 10 real-time database-derived KPIs (Total Revenue, Expenses, Net Profit, Receivables, Payables, Inventory Valuation, Low-Stock Count, Pending Approvals, Workforce, Active Projects), 6-month Revenue vs. Expenses & Cash Flow analytics, and CSV export. |
| **Human Resource Management (HR)** | Employee directory (with RBAC confidential salary masking), Designations, Attendance tracking, Leave Balances, Leave Requests with Separation-of-Duties approval, and KPI/Competency Performance Reviews. |
| **Inventory & Warehouses** | Multi-warehouse stock ledger, SKU/Barcode/QR generation, **Weighted Average Cost (WAC)** automatic recalculation on receipt, **Negative Stock Prevention**, partial/full inter-warehouse Stock Transfers, and Low-Stock Alert notifications. |
| **Procurement & Suppliers** | Supplier directory & ratings, Purchase Requests, Supplier RFQ Quotation comparisons, Purchase Orders with **LKR 50,000 multi-level approval thresholds**, and Goods Receipt Notes (GRNs) that atomically update stock and post Accounts Payable journals. |
| **Sales & Customer Billing** | Customer credit limits & receivables aging, Sales Quotations, Sales Orders, Tax Invoices (auto-deducting inventory and posting Revenue/COGS/AR journals), and **Idempotent Payment Recording**. |
| **Finance & Double-Entry Accounting** | Hierarchical Chart of Accounts, General Ledger, Journal Entries enforcing $\sum \text{Debits} = \sum \text{Credits}$, immutable posted journals with **Reversal Entry** support, Expense management, live **Trial Balance**, **Income Statement (P&L)**, **Balance Sheet**, and **Cash Flow Statement**. |
| **Projects, Kanban & Workflow Engine** | Project budget & milestone tracking, interactive 5-stage **Kanban Board**, and a centralized **Approval Center** enforcing Separation of Duties (`requester != approver`). |
| **Nexora Intelligence (AI & ML)** | **1. Inventory Demand Forecasting** (7D/30D/90D predictions using XGBoost / Gradient Boosting, Seasonal Naive & Moving Average with backtested `MAE`, `RMSE`, `WAPE`, 90% prediction intervals, stockout risk & reorder quantities).<br>**2. Sales Revenue Forecasting** (6-month revenue trajectory with confidence bands).<br>**3. Business Anomaly Detection** (Isolation Forest + Z-Score + Rule Engine across expenses, stock adjustments & PO price variances).<br>**4. Nexora AI Business Copilot** (permission-aware, read-only conversational assistant with factual tables & source citations). |

---

## 2. Architecture & Documentation Index

- [System Architecture & Diagrams](file:///c:/Users/abdur/OneDrive/Desktop/NEXORA-AI/docs/ARCHITECTURE.md)
- [Normalized Relational Database Schema (56 Tables & ER Diagram)](file:///c:/Users/abdur/OneDrive/Desktop/NEXORA-AI/docs/DATABASE_SCHEMA.md)
- [REST API v1 Contracts & Endpoint Catalogue](file:///c:/Users/abdur/OneDrive/Desktop/NEXORA-AI/docs/API_CONTRACTS.md)
- [Glassmorphism Design System & Theme Tokens](file:///c:/Users/abdur/OneDrive/Desktop/NEXORA-AI/docs/DESIGN_SYSTEM.md)
- [12-Role RBAC Permission Matrix & Separation of Duties](file:///c:/Users/abdur/OneDrive/Desktop/NEXORA-AI/docs/PERMISSION_MATRIX.md)
- [Nexora Intelligence AI & ML Documentation](file:///c:/Users/abdur/OneDrive/Desktop/NEXORA-AI/docs/AI_MODELS.md)
- [Security Architecture & Backup/Recovery Guide](file:///c:/Users/abdur/OneDrive/Desktop/NEXORA-AI/docs/SECURITY.md)
- [ADR-001: Modular Monolith & Multi-Tenancy](file:///c:/Users/abdur/OneDrive/Desktop/NEXORA-AI/docs/ADR/001-modular-monolith-and-multi-tenancy.md)
- [Development Progress Log](file:///c:/Users/abdur/OneDrive/Desktop/NEXORA-AI/DEVELOPMENT_PROGRESS.md)

---

## 3. Demo Organization & Role Credentials (`Nexora Demo Holdings`)

On startup, NEXORA ERP idempotently seeds **Nexora Demo Holdings** (`Currency: LKR`, `Timezone: Asia/Colombo`, `Date Format: DD MMM YYYY`) with 4 branches, 8 departments, 35 employees, 8 suppliers, 20 corporate/retail customers, 50 products across 3 warehouses, 6 months of historical sales invoices, payments, purchase orders, GRNs, balanced GL journals, projects, and AI forecasts.

All demo accounts use the password: **`Nexora#2026`**

| Role | Demo Email | Key Scope |
| :--- | :--- | :--- |
| **Super Admin** | `admin@nexora.lk` | Full multi-tenant & system access |
| **Organization Admin** | `orgadmin@nexora.lk` | Full administration within Nexora Demo Holdings |
| **CEO / Director** | `ceo@nexora.lk` | Executive KPIs, Financial Reports, High-Value Approvals, AI Suite |
| **Finance Manager** | `finance@nexora.lk` | General Ledger, Journals, Trial Balance, P&L, Balance Sheet, PO Step-2 Approvals |
| **HR Manager** | `hr@nexora.lk` | Employees (including confidential salary), Attendance, Leave Approvals |
| **Inventory Manager** | `inventory@nexora.lk` | Products, Warehouses, Stock Movements, Transfers, Demand Forecasting |
| **Procurement Officer** | `procurement@nexora.lk` | Suppliers, PRs, RFQs, Purchase Orders, Goods Receipt Notes |
| **Sales Manager** | `sales@nexora.lk` | Customers, Quotations, Sales Orders, Invoices, Receipts |
| **Project Manager** | `projects@nexora.lk` | Projects, Milestones, Kanban Tasks |
| **Department Manager** | `deptmanager@nexora.lk` | Departmental Leave & Step-1 Purchase Approvals |
| **Employee** | `employee@nexora.lk` | Self-service employee directory (salary redacted), Leave submission |
| **Auditor** | `auditor@nexora.lk` | Read-only General Ledger, Anomaly Detection & Immutable Audit Logs |
| **Secondary Tenant Admin** | `admin@ceylonhorizon.lk` | Isolated tenant (`Ceylon Horizon Logistics Ltd`) for tenant-isolation verification |

---

## 4. Quick Start & Deployment Instructions

### Option A: Full Docker Compose Stack (PostgreSQL 16 + Redis 7 + FastAPI + Celery + React/Nginx)

1. **Copy Environment Variables**:
   ```bash
   cp .env.example .env
   ```
2. **Start All Services**:
   ```bash
   docker compose up --build -d
   ```
3. **Run Alembic Migrations (if running manually)**:
   ```bash
   docker compose exec backend alembic upgrade head
   ```
4. **Access the Platform**:
   - **Frontend Web App**: `http://localhost:5173`
   - **Backend REST API & Integrated Portal**: `http://localhost:8000`
   - **Interactive OpenAPI / Swagger Docs**: `http://localhost:8000/docs`

### Option B: Local Host Development (Without Docker Daemon)

1. **Start the Backend (FastAPI + SQLAlchemy)**:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. **Start the Frontend (React + TypeScript + Vite)**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## 5. Running the Automated Test Suite

```bash
cd backend
pytest tests/test_nexora_erp.py -v
```

### Verified Critical Scenarios:
- `test_01_health_and_demo_seed`: Verifies health check and `Nexora Demo Holdings` seeding (`LKR`, `Asia/Colombo`).
- `test_02_authentication_refresh_and_mfa`: Verifies Argon2id login, credential rejection, and `HttpOnly` refresh token rotation.
- `test_03_multi_tenant_isolation_enforced`: Verifies cross-organization requests are blocked with `403 TENANT_ISOLATION_VIOLATION`.
- `test_04_rbac_and_confidential_hr_masking`: Verifies salary masking for non-HR roles and permission enforcement.
- `test_05_inventory_weighted_average_cost_and_negative_stock_prevention`: Verifies Weighted Average Cost recalculation, negative stock prevention (`422 INSUFFICIENT_STOCK`), and stock transfers.
- `test_06_procurement_separation_of_duties_and_goods_receipt`: Verifies LKR 50,000 2-step approval threshold, self-approval block (`403 SELF_APPROVAL_FORBIDDEN`), and GRN inventory/GL synchronization.
- `test_07_sales_invoice_and_idempotent_payment_processing`: Verifies sales invoice stock deduction, GL posting, and duplicate payment prevention (`409 DUPLICATE_PAYMENT`).
- `test_08_double_entry_accounting_invariants_and_trial_balance`: Verifies unbalanced journal rejection (`422 UNBALANCED_JOURNAL`), journal reversal, and balanced Trial Balance & Balance Sheet.
- `test_09_nexora_intelligence_ai_suite`: Verifies Demand Forecasting (`MAE`, `RMSE`, `WAPE`), Sales Forecasting, Anomaly Detection, and AI Copilot grounding.

---

## 6. Known Limitations & Roadmap

- **Statutory Tax Localization**: The platform supports configurable VAT/tax percentages on purchase orders and invoices, but does not claim certified statutory e-filing compliance for specific tax jurisdictions without jurisdiction-specific legal plugins.
- **Future Roadmap**:
  - Multi-currency real-time FX revaluation journals.
  - Barcode/RFID hardware scanner WebHID integration.
  - `pgvector` semantic contract & supplier document RAG search.
