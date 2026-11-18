# NEXORA ERP — Role-Based Access Control (RBAC) & Permission Matrix

## 1. The 12 Enterprise Roles

1. **Super Admin (`SUPER_ADMIN`)**: Full platform & multi-tenant administration.
2. **Organization Admin (`ORG_ADMIN`)**: Full administrative control within their assigned organization.
3. **CEO / Director (`CEO_DIRECTOR`)**: Executive visibility across all modules, high-value approvals, financial & AI intelligence.
4. **Finance Manager (`FINANCE_MANAGER`)**: Full control of Chart of Accounts, Journal Entries, AP/AR, Expenses, Financial Reports, and high-value PO approvals (`> LKR 50,000`).
5. **HR Manager (`HR_MANAGER`)**: Full control of Employee records (including confidential salary data), Attendance, Leave approvals, and Performance Reviews.
6. **Inventory Manager (`INVENTORY_MANAGER`)**: Full control of Products, Warehouses, Stock Movements, Adjustments, and Transfers.
7. **Procurement Officer (`PROCUREMENT_OFFICER`)**: Manages Suppliers, Purchase Requests, RFQs/Quotations, Purchase Orders, and Goods Receipt Notes.
8. **Sales Manager (`SALES_MANAGER`)**: Manages Customers, Quotations, Sales Orders, Invoices, and Customer Receipts.
9. **Project Manager (`PROJECT_MANAGER`)**: Manages Projects, Budgets, Milestones, Tasks, and Kanban workflows.
10. **Department Manager (`DEPARTMENT_MANAGER`)**: Approves departmental Leave Requests, Expenses, and Purchase Requests (`<= LKR 50,000`).
11. **Employee (`EMPLOYEE`)**: Self-service access to own profile, attendance, leave submission, assigned project tasks, and basic directory.
12. **Auditor (`AUDITOR`)**: Read-only access to Financial Ledgers, Trial Balance, Procurement, Inventory Movements, Anomaly Detection, and Immutable Audit Logs.

---

## 2. Granular Permission Matrix

| Permission Code | Super / Org Admin | CEO / Director | Finance Mgr | HR Mgr | Inventory Mgr | Procurement Officer | Sales Mgr | Project Mgr | Dept Mgr | Employee | Auditor |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `dashboard.view` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `organizations.view` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `organizations.manage` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `users.view` | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `users.manage` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `employees.view` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| `employees.create` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `employees.update` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `employees.delete` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `hr.confidential.view` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `leave.view` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `leave.create` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `leave.approve` | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `inventory.view` | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| `inventory.manage` | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `inventory.adjust` | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `inventory.transfer` | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `procurement.view` | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ |
| `procurement.manage` | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `purchase_requests.create`| ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `purchase_orders.create` | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `purchase_orders.approve`| ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `goods_receipts.create` | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `sales.view` | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| `sales.manage` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `invoices.view` | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| `invoices.create` | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `payments.view` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| `payments.create` | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `finance.view` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `finance.manage` | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `finance.post` | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `finance.reports.view` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `expenses.create` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `projects.view` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `projects.manage` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| `approvals.view` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `approvals.act` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `reports.view` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| `ai.forecast.view` | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| `ai.anomalies.view` | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `ai.copilot.use` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| `audit_logs.view` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 3. Separation of Duties & Approval Invariants

1. **No Self-Approval**: Any user (`created_by_id` / `requested_by_id`) who initiates a Purchase Request, Purchase Order, Expense Claim, or Leave Request is strictly blocked from approving that same transaction (`HTTP 403 SELF_APPROVAL_FORBIDDEN`), even if they hold the `purchase_orders.approve` or `approvals.act` permission (unless explicitly acting as an emergency override logged in `audit_logs`, which is disabled by default for standard operational roles).
2. **Multi-Tier Value Thresholds**:
   - Transactions `<= LKR 50,000`: Require Step 1 (`DEPARTMENT_MANAGER` or higher).
   - Transactions `> LKR 50,000`: Require Step 1 (`DEPARTMENT_MANAGER`) **AND** Step 2 (`FINANCE_MANAGER` or `CEO_DIRECTOR`).
