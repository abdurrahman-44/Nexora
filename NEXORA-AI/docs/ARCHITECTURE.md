# NEXORA ERP — System Architecture & Engineering Blueprint

## 1. Architectural Overview

**NEXORA ERP** is built as a **production-grade modular monolith** with a decoupled single-page frontend, a domain-driven FastAPI backend, an asynchronous Celery/Redis task pipeline, an embedded Machine Learning & AI Copilot engine, and a multi-tenant PostgreSQL relational database.

### High-Level System Architecture

```mermaid
flowchart TB
    subgraph Client["Client Layer (React + TypeScript + Vite)"]
        UI["Glassmorphism UI Shell (Tailwind + shadcn/ui)"]
        State["TanStack Query + Zustand Session Store"]
        WSClient["WebSocket Real-Time Client"]
    end

    subgraph Edge["API Gateway / Reverse Proxy"]
        Nginx["Nginx / CORS & Rate Limiter"]
    end

    subgraph Backend["NEXORA Core Backend (FastAPI / Python)"]
        Middleware["Auth Middleware + Tenant Context + Correlation ID + Audit"]
        RBAC["Granular RBAC & Separation-of-Duties Engine"]
        
        subgraph Domains["Domain Service Layer"]
            OrgSvc["Organization & Tenant Service"]
            HRSvc["HR, Attendance & Leave Service"]
            InvSvc["Inventory & Weighted-Avg Costing Service"]
            ProcSvc["Procurement & Supplier Service"]
            SalesSvc["Sales, Invoicing & AR Service"]
            FinSvc["Double-Entry Accounting & GL Engine"]
            ProjSvc["Project & Task Service"]
            WfSvc["Reusable Approval Workflow Engine"]
            RepSvc["BI & Financial Reporting Engine"]
            NotifSvc["Notification & WebSocket Hub"]
        end

        subgraph AIEngine["Nexora Intelligence Engine"]
            DemandML["Inventory Demand Forecaster (XGBoost / Seasonal / MA)"]
            SalesML["Sales & Revenue Forecaster"]
            AnomalyML["Anomaly Detection (Isolation Forest + Z-Score + Rules)"]
            Copilot["Nexora AI Copilot (Permission-Scoped Tool Calling)"]
        end
    end

    subgraph DataLayer["Persistence & Messaging Layer"]
        PG[("PostgreSQL 16\n(UUID PKs, ACID, Tenant RLS)")]
        Redis[("Redis 7\n(Cache, Rate Limit, Broker)")]
        Celery["Celery Worker & Beat\n(Forecasts, Exports, Alerts)"]
    end

    UI --> State
    State -->|REST /api/v1| Nginx
    WSClient -->|WSS /api/v1/ws| Nginx
    Nginx --> Middleware
    Middleware --> RBAC
    RBAC --> Domains
    RBAC --> AIEngine
    Domains --> PG
    AIEngine --> PG
    Domains --> Redis
    Celery --> Redis
    Celery --> PG
```

---

## 2. Multi-Tenant Data Isolation Architecture

Every business record in NEXORA ERP belongs to a specific `organization_id` (and optionally a `branch_id` and `department_id`).

1. **Tenant Context Injection**:
   - Authenticated requests validate the user's JWT access token and active `X-Organization-ID` header (or default organization from user membership).
   - The backend verifies that the user is an active member of that `organization_id`.
2. **Application-Level & Database-Level Isolation**:
   - Every repository/service query explicitly filters by `organization_id == current_tenant.id`.
   - PostgreSQL session variables (`SET LOCAL app.current_organization_id = '<uuid>'`) support Row-Level Security (RLS) policies on tenant-owned tables.
   - Cross-tenant references (e.g., linking an invoice from Organization A to a customer in Organization B) are rejected at both service validation and composite foreign-key validation layers.

---

## 3. Double-Entry Accounting & Operational Integration Flow

All financial KPIs on the Executive Dashboard and Financial Reports derive directly from balanced `journal_entries` and `journal_lines`.

```mermaid
sequenceDiagram
    participant User as Sales / Procurement User
    participant OrderSvc as Sales / Procurement Service
    participant InvSvc as Inventory Service
    participant WfSvc as Workflow Approval Engine
    participant FinSvc as Accounting Service (GL)
    participant DB as PostgreSQL (ACID Transaction)

    User->>OrderSvc: Submit Purchase Order / Sales Invoice
    OrderSvc->>WfSvc: Check Approval Rules (e.g. > LKR 50,000)
    WfSvc-->>OrderSvc: Approved (Creator != Approver enforced)
    OrderSvc->>DB: Begin Transaction
    OrderSvc->>InvSvc: Record Stock Movement & Update Weighted Avg Cost
    InvSvc->>DB: Insert stock_movements & Update stock_balances
    OrderSvc->>FinSvc: Auto-Generate Balanced Journal Entry
    FinSvc->>FinSvc: Verify sum(debit) == sum(credit) > 0
    FinSvc->>DB: Insert journal_entries (POSTED) & journal_lines
    OrderSvc->>DB: Commit Transaction
```

---

## 4. Reusable Workflow & Approval Engine

Instead of hardcoding approval statuses in individual modules, NEXORA ERP routes all gated documents (`purchase_request`, `purchase_order`, `leave_request`, `expense`, `stock_adjustment`) through the central **Workflow Engine**:

- **`approval_workflows`**: Defines rules per organization and document type (e.g., `purchase_order`).
- **`approval_steps`**: Defines step sequence, threshold condition (`min_amount`, `max_amount`), required `role_code` or `permission_code`, and approval mode (`SEQUENTIAL` or `PARALLEL`).
- **`approval_requests`**: Tracks the active state of a document's approval lifecycle.
- **`approval_actions`**: Immutable audit record of each step approval, rejection (with mandatory reason), or escalation.
- **Separation of Duties Rule**: `requester_user_id != approver_user_id` is strictly enforced for restricted financial and procurement approvals.

---

## 5. Repository Folder Structure

```text
NEXORA-AI/
├── backend/
│   ├── alembic/                    # Database migrations
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py             # Auth, RBAC, Tenant & DB dependencies
│   │   │   └── v1/                 # Versioned domain routers
│   │   │       ├── auth.py
│   │   │       ├── organizations.py
│   │   │       ├── users.py
│   │   │       ├── hr.py
│   │   │       ├── inventory.py
│   │   │       ├── procurement.py
│   │   │       ├── sales.py
│   │   │       ├── finance.py
│   │   │       ├── projects.py
│   │   │       ├── workflows.py
│   │   │       ├── analytics.py
│   │   │       ├── ai.py
│   │   │       └── notifications.py
│   │   ├── core/
│   │   │   ├── config.py           # Environment settings
│   │   │   ├── database.py         # SQLAlchemy 2.x engine & session
│   │   │   ├── security.py         # Argon2id, JWT, TOTP MFA, CSRF
│   │   │   ├── exceptions.py       # Standardized error handlers
│   │   │   └── logging.py          # Correlation IDs & structured logs
│   │   ├── models/                 # Normalized SQLAlchemy 2.x ORM models
│   │   ├── schemas/                # Pydantic v2 request/response schemas
│   │   ├── services/               # Business logic & accounting/AI engines
│   │   │   ├── accounting_service.py
│   │   │   ├── inventory_service.py
│   │   │   ├── workflow_service.py
│   │   │   ├── ai_forecasting.py
│   │   │   ├── ai_anomaly.py
│   │   │   ├── ai_copilot.py
│   │   │   └── seed_service.py     # "Nexora Demo Holdings" generator
│   │   ├── worker/                 # Celery background tasks
│   │   └── main.py                 # FastAPI entrypoint
│   ├── tests/                      # Pytest unit, integration & security tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/                    # Axios/Fetch client + TanStack Query hooks
│   │   ├── components/
│   │   │   ├── layout/             # GlassSidebar, TopNavbar, CommandPalette
│   │   │   ├── ui/                 # Reusable Glass cards, DataTables, Modals
│   │   │   └── charts/             # Recharts glass-styled financial charts
│   │   ├── context/                # AuthContext, ThemeContext, TenantContext
│   │   ├── pages/                  # All 12 domain module views
│   │   ├── types/                  # TypeScript interfaces matching API
│   │   ├── utils/                  # LKR currency, DD MMM YYYY date formatters
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.ts
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATABASE_SCHEMA.md
│   ├── API_CONTRACTS.md
│   ├── DESIGN_SYSTEM.md
│   ├── PERMISSION_MATRIX.md
│   ├── AI_MODELS.md
│   ├── SECURITY.md
│   └── ADR/
├── .github/workflows/ci.yml
├── docker-compose.yml
├── .env.example
├── DEVELOPMENT_PROGRESS.md
└── README.md
```
