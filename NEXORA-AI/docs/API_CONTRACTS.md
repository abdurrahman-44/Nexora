# NEXORA ERP — REST API v1 Contracts & Specification

## 1. API Design Standards

- **Base URL**: `/api/v1`
- **OpenAPI Spec**: Automatically generated at `/api/v1/openapi.json` and `/docs`
- **Authentication**:
  - `Authorization: Bearer <access_token>` (short-lived JWT containing `sub`, `org_id`, `roles`, `permissions`).
  - `HttpOnly; SameSite=Lax; Secure` cookie `nexora_refresh_token` for refresh token rotation.
- **Multi-Tenant Scoping**:
  - Active tenant resolved from `X-Organization-ID` header (validated against user's permitted organizations) or user's primary `organization_id`.
  - Optional branch scoping via `X-Branch-ID` header or `?branch_id=<uuid>`.
- **Request Correlation & Auditing**:
  - Every request receives or propagates `X-Correlation-ID` in response headers.
  - Sensitive mutations accept `Idempotency-Key` header to prevent duplicate financial/stock postings.
- **Standardized Pagination Envelope**:
  ```json
  {
    "items": [],
    "total": 120,
    "page": 1,
    "page_size": 25,
    "total_pages": 5
  }
  ```
- **Standardized Error Envelope**:
  ```json
  {
    "error": {
      "code": "INSUFFICIENT_STOCK",
      "message": "Cannot issue 50 units of SKU NEX-LAP-001; only 18 available in Colombo Central Warehouse.",
      "correlation_id": "req-91a8b2c4",
      "details": null
    }
  }
  ```

---

## 2. Domain Endpoint Catalogue

### Authentication (`/api/v1/auth`)
| Method | Endpoint | Permission | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/login` | Public | Authenticate with email/password (+ optional TOTP code); returns access token, user profile, roles, permissions, and sets HttpOnly refresh cookie. |
| `POST` | `/auth/refresh` | Cookie / Token | Rotate refresh token and issue a fresh access token. |
| `POST` | `/auth/logout` | Authenticated | Revoke current refresh token family and clear cookie. |
| `POST` | `/auth/forgot-password` | Public | Issue time-bound password reset token and log notification. |
| `POST` | `/auth/reset-password` | Public | Verify reset token and update password with Argon2id hash. |
| `POST` | `/auth/mfa/setup` | Authenticated | Generate TOTP secret & provisioning URI. |
| `POST` | `/auth/mfa/verify` | Authenticated | Verify 6-digit TOTP code and enable MFA. |
| `GET` | `/auth/me` | Authenticated | Return current user, active organization, branches, roles, and permissions. |

### Organization & Multi-Tenancy (`/api/v1/organizations`)
| Method | Endpoint | Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/organizations` | Authenticated | List organizations accessible to current user. |
| `POST` | `/organizations` | `organizations.manage` | Create a new tenant organization with default Chart of Accounts & workflows. |
| `GET` | `/organizations/{id}` | `organizations.view` | Get organization profile, fiscal config, branches, and departments. |
| `PUT` | `/organizations/{id}` | `organizations.manage` | Update organization profile, currency, timezone, fiscal year. |
| `GET` | `/organizations/{id}/branches` | `organizations.view` | List organization branches. |
| `POST` | `/organizations/{id}/branches` | `organizations.manage` | Create branch. |
| `GET` | `/organizations/{id}/departments` | `organizations.view` | List organization departments. |
| `POST` | `/organizations/{id}/departments` | `organizations.manage` | Create department. |

### Users, Roles & Permissions (`/api/v1/users`, `/api/v1/roles`, `/api/v1/permissions`)
| Method | Endpoint | Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/users` | `users.view` | List tenant users with roles and status. |
| `POST` | `/users` | `users.manage` | Create user and assign roles. |
| `PUT` | `/users/{id}` | `users.manage` | Update user status, branch, department, or roles. |
| `GET` | `/roles` | `users.view` | List all roles and their mapped permissions. |
| `POST` | `/roles` | `users.manage` | Create custom role with selected permissions. |
| `PUT` | `/roles/{id}` | `users.manage` | Update role permissions. |
| `GET` | `/permissions` | `users.view` | List all granular permissions grouped by domain. |

### Human Resources (`/api/v1/employees`, `/api/v1/leave-requests`, `/api/v1/hr`)
| Method | Endpoint | Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/employees` | `employees.view` | Paginated employee directory with department/branch/status filters (salary masked unless `hr.confidential.view` or HR/Admin). |
| `POST` | `/employees` | `employees.create` | Register new employee and initialize leave balances. |
| `GET` | `/employees/{id}` | `employees.view` | Full employee profile, attendance summary, leave balances, performance history. |
| `PUT` | `/employees/{id}` | `employees.update` | Update employee details, designation, or status. |
| `GET` | `/hr/attendance` | `employees.view` | List attendance logs with date & department filters. |
| `POST` | `/hr/attendance` | `employees.update` | Record check-in / check-out attendance entry. |
| `GET` | `/leave-requests` | `leave.view` | List leave requests and balances. |
| `POST` | `/leave-requests` | `leave.create` | Submit leave request and trigger approval workflow. |
| `POST` | `/leave-requests/{id}/approve` | `leave.approve` | Approve or reject leave request (enforces self-approval block & deducts balance). |
| `GET` | `/hr/performance` | `employees.view` | List performance reviews. |
| `POST` | `/hr/performance` | `employees.update` | Create employee performance evaluation. |

### Inventory & Warehouses (`/api/v1/inventory`)
| Method | Endpoint | Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/inventory/products` | `inventory.view` | List products with category, stock level, weighted avg cost, and low-stock flags. |
| `POST` | `/inventory/products` | `inventory.manage` | Create product with SKU, barcode, QR code, and reorder thresholds. |
| `PUT` | `/inventory/products/{id}` | `inventory.manage` | Update product attributes and pricing. |
| `GET` | `/inventory/warehouses` | `inventory.view` | List warehouses with utilization and valuation metrics. |
| `POST` | `/inventory/warehouses` | `inventory.manage` | Create warehouse and bin locations. |
| `GET` | `/inventory/movements` | `inventory.view` | Immutable stock movement ledger with filters. |
| `POST` | `/inventory/movements` | `inventory.adjust` | Post stock adjustment/receipt/issue (ACID, prevents negative stock, updates weighted average cost, posts GL journal when applicable). |
| `POST` | `/inventory/transfers` | `inventory.transfer` | Execute full or partial inter-warehouse stock transfer. |
| `GET` | `/inventory/stock-summary` | `inventory.view` | Valuation summary, warehouse distribution, low-stock & out-of-stock alerts. |

### Procurement & Suppliers (`/api/v1/suppliers`, `/api/v1/purchase-requests`, `/api/v1/purchase-orders`, `/api/v1/goods-receipts`)
| Method | Endpoint | Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/suppliers` | `procurement.view` | List suppliers with rating and delivery performance. |
| `POST` | `/suppliers` | `procurement.manage` | Register supplier. |
| `GET` | `/purchase-requests` | `procurement.view` | List purchase requests and quotation comparisons. |
| `POST` | `/purchase-requests` | `purchase_requests.create` | Create PR and route through threshold-based workflow engine. |
| `POST` | `/purchase-requests/{id}/quotations` | `procurement.manage` | Record supplier quotation for comparison. |
| `GET` | `/purchase-orders` | `procurement.view` | List purchase orders with status and receipt progress. |
| `POST` | `/purchase-orders` | `purchase_orders.create` | Create purchase order from PR or directly. |
| `POST` | `/purchase-orders/{id}/approve` | `purchase_orders.approve` | Approve or reject PO (enforces separation of duties: creator != approver, checks LKR 50,000 multi-level threshold). |
| `GET` | `/goods-receipts` | `procurement.view` | List goods receipt notes (GRNs). |
| `POST` | `/goods-receipts` | `goods_receipts.create` | Receive full or partial PO delivery -> updates inventory weighted avg cost -> generates Supplier Bill & AP Journal Entry (`Debit Inventory, Credit Accounts Payable`). |

### Sales, Customers, Invoices & Payments (`/api/v1/customers`, `/api/v1/sales`, `/api/v1/invoices`, `/api/v1/payments`)
| Method | Endpoint | Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/customers` | `sales.view` | List customers with credit limit, outstanding receivables, and aging summary. |
| `POST` | `/customers` | `sales.manage` | Register customer. |
| `GET` | `/sales/quotations` | `sales.view` | List sales quotations. |
| `POST` | `/sales/quotations` | `sales.manage` | Create sales quotation. |
| `GET` | `/sales/orders` | `sales.view` | List sales orders. |
| `POST` | `/sales/orders` | `sales.manage` | Create sales order and allocate stock. |
| `GET` | `/invoices` | `invoices.view` | List customer invoices and supplier bills with aging status. |
| `POST` | `/invoices` | `invoices.create` | Issue sales invoice -> deducts stock -> posts balanced GL Journal Entry (`Debit AR, Credit Sales Revenue` + `Debit COGS, Credit Inventory`). |
| `GET` | `/payments` | `payments.view` | List recorded payments and receipts. |
| `POST` | `/payments` | `payments.create` | Record full or partial payment (idempotent) -> updates invoice balance -> posts balanced GL Journal Entry (`Debit Cash/Bank, Credit AR` or `Debit AP, Credit Cash/Bank`). |

### Finance & Double-Entry Accounting (`/api/v1/finance`)
| Method | Endpoint | Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/finance/accounts` | `finance.view` | Hierarchical Chart of Accounts with live ledger balances. |
| `POST` | `/finance/accounts` | `finance.manage` | Create GL account. |
| `GET` | `/finance/journal-entries` | `finance.view` | List journal entries (`DRAFT`, `POSTED`, `REVERSED`) with lines. |
| `POST` | `/finance/journal-entries` | `finance.manage` | Create draft or posted journal entry (validates `sum(debit) == sum(credit)`). |
| `POST` | `/finance/journal-entries/{id}/post` | `finance.post` | Post a draft journal entry (enforces balance & immutability). |
| `POST` | `/finance/journal-entries/{id}/reverse` | `finance.post` | Generate an inverting reversal journal entry for an existing posted entry. |
| `GET` | `/finance/expenses` | `finance.view` | List organizational expenses. |
| `POST` | `/finance/expenses` | `expenses.create` | Submit expense and post to GL upon approval. |
| `GET` | `/finance/trial-balance` | `finance.reports.view` | Real-time Trial Balance verifying Total Debits = Total Credits. |
| `GET` | `/finance/profit-loss` | `finance.reports.view` | Income Statement (Revenue, COGS, Gross Profit, Operating Expenses, Net Profit). |
| `GET` | `/finance/balance-sheet` | `finance.reports.view` | Balance Sheet (Assets = Liabilities + Equity). |
| `GET` | `/finance/cash-flow` | `finance.reports.view` | Cash Flow Statement (Operating, Investing, Financing cash movements). |

### Projects, Workflows, Analytics & AI (`/api/v1/projects`, `/api/v1/workflows`, `/api/v1/analytics`, `/api/v1/ai`)
| Method | Endpoint | Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/projects` | `projects.view` | List projects with budget utilization, milestones, and progress. |
| `POST` | `/projects` | `projects.manage` | Create project. |
| `GET` | `/tasks` | `projects.view` | List tasks across Kanban statuses (`BACKLOG`, `TODO`, `IN_PROGRESS`, `REVIEW`, `DONE`). |
| `POST` | `/tasks` | `projects.manage` | Create or update project task. |
| `PATCH` | `/tasks/{id}/status` | `projects.view` | Move task card across Kanban columns. |
| `GET` | `/workflows/approvals` | `approvals.view` | Unified Approval Center listing pending/completed approvals across all modules. |
| `POST` | `/workflows/approvals/{id}/act` | `approvals.act` | Approve, reject, or escalate a workflow step (enforces Separation of Duties). |
| `GET` | `/analytics/dashboard` | `dashboard.view` | Executive Dashboard KPIs, revenue vs. expenses, cash flow, department metrics. |
| `GET` | `/analytics/reports/{report_type}` | `reports.view` | Generate tabular BI report with CSV/JSON export. |
| `POST` | `/ai/forecast/inventory` | `ai.forecast.view` | Run/retrieve 7D, 30D, 90D product demand forecast (MA, Seasonal Naive, XGBoost) with MAE, RMSE, WAPE, prediction intervals, and reorder recommendations. |
| `POST` | `/ai/forecast/sales` | `ai.forecast.view` | Run/retrieve monthly revenue & sales forecast with confidence bands and model metrics. |
| `POST` | `/ai/anomalies/analyze` | `ai.anomalies.view` | Run Isolation Forest + Z-Score + Rule Engine across inventory, expenses, POs, and invoices; returns explainable anomaly events for human review. |
| `POST` | `/ai/copilot/chat` | `ai.copilot.use` | Permission-aware conversational AI Copilot grounded in read-only tenant tools with source references. |
