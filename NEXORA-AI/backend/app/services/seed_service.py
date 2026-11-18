"""NEXORA ERP — Repeatable Synthetic Demonstration Data Generator ('Nexora Demo Holdings')."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.entities import (
    Account,
    AIInsight,
    AttendanceRecord,
    AuditLog,
    BankAccount,
    Branch,
    Customer,
    Department,
    Designation,
    Employee,
    Expense,
    FinancialPeriod,
    GoodsReceipt,
    GoodsReceiptItem,
    Invoice,
    InvoiceItem,
    LeaveBalance,
    LeaveRequest,
    Milestone,
    Notification,
    Organization,
    Payment,
    PerformanceReview,
    Permission,
    Product,
    ProductCategory,
    Project,
    ProjectMember,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseRequest,
    PurchaseRequestItem,
    Role,
    RolePermission,
    SalesOrder,
    SalesOrderItem,
    SalesQuotation,
    Supplier,
    SupplierQuotation,
    Task,
    User,
    UserRole,
    Warehouse,
    WarehouseLocation,
    new_uuid,
)
from app.services.accounting_service import create_journal_entry, quantize_money
from app.services.ai_service import (
    run_business_anomaly_detection,
    run_inventory_demand_forecast,
)
from app.services.inventory_service import record_stock_movement
from app.services.workflow_service import initiate_approval_request


PERMISSIONS_CATALOG: list[tuple[str, str, str]] = [
    ("dashboard.view", "OVERVIEW", "View executive dashboard and KPI analytics"),
    ("organizations.view", "ORGANIZATION", "View organization profile, branches, and departments"),
    ("organizations.manage", "ORGANIZATION", "Create and update organizations, branches, and departments"),
    ("users.view", "SYSTEM", "View users, roles, and permission assignments"),
    ("users.manage", "SYSTEM", "Create and manage users, roles, and permissions"),
    ("employees.view", "HR", "View employee directory, attendance, and profiles"),
    ("employees.create", "HR", "Register new employees"),
    ("employees.update", "HR", "Update employee records, attendance, and performance reviews"),
    ("employees.delete", "HR", "Deactivate or remove employee records"),
    ("hr.confidential.view", "HR", "View confidential employee compensation and national ID data"),
    ("leave.view", "HR", "View leave requests and balances"),
    ("leave.create", "HR", "Submit employee leave requests"),
    ("leave.approve", "HR", "Approve or reject employee leave requests"),
    ("inventory.view", "INVENTORY", "View product catalogue, warehouses, and stock balances"),
    ("inventory.manage", "INVENTORY", "Create and update products, categories, and warehouses"),
    ("inventory.adjust", "INVENTORY", "Record manual stock receipts, issues, and adjustments"),
    ("inventory.transfer", "INVENTORY", "Execute inter-warehouse stock transfers"),
    ("procurement.view", "PROCUREMENT", "View suppliers, purchase requests, quotations, POs, and GRNs"),
    ("procurement.manage", "PROCUREMENT", "Manage suppliers and supplier quotations"),
    ("purchase_requests.create", "PROCUREMENT", "Create purchase requests"),
    ("purchase_orders.create", "PROCUREMENT", "Create purchase orders"),
    ("purchase_orders.approve", "PROCUREMENT", "Approve or reject purchase orders"),
    ("goods_receipts.create", "PROCUREMENT", "Receive deliveries and post Goods Receipt Notes"),
    ("sales.view", "SALES", "View customers, quotations, and sales orders"),
    ("sales.manage", "SALES", "Create and manage customers, quotations, and sales orders"),
    ("invoices.view", "FINANCIALS", "View customer invoices and supplier bills"),
    ("invoices.create", "FINANCIALS", "Create and issue invoices"),
    ("payments.view", "FINANCIALS", "View recorded payments and receipts"),
    ("payments.create", "FINANCIALS", "Record customer receipts and supplier payments"),
    ("finance.view", "FINANCIALS", "View chart of accounts, general ledger, and journal entries"),
    ("finance.manage", "FINANCIALS", "Create accounts and draft journal entries"),
    ("finance.post", "FINANCIALS", "Post and reverse general ledger journal entries"),
    ("finance.reports.view", "FINANCIALS", "View Trial Balance, Profit & Loss, Balance Sheet, and Cash Flow"),
    ("expenses.create", "FINANCIALS", "Submit organizational expenses"),
    ("projects.view", "MANAGEMENT", "View projects, milestones, tasks, and Kanban boards"),
    ("projects.manage", "MANAGEMENT", "Create and manage projects, budgets, and tasks"),
    ("approvals.view", "MANAGEMENT", "View workflow approval center"),
    ("approvals.act", "MANAGEMENT", "Approve, reject, or escalate workflow requests"),
    ("reports.view", "SYSTEM", "Access and export Business Intelligence reports"),
    ("ai.forecast.view", "INTELLIGENCE", "Run and view Inventory Demand & Sales Forecasting models"),
    ("ai.anomalies.view", "INTELLIGENCE", "Run and review Business Anomaly Detection alerts"),
    ("ai.copilot.use", "INTELLIGENCE", "Interact with Nexora AI Business Copilot"),
    ("audit_logs.view", "SYSTEM", "Inspect immutable security and operational audit logs"),
]

ROLE_DEFINITIONS: dict[str, tuple[str, str, list[str]]] = {
    "SUPER_ADMIN": (
        "Super Admin",
        "Full multi-tenant platform and enterprise administration",
        [p[0] for p in PERMISSIONS_CATALOG],
    ),
    "ORG_ADMIN": (
        "Organization Admin",
        "Full administrative control within the organization",
        [p[0] for p in PERMISSIONS_CATALOG],
    ),
    "CEO_DIRECTOR": (
        "CEO / Director",
        "Executive oversight, financial intelligence, high-value approvals, and AI insights",
        [
            "dashboard.view", "organizations.view", "users.view", "employees.view", "hr.confidential.view",
            "leave.view", "leave.approve", "inventory.view", "procurement.view", "purchase_orders.approve",
            "sales.view", "invoices.view", "payments.view", "finance.view", "finance.reports.view",
            "projects.view", "projects.manage", "approvals.view", "approvals.act", "reports.view",
            "ai.forecast.view", "ai.anomalies.view", "ai.copilot.use", "audit_logs.view",
        ],
    ),
    "FINANCE_MANAGER": (
        "Finance Manager",
        "Manages General Ledger, AP/AR, Financial Statements, Expenses, and high-value PO approvals",
        [
            "dashboard.view", "organizations.view", "employees.view", "hr.confidential.view",
            "inventory.view", "procurement.view", "purchase_orders.approve", "sales.view",
            "invoices.view", "invoices.create", "payments.view", "payments.create",
            "finance.view", "finance.manage", "finance.post", "finance.reports.view", "expenses.create",
            "approvals.view", "approvals.act", "reports.view", "ai.forecast.view", "ai.anomalies.view",
            "ai.copilot.use", "audit_logs.view",
        ],
    ),
    "HR_MANAGER": (
        "HR Manager",
        "Manages Employee lifecycle, compensation, attendance, leave approvals, and performance reviews",
        [
            "dashboard.view", "organizations.view", "users.view", "employees.view", "employees.create",
            "employees.update", "employees.delete", "hr.confidential.view", "leave.view", "leave.create",
            "leave.approve", "projects.view", "approvals.view", "approvals.act", "reports.view", "ai.copilot.use",
        ],
    ),
    "INVENTORY_MANAGER": (
        "Inventory Manager",
        "Manages Products, Warehouses, Stock Movements, Adjustments, Transfers, and Demand Forecasting",
        [
            "dashboard.view", "organizations.view", "inventory.view", "inventory.manage",
            "inventory.adjust", "inventory.transfer", "procurement.view", "purchase_requests.create",
            "goods_receipts.create", "sales.view", "reports.view", "ai.forecast.view", "ai.anomalies.view",
            "ai.copilot.use",
        ],
    ),
    "PROCUREMENT_OFFICER": (
        "Procurement Officer",
        "Manages Suppliers, Purchase Requests, RFQs, Purchase Orders, and Goods Receipt Notes",
        [
            "dashboard.view", "organizations.view", "inventory.view", "procurement.view",
            "procurement.manage", "purchase_requests.create", "purchase_orders.create",
            "goods_receipts.create", "invoices.view", "approvals.view", "reports.view",
            "ai.forecast.view", "ai.anomalies.view", "ai.copilot.use",
        ],
    ),
    "SALES_MANAGER": (
        "Sales Manager",
        "Manages Customers, Quotations, Sales Orders, Invoices, Receipts, and Sales Forecasting",
        [
            "dashboard.view", "organizations.view", "inventory.view", "sales.view", "sales.manage",
            "invoices.view", "invoices.create", "payments.view", "payments.create",
            "reports.view", "ai.forecast.view", "ai.copilot.use",
        ],
    ),
    "PROJECT_MANAGER": (
        "Project Manager",
        "Manages Projects, Budgets, Milestones, Tasks, and Kanban delivery",
        [
            "dashboard.view", "organizations.view", "employees.view", "leave.view", "leave.create",
            "purchase_requests.create", "expenses.create", "projects.view", "projects.manage",
            "approvals.view", "reports.view", "ai.copilot.use",
        ],
    ),
    "DEPARTMENT_MANAGER": (
        "Department Manager",
        "Manages Departmental Operations, Leave Approvals, and Step-1 Purchase Approvals",
        [
            "dashboard.view", "organizations.view", "employees.view", "leave.view", "leave.create",
            "leave.approve", "inventory.view", "procurement.view", "purchase_requests.create",
            "purchase_orders.approve", "expenses.create", "projects.view", "projects.manage",
            "approvals.view", "approvals.act", "reports.view", "ai.forecast.view", "ai.copilot.use",
        ],
    ),
    "EMPLOYEE": (
        "Employee",
        "Self-service employee portal for attendance, leave requests, expenses, and assigned tasks",
        [
            "dashboard.view", "organizations.view", "employees.view", "leave.view", "leave.create",
            "purchase_requests.create", "expenses.create", "projects.view", "approvals.view",
        ],
    ),
    "AUDITOR": (
        "Auditor",
        "Read-only compliance, financial ledger, anomaly detection, and audit trail access",
        [
            "dashboard.view", "organizations.view", "users.view", "employees.view", "hr.confidential.view",
            "leave.view", "inventory.view", "procurement.view", "sales.view", "invoices.view",
            "payments.view", "finance.view", "finance.reports.view", "projects.view", "approvals.view",
            "reports.view", "ai.forecast.view", "ai.anomalies.view", "ai.copilot.use", "audit_logs.view",
        ],
    ),
}


def seed_demo_data(db: Session) -> dict[str, int | str]:
    """Idempotently populate 'Nexora Demo Holdings' and secondary tenant 'Ceylon Horizon Logistics'."""
    existing_org = db.execute(
        select(Organization).where(Organization.code == "NEXORA-DEMO")
    ).scalar_one_or_none()
    if existing_org:
        return {"status": "already_seeded", "organization_id": existing_org.id}

    today = date.today()
    default_pw_hash = hash_password("Nexora#2026")

    # ------------------------------------------------------------------------
    # 1. PERMISSIONS & ROLES
    # ------------------------------------------------------------------------
    perm_map: dict[str, Permission] = {}
    for code, module, desc in PERMISSIONS_CATALOG:
        p = Permission(id=new_uuid(), code=code, module=module, description=desc)
        db.add(p)
        perm_map[code] = p
    db.flush()

    role_map: dict[str, Role] = {}
    for r_code, (r_name, r_desc, p_codes) in ROLE_DEFINITIONS.items():
        r = Role(
            id=new_uuid(),
            organization_id=None,
            code=r_code,
            name=r_name,
            description=r_desc,
            is_system=True,
        )
        db.add(r)
        role_map[r_code] = r
        db.flush()
        for pc in p_codes:
            if pc in perm_map:
                db.add(RolePermission(id=new_uuid(), role_id=r.id, permission_id=perm_map[pc].id))
    db.flush()

    # ------------------------------------------------------------------------
    # 2. ORGANIZATIONS (Primary Demo Tenant + Isolated Secondary Tenant)
    # ------------------------------------------------------------------------
    org = Organization(
        id=new_uuid(),
        name="Nexora Demo Holdings",
        code="NEXORA-DEMO",
        registration_number="PV-00294812",
        tax_id="TIN-114928300-7000",
        email="corporate@nexoraholdings.lk",
        phone="+94 11 234 5678",
        address="Level 28, West Tower, World Trade Center, Echelon Square, Colombo 01, Sri Lanka",
        default_currency="LKR",
        timezone="Asia/Colombo",
        fiscal_year_start_month=4,
        date_format="DD MMM YYYY",
        is_demo=True,
        is_active=True,
    )
    secondary_org = Organization(
        id=new_uuid(),
        name="Ceylon Horizon Logistics Ltd",
        code="CEYLON-HORIZON",
        registration_number="PV-00881122",
        tax_id="TIN-998811220-7000",
        email="ops@ceylonhorizon.lk",
        phone="+94 11 499 1100",
        address="No. 142, Vauxhall Street, Colombo 02, Sri Lanka",
        default_currency="LKR",
        timezone="Asia/Colombo",
        fiscal_year_start_month=4,
        date_format="DD MMM YYYY",
        is_demo=True,
        is_active=True,
    )
    db.add_all([org, secondary_org])
    db.flush()

    # ------------------------------------------------------------------------
    # 3. BRANCHES & DEPARTMENTS
    # ------------------------------------------------------------------------
    branches_data = [
        ("BR-CMB-HQ", "Colombo World Trade Center HQ", "Colombo", "Level 28, WTC, Colombo 01", "Ashan Jayawardena", True),
        ("BR-PEL-DIST", "Peliyagoda Logistics & Distribution Park", "Peliyagoda", "210 Negombo Road, Peliyagoda", "Roshan Perera", False),
        ("BR-KDY-REG", "Kandy Central Regional Branch", "Kandy", "48 Peradeniya Road, Kandy", "Dilani Ratnayake", False),
        ("BR-GAL-STH", "Galle Southern Operations Hub", "Galle", "19 Wakwella Road, Galle", "Chathura Silva", False),
    ]
    branches: list[Branch] = []
    for code, name, city, addr, mgr, is_hq in branches_data:
        b = Branch(
            id=new_uuid(),
            organization_id=org.id,
            code=code,
            name=name,
            city=city,
            address=addr,
            phone="+94 11 234 5600",
            manager_name=mgr,
            is_headquarters=is_hq,
        )
        db.add(b)
        branches.append(b)
    db.flush()

    depts_data = [
        ("DEPT-EXEC", "Executive & Corporate Strategy", Decimal("18500000.00")),
        ("DEPT-FIN", "Finance & Treasury", Decimal("14200000.00")),
        ("DEPT-HR", "Human Capital & Administration", Decimal("9800000.00")),
        ("DEPT-SCM", "Supply Chain & Warehousing", Decimal("26500000.00")),
        ("DEPT-PROC", "Strategic Procurement", Decimal("22000000.00")),
        ("DEPT-SALES", "Enterprise Sales & Distribution", Decimal("31000000.00")),
        ("DEPT-ENG", "Digital Transformation & Projects", Decimal("24500000.00")),
        ("DEPT-AUD", "Internal Audit & Risk Compliance", Decimal("7500000.00")),
    ]
    depts: list[Department] = []
    for idx, (code, name, budget) in enumerate(depts_data):
        d = Department(
            id=new_uuid(),
            organization_id=org.id,
            branch_id=branches[idx % len(branches)].id,
            code=code,
            name=name,
            budget_allocated=budget,
        )
        db.add(d)
        depts.append(d)
    db.flush()

    # ------------------------------------------------------------------------
    # 4. DEMO USERS FOR ALL 12 ROLES (+ Secondary Tenant User)
    # ------------------------------------------------------------------------
    demo_users_spec = [
        ("admin@nexora.lk", "Ashan Jayawardena (Super Admin)", "SUPER_ADMIN", True, 0),
        ("orgadmin@nexora.lk", "Nadeesha Wickramasinghe (Org Admin)", "ORG_ADMIN", False, 0),
        ("ceo@nexora.lk", "Dr. Kavinda Senanayake (CEO)", "CEO_DIRECTOR", False, 0),
        ("finance@nexora.lk", "Malini Fernando (Finance Manager)", "FINANCE_MANAGER", False, 1),
        ("hr@nexora.lk", "Dinithi Gunawardena (HR Manager)", "HR_MANAGER", False, 2),
        ("inventory@nexora.lk", "Roshan Perera (Inventory Manager)", "INVENTORY_MANAGER", False, 3),
        ("procurement@nexora.lk", "Tharindu Bandara (Procurement Officer)", "PROCUREMENT_OFFICER", False, 4),
        ("sales@nexora.lk", "Shehan De Silva (Sales Manager)", "SALES_MANAGER", False, 5),
        ("projects@nexora.lk", "ishara@nexora.lk", "PROJECT_MANAGER", False, 6),
        ("deptmanager@nexora.lk", "Kasun Rajapaksa (Department Manager)", "DEPARTMENT_MANAGER", False, 3),
        ("employee@nexora.lk", "Amaya Wijeratne (Senior Analyst)", "EMPLOYEE", False, 6),
        ("auditor@nexora.lk", "Ruwan Samaraweera (Chief Auditor)", "AUDITOR", False, 7),
    ]
    # Fix email/name tuple for projects manager
    demo_users_spec[8] = ("projects@nexora.lk", "Ishara Karunaratne (Project Manager)", "PROJECT_MANAGER", False, 6)

    users_by_role: dict[str, User] = {}
    for email, full_name, r_code, is_sa, dept_idx in demo_users_spec:
        u = User(
            id=new_uuid(),
            organization_id=org.id,
            branch_id=branches[0].id,
            department_id=depts[dept_idx].id,
            email=email,
            full_name=full_name,
            password_hash=default_pw_hash,
            is_super_admin=is_sa,
            is_active=True,
            theme_preference="dark",
            last_login_at=datetime.now(timezone.utc),
        )
        db.add(u)
        db.flush()
        db.add(UserRole(id=new_uuid(), user_id=u.id, role_id=role_map[r_code].id))
        users_by_role[r_code] = u

    # Secondary tenant user for multi-tenant isolation testing
    sec_user = User(
        id=new_uuid(),
        organization_id=secondary_org.id,
        email="admin@ceylonhorizon.lk",
        full_name="Nuwan Dissanayake (Horizon Admin)",
        password_hash=default_pw_hash,
        is_super_admin=False,
        is_active=True,
    )
    db.add(sec_user)
    db.flush()
    db.add(UserRole(id=new_uuid(), user_id=sec_user.id, role_id=role_map["ORG_ADMIN"].id))
    db.flush()

    # ------------------------------------------------------------------------
    # 5. HUMAN RESOURCES (35 Employees, Attendance, Leave, Performance)
    # ------------------------------------------------------------------------
    designations_spec = [
        ("Chief Executive Officer", "E1"),
        ("Head of Finance & Treasury", "M1"),
        ("Human Capital Manager", "M1"),
        ("Supply Chain & Logistics Lead", "M1"),
        ("Senior Procurement Specialist", "L4"),
        ("Enterprise Sales Director", "M1"),
        ("Principal Solutions Architect", "L5"),
        ("Senior ERP Software Engineer", "L4"),
        ("Warehouse Operations Supervisor", "L3"),
        ("Financial Accountant", "L3"),
    ]
    designations: list[Designation] = []
    for idx, (title, grade) in enumerate(designations_spec):
        des = Designation(
            id=new_uuid(),
            organization_id=org.id,
            title=title,
            grade=grade,
            department_id=depts[idx % len(depts)].id,
        )
        db.add(des)
        designations.append(des)
    db.flush()

    first_names = [
        "Ashan", "Nadeesha", "Kavinda", "Malini", "Dinithi", "Roshan", "Tharindu", "Shehan",
        "Ishara", "Kasun", "Amaya", "Ruwan", "Dilshan", "Chathuri", "Sajith", "Piumi",
        "Harsha", "Nethmi", "Lasith", "Sachini", "Gayan", "Hashini", "Dinesh", "oshadi",
        "Pradeep", "hiruni", "Sandun", "Kaveesha", "buddhika", "Thilini", "Charith", "Madhavi",
        "Janaka", "Anjali", "Supun",
    ]
    last_names = [
        "Jayawardena", "Wickramasinghe", "Senanayake", "Fernando", "Gunawardena", "Perera",
        "Bandara", "De Silva", "Karunaratne", "Rajapaksa", "Wijeratne", "Samaraweera",
        "Ekanayake", "Ratnayake", "Abeysekera", "Liyanage", "Dissanayake", "Herath",
    ]

    employees: list[Employee] = []
    for i in range(35):
        fn = first_names[i % len(first_names)].capitalize()
        ln = last_names[i % len(last_names)]
        dept = depts[i % len(depts)]
        branch = branches[i % len(branches)]
        desig = designations[i % len(designations)]
        salary = Decimal(str(145000 + (i % 10) * 32000))
        emp = Employee(
            id=new_uuid(),
            organization_id=org.id,
            branch_id=branch.id,
            department_id=dept.id,
            designation_id=desig.id,
            employee_code=f"EMP-{2024001 + i}",
            first_name=fn,
            last_name=ln,
            email=f"{fn.lower()}.{ln.lower().replace(' ', '')}{i}@nexoraholdings.lk",
            phone=f"+94 77 {210 + i:03d} {4100 + i:04d}",
            national_id=f"199{i % 9}{10000000 + i * 137:08d}",
            employment_type="FULL_TIME" if i % 7 != 0 else "CONTRACT",
            employment_status="ACTIVE" if i != 33 else "ON_LEAVE",
            join_date=today - timedelta(days=450 - i * 9),
            base_salary=salary,
            emergency_contact_name=f"{ln} Family Contact",
            emergency_contact_phone=f"+94 71 {300 + i:03d} {8800 + i:04d}",
        )
        db.add(emp)
        employees.append(emp)
    db.flush()

    # Leave Balances, Attendance Records & Performance Reviews
    for idx, emp in enumerate(employees):
        for l_type, ent, used in [("ANNUAL", 14, idx % 5), ("CASUAL", 7, idx % 3), ("MEDICAL", 7, idx % 2)]:
            db.add(
                LeaveBalance(
                    id=new_uuid(),
                    organization_id=org.id,
                    employee_id=emp.id,
                    year=today.year,
                    leave_type=l_type,
                    entitled_days=Decimal(str(ent)),
                    used_days=Decimal(str(used)),
                    remaining_days=Decimal(str(ent - used)),
                )
            )
        # Recent 5 days attendance for first 18 employees
        if idx < 18:
            for d_back in range(5):
                att_date = today - timedelta(days=d_back)
                st = "PRESENT" if (idx + d_back) % 8 != 0 else ("REMOTE" if d_back % 2 == 0 else "LATE")
                db.add(
                    AttendanceRecord(
                        id=new_uuid(),
                        organization_id=org.id,
                        employee_id=emp.id,
                        attendance_date=att_date,
                        check_in="08:35" if st != "LATE" else "09:25",
                        check_out="17:30",
                        status=st,
                        hours_worked=Decimal("8.50") if st != "LATE" else Decimal("7.75"),
                        notes="Biometric terminal check-in" if st == "PRESENT" else "Hybrid work schedule",
                    )
                )
        if idx < 12:
            kpi_s = Decimal(str(round(3.8 + (idx % 5) * 0.25, 2)))
            comp_s = Decimal(str(round(3.9 + (idx % 4) * 0.22, 2)))
            db.add(
                PerformanceReview(
                    id=new_uuid(),
                    organization_id=org.id,
                    employee_id=emp.id,
                    reviewer_id=users_by_role["HR_MANAGER"].id,
                    review_period=f"FY {today.year} H1",
                    kpi_score=kpi_s,
                    competency_score=comp_s,
                    overall_rating="OUTSTANDING" if kpi_s >= Decimal("4.5") else "EXCEEDS",
                    strengths="Strong operational delivery, cross-departmental collaboration, and ERP workflow discipline.",
                    improvements="Continue expanding predictive analytics and automation adoption.",
                    status="COMPLETED",
                    review_date=today - timedelta(days=15 + idx),
                )
            )

    # Sample Leave Requests
    for i in range(6):
        st = "APPROVED" if i < 3 else "PENDING"
        lr = LeaveRequest(
            id=new_uuid(),
            organization_id=org.id,
            employee_id=employees[i + 4].id,
            requested_by_user_id=users_by_role["EMPLOYEE"].id,
            leave_type="ANNUAL" if i % 2 == 0 else "MEDICAL",
            start_date=today + timedelta(days=3 + i * 2),
            end_date=today + timedelta(days=5 + i * 2),
            days_count=Decimal("2.0"),
            reason="Family commitment and scheduled personal leave",
            status=st,
            approved_by_id=users_by_role["HR_MANAGER"].id if st == "APPROVED" else None,
        )
        db.add(lr)
    db.flush()

    # ------------------------------------------------------------------------
    # 6. CHART OF ACCOUNTS (Double-Entry Foundation)
    # ------------------------------------------------------------------------
    coa_spec = [
        ("1000", "Cash & Bank — Bank of Ceylon Corporate Operating", "ASSET", "CASH_BANK", "DEBIT"),
        ("1010", "Commercial Bank — Treasury Reserve Account", "ASSET", "CASH_BANK", "DEBIT"),
        ("1100", "Accounts Receivable — Trade Debtors", "ASSET", "ACCOUNTS_RECEIVABLE", "DEBIT"),
        ("1200", "Inventory Asset — Finished Goods & Stock", "ASSET", "INVENTORY", "DEBIT"),
        ("1500", "Property, Plant & Warehouse Equipment", "ASSET", "FIXED_ASSET", "DEBIT"),
        ("2000", "Accounts Payable — Trade Creditors", "LIABILITY", "ACCOUNTS_PAYABLE", "CREDIT"),
        ("2100", "VAT & Statutory Tax Payable", "LIABILITY", "TAX_PAYABLE", "CREDIT"),
        ("2200", "Accrued Operating Liabilities", "LIABILITY", "ACCOUNTS_PAYABLE", "CREDIT"),
        ("3000", "Share Capital — Nexora Holdings Equity", "EQUITY", "RETAINED_EARNINGS", "CREDIT"),
        ("3100", "Retained Earnings", "EQUITY", "RETAINED_EARNINGS", "CREDIT"),
        ("4000", "Enterprise Product Sales Revenue", "REVENUE", "SALES_REVENUE", "CREDIT"),
        ("4100", "Managed Services & Maintenance Revenue", "REVENUE", "SALES_REVENUE", "CREDIT"),
        ("5000", "Cost of Goods Sold (COGS)", "EXPENSE", "COGS", "DEBIT"),
        ("5100", "Inventory Shrinkage & Adjustment Expense", "EXPENSE", "COGS", "DEBIT"),
        ("6000", "Executive & Staff Salaries Expense", "EXPENSE", "OPERATING_EXPENSE", "DEBIT"),
        ("6100", "Warehouse Rent, Utilities & Cold-Chain Power", "EXPENSE", "OPERATING_EXPENSE", "DEBIT"),
        ("6200", "Cloud Infrastructure, AI Compute & Software Licenses", "EXPENSE", "OPERATING_EXPENSE", "DEBIT"),
        ("6300", "Inland Freight, Fleet & Customs Logistics", "EXPENSE", "OPERATING_EXPENSE", "DEBIT"),
    ]
    accounts_by_code: dict[str, Account] = {}
    for code, name, a_type, a_sub, norm_bal in coa_spec:
        acc = Account(
            id=new_uuid(),
            organization_id=org.id,
            code=code,
            name=name,
            account_type=a_type,
            account_subtype=a_sub,
            normal_balance=norm_bal,
            current_balance=Decimal("0.00"),
            is_system=True,
        )
        db.add(acc)
        accounts_by_code[code] = acc
    db.flush()

    db.add(
        FinancialPeriod(
            id=new_uuid(),
            organization_id=org.id,
            name=f"FY {today.year}/{today.year + 1}",
            start_date=date(today.year, 4, 1),
            end_date=date(today.year + 1, 3, 31),
            is_closed=False,
        )
    )
    bank_acc = BankAccount(
        id=new_uuid(),
        organization_id=org.id,
        gl_account_id=accounts_by_code["1000"].id,
        account_name="Nexora Holdings Corporate Operating LKR",
        bank_name="Bank of Ceylon — Corporate Branch",
        account_number="000849201184",
        branch_name="Colombo 01",
        currency="LKR",
        current_balance=Decimal("45000000.00"),
    )
    db.add(bank_acc)
    db.flush()

    # Post Initial Share Capital & Equipment Opening Journal Entry
    create_journal_entry(
        db,
        organization_id=org.id,
        entry_date=today - timedelta(days=180),
        reference_type="OPENING_CAPITAL",
        reference_id=org.id,
        reference_number="CAP-OPEN-2026",
        description="Initial corporate capitalization and warehouse infrastructure capitalization",
        lines=[
            {"account_code": "1000", "debit": Decimal("38000000.00"), "credit": Decimal("0.00")},
            {"account_code": "1500", "debit": Decimal("22000000.00"), "credit": Decimal("0.00")},
            {"account_code": "3000", "debit": Decimal("0.00"), "credit": Decimal("60000000.00")},
        ],
        created_by_id=users_by_role["FINANCE_MANAGER"].id,
        auto_post=True,
    )

    # ------------------------------------------------------------------------
    # 7. SUPPLIERS & CUSTOMERS
    # ------------------------------------------------------------------------
    suppliers_spec = [
        ("SUP-001", "Lanka Industrial Tech & Automation (Pvt) Ltd", "Nimal Perera", "supply@lankatech.lk", 30, "4.85", "97.50"),
        ("SUP-002", "Ceylon Precision Electronics & Components", "Rohan Wijesinghe", "orders@ceylonelec.lk", 45, "4.70", "95.20"),
        ("SUP-003", "Asia Pacific Enterprise Hardware Distributors", "Kelvin Tan", "ap-desk@apenterprise.sg", 30, "4.65", "94.80"),
        ("SUP-004", "Colombo Smart Energy & Solar Systems", "Chaminda Silva", "sales@colombosolar.lk", 30, "4.55", "92.40"),
        ("SUP-005", "Serendib Packaging & Warehouse Robotics", "Dilrukshi Fernando", "b2b@serendibpack.lk", 15, "4.40", "91.00"),
        ("SUP-006", "Southern Polymer & Industrial Consumables", "Prasanna Mendis", "info@southernpolymer.lk", 30, "4.30", "89.50"),
        ("SUP-007", "Apex Global Networking & Fiber Systems", "Tariq Mahmood", "enterprise@apexnet.lk", 45, "4.75", "96.10"),
        ("SUP-008", "Highland Office & Data Center Ergonomics", "Shalini Cooray", "orders@highlandergo.lk", 30, "4.50", "93.00"),
    ]
    suppliers: list[Supplier] = []
    for code, name, contact, email, terms, rating, otd in suppliers_spec:
        s = Supplier(
            id=new_uuid(),
            organization_id=org.id,
            supplier_code=code,
            name=name,
            contact_person=contact,
            email=email,
            phone="+94 11 288 9900",
            tax_id=f"SUP-TIN-{code}",
            address="Colombo Industrial Zone, Sri Lanka",
            payment_terms_days=terms,
            rating=Decimal(rating),
            on_time_delivery_rate=Decimal(otd),
        )
        db.add(s)
        suppliers.append(s)
    db.flush()

    customers_spec = [
        ("CUS-001", "Dialog Enterprise Solutions PLC", "CORPORATE", "25000000.00"),
        ("CUS-002", "John Keells Logistics & Retail Group", "CORPORATE", "30000000.00"),
        ("CUS-003", "Hemas Healthcare & Manufacturing", "CORPORATE", "20000000.00"),
        ("CUS-004", "MAS Active Apparel Tech Division", "CORPORATE", "25000000.00"),
        ("CUS-005", "Cargills Retail Supply Chain Hub", "DISTRIBUTOR", "18000000.00"),
        ("CUS-006", "Hayleys Industrial Engineering", "CORPORATE", "22000000.00"),
        ("CUS-007", "Aitken Spence Maritime & Freight", "CORPORATE", "15000000.00"),
        ("CUS-008", "Singer Sri Lanka Commercial Distribution", "DISTRIBUTOR", "20000000.00"),
        ("CUS-009", "Softlogic Retail & Enterprise Systems", "CORPORATE", "16000000.00"),
        ("CUS-010", "Brandix Smart Factory Operations", "CORPORATE", "24000000.00"),
        ("CUS-011", "Kandy City Commercial Supercenter", "RETAIL", "8000000.00"),
        ("CUS-012", "Galle Southern Marine & Hospitality", "CORPORATE", "12000000.00"),
        ("CUS-013", "Lanka Hospitals Diagnostics Network", "CORPORATE", "15000000.00"),
        ("CUS-014", "abans Enterprise Solutions Hub", "DISTRIBUTOR", "18000000.00"),
        ("CUS-015", "Dilmah Global Packaging & Logistics", "CORPORATE", "20000000.00"),
        ("CUS-016", "Orion City Tech Park Tenants Association", "CORPORATE", "14000000.00"),
        ("CUS-017", "Negombo Coastal Trading Consortium", "DISTRIBUTOR", "9500000.00"),
        ("CUS-018", "Kurunegala Agro-Industrial Supply Co", "RETAIL", "7500000.00"),
        ("CUS-019", "Jaffna Northern Commercial Hub", "DISTRIBUTOR", "11000000.00"),
        ("CUS-020", "Matara Southern Retail Networks", "RETAIL", "6500000.00"),
    ]
    customers: list[Customer] = []
    for code, name, c_type, cred in customers_spec:
        c = Customer(
            id=new_uuid(),
            organization_id=org.id,
            customer_code=code,
            name=name,
            customer_type=c_type,
            contact_person=f"Procurement Desk — {code}",
            email=f"accounts@{code.lower()}.lk",
            phone="+94 11 450 2200",
            tax_id=f"CUS-TIN-{code}",
            billing_address="Colombo Commercial District, Sri Lanka",
            shipping_address="Central Receiving Bay, Sri Lanka",
            credit_limit=Decimal(cred),
            outstanding_balance=Decimal("0.00"),
            payment_terms_days=30,
        )
        db.add(c)
        customers.append(c)
    db.flush()

    # ------------------------------------------------------------------------
    # 8. WAREHOUSES, CATEGORIES & 50 PRODUCTS
    # ------------------------------------------------------------------------
    warehouses_spec = [
        ("WH-PEL-01", "Peliyagoda Automated Central Fulfillment Center", branches[1].id, "Roshan Perera", 25000),
        ("WH-CMB-02", "Colombo Port Bonded & High-Value Tech Vault", branches[0].id, "Kasun Rajapaksa", 12000),
        ("WH-KDY-03", "Kandy Hill-Country Regional Distribution Depot", branches[2].id, "Dilani Ratnayake", 8000),
    ]
    warehouses: list[Warehouse] = []
    for code, name, b_id, mgr, cap in warehouses_spec:
        wh = Warehouse(
            id=new_uuid(),
            organization_id=org.id,
            branch_id=b_id,
            code=code,
            name=name,
            address="Industrial Logistics Zone, Sri Lanka",
            manager_name=mgr,
            capacity_units=cap,
        )
        db.add(wh)
        warehouses.append(wh)
        db.flush()
        db.add(
            WarehouseLocation(
                id=new_uuid(),
                organization_id=org.id,
                warehouse_id=wh.id,
                zone="ZONE-A",
                aisle="A1",
                rack="R01",
                bin_code=f"{code}-A1-R01",
            )
        )
    db.flush()

    categories_spec = [
        ("CAT-COMP", "Enterprise Computing & Servers"),
        ("CAT-NET", "Networking, Fiber & Security Appliances"),
        ("CAT-AUTO", "Warehouse Barcode, RFID & IoT Scanners"),
        ("CAT-PWR", "Industrial UPS & Solar Energy Storage"),
        ("CAT-PACK", "Smart Packaging & Logistics Consumables"),
        ("CAT-ERGO", "Command Center Displays & Ergonomics"),
    ]
    categories: list[ProductCategory] = []
    for code, name in categories_spec:
        cat = ProductCategory(
            id=new_uuid(),
            organization_id=org.id,
            code=code,
            name=name,
            description=f"{name} product line",
        )
        db.add(cat)
        categories.append(cat)
    db.flush()

    base_product_templates = [
        ("Nexora Rack Server Blade X9", "UNIT", 420000, 560000, 8, 15),
        ("Enterprise Workstation Pro Z4", "UNIT", 185000, 248000, 12, 25),
        ("Managed Layer-3 Core Switch 48P", "UNIT", 112000, 154000, 15, 30),
        ("Wi-Fi 7 Industrial Tri-Band Access Point", "PCS", 34000, 48500, 25, 50),
        ("Long-Range 2D Barcode & RFID Terminal", "PCS", 46000, 66000, 20, 40),
        ("Thermal Industrial Label Printer ZT-400", "UNIT", 78000, 108000, 10, 20),
        ("Online Double-Conversion Smart UPS 3kVA", "UNIT", 95000, 132000, 12, 24),
        ("Lithium Iron Phosphate Rack Battery 5kWh", "UNIT", 265000, 345000, 6, 12),
        ("Anti-Static Smart Pallet Wrap Roll (Box)", "BOX", 8500, 12800, 45, 90),
        ("49-Inch Curved Command Center Monitor", "UNIT", 168000, 225000, 8, 16),
    ]

    products: list[Product] = []
    for i in range(50):
        tpl_name, uom, cost_int, sell_int, reorder_lvl, reorder_qty = base_product_templates[i % len(base_product_templates)]
        cat = categories[i % len(categories)]
        sup = suppliers[i % len(suppliers)]
        variant_num = (i // len(base_product_templates)) + 1
        sku = f"NEX-{cat.code.split('-')[1]}-{101 + i:03d}"
        cost_dec = Decimal(str(cost_int + (variant_num - 1) * 4500))
        sell_dec = Decimal(str(sell_int + (variant_num - 1) * 6500))

        p = Product(
            id=new_uuid(),
            organization_id=org.id,
            category_id=cat.id,
            sku=sku,
            barcode=f"4792026{10000 + i:05d}",
            qr_code=f"NEXORA://{sku}",
            name=f"{tpl_name} — Series {variant_num}00 (#{i + 1})",
            description=f"Enterprise-grade {tpl_name} engineered for high-reliability commercial deployments.",
            uom=uom,
            cost_price=cost_dec,
            weighted_avg_cost=cost_dec,
            selling_price=sell_dec,
            reorder_level=Decimal(str(reorder_lvl)),
            reorder_quantity=Decimal(str(reorder_qty)),
            lead_time_days=5 + (i % 10),
            preferred_supplier_id=sup.id,
            track_batch=(i % 3 == 0),
        )
        db.add(p)
        products.append(p)
    db.flush()

    # ------------------------------------------------------------------------
    # 9. PROCUREMENT, GOODS RECEIPTS, INVENTORY STOCK & AP ACCOUNTING
    # ------------------------------------------------------------------------
    total_initial_inventory_value = Decimal("0.00")

    for p_idx, prod in enumerate(products):
        wh = warehouses[p_idx % len(warehouses)]
        # Make 8 products intentionally low-stock so Low-Stock Alerts & Replenishment AI highlight them
        if p_idx < 8:
            init_qty = max(Decimal("2.00"), prod.reorder_level - Decimal("4.00"))
        else:
            init_qty = prod.reorder_level + Decimal(str(35 + (p_idx % 20) * 3))

        mov = record_stock_movement(
            db,
            organization_id=org.id,
            product_id=prod.id,
            warehouse_id=wh.id,
            movement_type="RECEIPT",
            quantity=init_qty,
            unit_cost=prod.cost_price,
            reference_type="INITIAL_GRN",
            reference_id=wh.id,
            reference_number=f"GRN-OPEN-{1001 + p_idx}",
            performed_by_id=users_by_role["INVENTORY_MANAGER"].id,
            notes="Opening verified stock receipt",
        )
        total_initial_inventory_value += quantize_money(init_qty * prod.cost_price)

    # Post balanced Journal Entry for Opening Inventory Receipt (Debit Inventory 1200, Credit AP 2000 & Cash 1000)
    ap_portion = quantize_money(total_initial_inventory_value * Decimal("0.35"))
    cash_portion = quantize_money(total_initial_inventory_value - ap_portion)
    create_journal_entry(
        db,
        organization_id=org.id,
        entry_date=today - timedelta(days=95),
        reference_type="INITIAL_INVENTORY",
        reference_id=org.id,
        reference_number="GRN-OPEN-BATCH",
        description="Opening multi-warehouse inventory valuation and supplier settlement",
        lines=[
            {"account_code": "1200", "debit": total_initial_inventory_value, "credit": Decimal("0.00")},
            {"account_code": "2000", "debit": Decimal("0.00"), "credit": ap_portion},
            {"account_code": "1000", "debit": Decimal("0.00"), "credit": cash_portion},
        ],
        created_by_id=users_by_role["FINANCE_MANAGER"].id,
        auto_post=True,
    )

    # Create Purchase Requests, Supplier Quotations, Purchase Orders (Approved & Pending) & GRNs
    for po_i in range(8):
        sup = suppliers[po_i % len(suppliers)]
        prod = products[(po_i * 3) % len(products)]
        qty = Decimal(str(10 + po_i * 4))
        # Make PO #7 have a +30% price spike so Anomaly Detection flags it!
        unit_p = quantize_money(prod.cost_price * (Decimal("1.32") if po_i == 6 else Decimal("1.00")))
        sub_t = quantize_money(qty * unit_p)
        tax_t = quantize_money(sub_t * Decimal("0.08"))
        tot_t = quantize_money(sub_t + tax_t)

        pr = PurchaseRequest(
            id=new_uuid(),
            organization_id=org.id,
            branch_id=branches[0].id,
            department_id=depts[3].id,
            pr_number=f"PR-2026-{101 + po_i:03d}",
            requested_by_id=users_by_role["PROCUREMENT_OFFICER"].id,
            required_date=today + timedelta(days=14),
            estimated_total=tot_t,
            status="APPROVED" if po_i < 5 else "PENDING_APPROVAL",
            justification=f"Quarterly stock replenishment for {prod.name}",
            approved_by_id=users_by_role["DEPARTMENT_MANAGER"].id if po_i < 5 else None,
        )
        db.add(pr)
        db.flush()
        db.add(
            PurchaseRequestItem(
                id=new_uuid(),
                purchase_request_id=pr.id,
                product_id=prod.id,
                quantity=qty,
                estimated_unit_price=unit_p,
                line_total=sub_t,
            )
        )
        db.add(
            SupplierQuotation(
                id=new_uuid(),
                organization_id=org.id,
                purchase_request_id=pr.id,
                supplier_id=sup.id,
                quotation_number=f"RFQ-{sup.supplier_code}-{201 + po_i}",
                quoted_total=tot_t,
                lead_time_days=7,
                validity_date=today + timedelta(days=30),
                is_selected=True,
                notes="Competitive tier-1 distributor pricing",
            )
        )

        po_status = "RECEIVED" if po_i < 4 else ("APPROVED" if po_i == 4 else "PENDING_APPROVAL")
        po = PurchaseOrder(
            id=new_uuid(),
            organization_id=org.id,
            po_number=f"PO-2026-{301 + po_i:03d}",
            supplier_id=sup.id,
            purchase_request_id=pr.id,
            warehouse_id=warehouses[0].id,
            order_date=today - timedelta(days=30 - po_i * 3),
            expected_delivery_date=today + timedelta(days=7 + po_i),
            subtotal=sub_t,
            tax_amount=tax_t,
            total_amount=tot_t,
            status=po_status,
            approval_step_required=2 if tot_t > Decimal("50000.00") else 1,
            approval_step_completed=2 if po_status in {"RECEIVED", "APPROVED"} else 0,
            created_by_id=users_by_role["PROCUREMENT_OFFICER"].id,
            approved_by_id=users_by_role["FINANCE_MANAGER"].id if po_status in {"RECEIVED", "APPROVED"} else None,
        )
        db.add(po)
        db.flush()
        poi = PurchaseOrderItem(
            id=new_uuid(),
            purchase_order_id=po.id,
            product_id=prod.id,
            ordered_qty=qty,
            received_qty=qty if po_status == "RECEIVED" else Decimal("0.00"),
            unit_price=unit_p,
            tax_rate=Decimal("8.00"),
            line_total=sub_t,
        )
        db.add(poi)
        db.flush()

        if po_status == "PENDING_APPROVAL":
            initiate_approval_request(
                db,
                organization_id=org.id,
                document_type="PURCHASE_ORDER",
                document_id=po.id,
                document_number=po.po_number,
                amount=po.total_amount,
                requested_by_id=users_by_role["PROCUREMENT_OFFICER"].id,
            )
        elif po_status == "RECEIVED":
            grn = GoodsReceipt(
                id=new_uuid(),
                organization_id=org.id,
                grn_number=f"GRN-2026-{401 + po_i:03d}",
                purchase_order_id=po.id,
                supplier_id=sup.id,
                warehouse_id=warehouses[0].id,
                received_date=today - timedelta(days=15 - po_i * 2),
                received_by_id=users_by_role["INVENTORY_MANAGER"].id,
                supplier_invoice_no=f"SINV-{8800 + po_i}",
                total_received_value=tot_t,
                status="POSTED",
            )
            db.add(grn)
            db.flush()
            db.add(
                GoodsReceiptItem(
                    id=new_uuid(),
                    goods_receipt_id=grn.id,
                    purchase_order_item_id=poi.id,
                    product_id=prod.id,
                    received_qty=qty,
                    rejected_qty=Decimal("0.00"),
                    unit_cost=unit_p,
                    line_total=sub_t,
                )
            )

    # ------------------------------------------------------------------------
    # 10. HISTORICAL SALES ORDERS, INVOICES, PAYMENTS & STOCK ISSUES (6 MONTHS)
    # ------------------------------------------------------------------------
    for inv_i in range(24):
        cust = customers[inv_i % len(customers)]
        prod = products[8 + (inv_i % 30)]  # Pick products with ample stock
        wh = warehouses[(8 + (inv_i % 30)) % len(warehouses)]
        days_ago = max(1, 165 - inv_i * 7)
        iss_date = today - timedelta(days=days_ago)
        due_date = iss_date + timedelta(days=30)

        qty = Decimal(str(2 + (inv_i % 4)))
        unit_p = prod.selling_price
        sub_t = quantize_money(qty * unit_p)
        disc_t = Decimal("0.00")
        tax_t = quantize_money(sub_t * Decimal("0.08"))
        tot_t = quantize_money(sub_t + tax_t)

        # Record outbound stock movement so ML demand forecaster has realistic 90-day time series
        mov = record_stock_movement(
            db,
            organization_id=org.id,
            product_id=prod.id,
            warehouse_id=wh.id,
            movement_type="ISSUE",
            quantity=qty,
            unit_cost=prod.weighted_avg_cost,
            reference_type="SALES_INVOICE",
            reference_id=None,
            reference_number=f"INV-2026-{1001 + inv_i:04d}",
            performed_by_id=users_by_role["SALES_MANAGER"].id,
            notes=f"Fulfillment for {cust.name}",
        )
        mov.created_at = datetime.combine(iss_date, datetime.min.time(), tzinfo=timezone.utc)

        so = SalesOrder(
            id=new_uuid(),
            organization_id=org.id,
            so_number=f"SO-2026-{501 + inv_i:04d}",
            customer_id=cust.id,
            warehouse_id=wh.id,
            order_date=iss_date,
            status="INVOICED",
            subtotal=sub_t,
            discount_amount=disc_t,
            tax_amount=tax_t,
            total_amount=tot_t,
            created_by_id=users_by_role["SALES_MANAGER"].id,
        )
        db.add(so)
        db.flush()
        db.add(
            SalesOrderItem(
                id=new_uuid(),
                sales_order_id=so.id,
                product_id=prod.id,
                quantity=qty,
                unit_price=unit_p,
                discount_amount=disc_t,
                tax_amount=tax_t,
                line_total=tot_t,
            )
        )

        # Post Sales & COGS Journal Entry
        cogs_val = quantize_money(qty * prod.weighted_avg_cost)
        je = create_journal_entry(
            db,
            organization_id=org.id,
            entry_date=iss_date,
            reference_type="SALES_INVOICE",
            reference_id=so.id,
            reference_number=f"INV-2026-{1001 + inv_i:04d}",
            description=f"Sales Invoice INV-2026-{1001 + inv_i:04d} — {cust.name}",
            lines=[
                {"account_code": "1100", "debit": tot_t, "credit": Decimal("0.00"), "department_id": depts[5].id},
                {"account_code": "4000", "debit": Decimal("0.00"), "credit": sub_t, "department_id": depts[5].id},
                {"account_code": "2100", "debit": Decimal("0.00"), "credit": tax_t, "department_id": depts[5].id},
                {"account_code": "5000", "debit": cogs_val, "credit": Decimal("0.00"), "department_id": depts[3].id},
                {"account_code": "1200", "debit": Decimal("0.00"), "credit": cogs_val, "department_id": depts[3].id},
            ],
            created_by_id=users_by_role["FINANCE_MANAGER"].id,
            auto_post=True,
        )

        is_paid = inv_i < 17
        is_partial = inv_i in {17, 18, 19}
        paid_amt = tot_t if is_paid else (quantize_money(tot_t * Decimal("0.50")) if is_partial else Decimal("0.00"))
        bal_due = quantize_money(tot_t - paid_amt)
        inv_status = "PAID" if is_paid else ("PARTIALLY_PAID" if is_partial else ("OVERDUE" if due_date < today else "ISSUED"))

        inv = Invoice(
            id=new_uuid(),
            organization_id=org.id,
            invoice_number=f"INV-2026-{1001 + inv_i:04d}",
            invoice_type="CUSTOMER_INVOICE",
            customer_id=cust.id,
            sales_order_id=so.id,
            warehouse_id=wh.id,
            issue_date=iss_date,
            due_date=due_date,
            subtotal=sub_t,
            discount_amount=disc_t,
            tax_amount=tax_t,
            total_amount=tot_t,
            amount_paid=paid_amt,
            balance_due=bal_due,
            status=inv_status,
            journal_entry_id=je.id,
            created_by_id=users_by_role["SALES_MANAGER"].id,
        )
        db.add(inv)
        db.flush()
        db.add(
            InvoiceItem(
                id=new_uuid(),
                invoice_id=inv.id,
                product_id=prod.id,
                description=prod.name,
                quantity=qty,
                unit_price=unit_p,
                discount_amount=disc_t,
                tax_amount=tax_t,
                line_total=tot_t,
            )
        )

        cust.outstanding_balance = quantize_money(cust.outstanding_balance + bal_due)

        if paid_amt > Decimal("0.00"):
            pay_je = create_journal_entry(
                db,
                organization_id=org.id,
                entry_date=iss_date + timedelta(days=5),
                reference_type="CUSTOMER_PAYMENT",
                reference_id=inv.id,
                reference_number=f"PAY-2026-{2001 + inv_i:04d}",
                description=f"Customer Receipt against {inv.invoice_number} — {cust.name}",
                lines=[
                    {"account_code": "1000", "debit": paid_amt, "credit": Decimal("0.00")},
                    {"account_code": "1100", "debit": Decimal("0.00"), "credit": paid_amt},
                ],
                created_by_id=users_by_role["FINANCE_MANAGER"].id,
                auto_post=True,
            )
            db.add(
                Payment(
                    id=new_uuid(),
                    organization_id=org.id,
                    payment_number=f"PAY-2026-{2001 + inv_i:04d}",
                    payment_type="CUSTOMER_RECEIPT",
                    invoice_id=inv.id,
                    customer_id=cust.id,
                    bank_account_id=bank_acc.id,
                    payment_date=iss_date + timedelta(days=5),
                    amount=paid_amt,
                    payment_method="BANK_TRANSFER",
                    reference_no=f"SLIPS-{99001 + inv_i}",
                    journal_entry_id=pay_je.id,
                    recorded_by_id=users_by_role["FINANCE_MANAGER"].id,
                )
            )

    # Sample Sales Quotations
    for q_i in range(4):
        db.add(
            SalesQuotation(
                id=new_uuid(),
                organization_id=org.id,
                quotation_number=f"SQ-2026-{701 + q_i:03d}",
                customer_id=customers[q_i].id,
                valid_until=today + timedelta(days=21),
                subtotal=Decimal("840000.00"),
                discount_amount=Decimal("20000.00"),
                tax_amount=Decimal("65600.00"),
                total_amount=Decimal("885600.00"),
                status="SENT" if q_i % 2 == 0 else "ACCEPTED",
                created_by_id=users_by_role["SALES_MANAGER"].id,
            )
        )

    # ------------------------------------------------------------------------
    # 11. OPERATING EXPENSES (Including 1 Statistical Outlier for Anomaly Engine)
    # ------------------------------------------------------------------------
    expenses_spec = [
        ("EXP-2026-001", "6000", "Payroll & Benefits", "Executive & Engineering Monthly Payroll", "2850000.00", 40, depts[2].id),
        ("EXP-2026-002", "6100", "Facilities & Power", "Ceylon Electricity Board — Cold-Chain & WTC HQ", "640000.00", 32, depts[3].id),
        ("EXP-2026-003", "6200", "Cloud & AI Compute", "Enterprise Cloud Cluster & GPU Telemetry", "480000.00", 25, depts[6].id),
        ("EXP-2026-004", "6300", "Logistics & Fleet", "Peliyagoda Inter-Branch Container Haulage", "520000.00", 18, depts[3].id),
        ("EXP-2026-005", "6100", "Facilities & Power", "World Trade Center Tower Lease & Maintenance", "750000.00", 12, depts[0].id),
        # Statistical anomaly spike (> 2.5 sigma) for Anomaly Detection demonstration:
        ("EXP-2026-006", "6300", "Emergency Air-Freight Charter", "Unscheduled Urgent Air-Freight Charter Clearing", "6950000.00", 4, depts[4].id),
    ]
    for exp_no, acc_code, cat_name, vendor, amt_str, d_ago, dept_id in expenses_spec:
        amt = Decimal(amt_str)
        exp_date = today - timedelta(days=d_ago)
        exp_je = create_journal_entry(
            db,
            organization_id=org.id,
            entry_date=exp_date,
            reference_type="OPERATING_EXPENSE",
            reference_id=None,
            reference_number=exp_no,
            description=f"{cat_name} — {vendor}",
            lines=[
                {"account_code": acc_code, "debit": amt, "credit": Decimal("0.00"), "department_id": dept_id},
                {"account_code": "1000", "debit": Decimal("0.00"), "credit": amt, "department_id": dept_id},
            ],
            created_by_id=users_by_role["FINANCE_MANAGER"].id,
            auto_post=True,
        )
        db.add(
            Expense(
                id=new_uuid(),
                organization_id=org.id,
                expense_number=exp_no,
                department_id=dept_id,
                branch_id=branches[0].id,
                expense_account_id=accounts_by_code[acc_code].id,
                submitted_by_id=users_by_role["FINANCE_MANAGER"].id,
                category=cat_name,
                vendor_name=vendor,
                expense_date=exp_date,
                amount=amt,
                tax_amount=Decimal("0.00"),
                total_amount=amt,
                status="PAID",
                approved_by_id=users_by_role["CEO_DIRECTOR"].id,
                journal_entry_id=exp_je.id,
                description=f"Posted operating expense: {vendor}",
            )
        )

    # ------------------------------------------------------------------------
    # 12. PROJECTS, MILESTONES & KANBAN TASKS
    # ------------------------------------------------------------------------
    projects_spec = [
        ("PRJ-2026-01", "Peliyagoda Automated RFID Warehouse Modernization", "12500000.00", "8200000.00", 72, "IN_PROGRESS", "CRITICAL", 45),
        ("PRJ-2026-02", "Islandwide B2B Dealer Portal & FinTech Integration", "8400000.00", "4100000.00", 54, "IN_PROGRESS", "HIGH", 30),
        ("PRJ-2026-03", "Kandy & Galle Cold-Chain Solar Microgrid Rollout", "15000000.00", "13400000.00", 48, "IN_PROGRESS", "HIGH", 12),
        ("PRJ-2026-04", "ISO 27001 & Automated Double-Entry Audit Certification", "4500000.00", "4350000.00", 95, "IN_PROGRESS", "MEDIUM", 20),
    ]
    projects: list[Project] = []
    for p_code, p_name, bud, spent, prog, st, prio, days_left in projects_spec:
        prj = Project(
            id=new_uuid(),
            organization_id=org.id,
            project_code=p_code,
            name=p_name,
            description=f"Strategic enterprise initiative: {p_name}",
            department_id=depts[6].id,
            manager_employee_id=employees[8].id,
            start_date=today - timedelta(days=75),
            end_date=today + timedelta(days=days_left),
            budget=Decimal(bud),
            spent_amount=Decimal(spent),
            progress_percent=prog,
            status=st,
            priority=prio,
        )
        db.add(prj)
        projects.append(prj)
        db.flush()
        db.add(
            ProjectMember(
                id=new_uuid(),
                project_id=prj.id,
                employee_id=employees[8].id,
                role_in_project="Lead Project Manager",
                allocation_percent=100,
            )
        )
        ms = Milestone(
            id=new_uuid(),
            project_id=prj.id,
            title=f"{p_code} Phase 2 Production Cutover",
            due_date=today + timedelta(days=days_left // 2),
            status="PENDING",
        )
        db.add(ms)
        db.flush()

    kanban_tasks_spec = [
        ("TSK-101", projects[0].id, "Calibrate RFID Gate Readers at Bay 1-4", "DONE", "HIGH", 16, 16),
        ("TSK-102", projects[0].id, "Integrate Real-Time Weighted Average Cost Webhook", "IN_PROGRESS", "URGENT", 24, 18),
        ("TSK-103", projects[0].id, "Conduct Warehouse Staff UAT Drills", "TODO", "MEDIUM", 12, 0),
        ("TSK-104", projects[1].id, "Implement LKR Multi-Tier Credit Limit Validator", "REVIEW", "HIGH", 20, 19),
        ("TSK-105", projects[1].id, "Configure Automated PDF Tax Invoice Dispatch", "IN_PROGRESS", "HIGH", 16, 10),
        ("TSK-106", projects[2].id, "Commission 50kW Hybrid Inverter Bank in Kandy", "TODO", "URGENT", 32, 8),
        ("TSK-107", projects[2].id, "Inspect Battery Thermal Telemetry Sensors", "BACKLOG", "MEDIUM", 14, 0),
        ("TSK-108", projects[3].id, "Verify Argon2id & RBAC Separation-of-Duties Matrix", "DONE", "HIGH", 10, 10),
    ]
    for idx, (t_code, prj_id, title, st, prio, est_h, log_h) in enumerate(kanban_tasks_spec):
        db.add(
            Task(
                id=new_uuid(),
                organization_id=org.id,
                project_id=prj_id,
                task_code=t_code,
                title=title,
                description=f"Deliverable specification for {title}",
                assignee_employee_id=employees[idx % 12].id,
                status=st,
                priority=prio,
                start_date=today - timedelta(days=14),
                due_date=today + timedelta(days=7 + idx * 3),
                estimated_hours=Decimal(str(est_h)),
                logged_hours=Decimal(str(log_h)),
            )
        )

    # ------------------------------------------------------------------------
    # 13. AI INSIGHTS, NOTIFICATIONS & AUDIT LOGS
    # ------------------------------------------------------------------------
    insights_spec = [
        (
            "INVENTORY_OPTIMIZATION",
            "8 High-Velocity SKUs Require Immediate Replenishment",
            "Demand forecasting (XGBoost GBR) projects stockout within 7 days for 8 core server and networking SKUs in Peliyagoda.",
            "Prevent LKR 4.2M in lost order fulfillment",
            ["Stock Balances WH-PEL-01", "Demand Forecast Run v2"],
        ),
        (
            "PROCUREMENT_VARIANCE",
            "PO-2026-307 Unit Cost Exceeds Historical WAC by +32%",
            "Anomaly engine flagged an unscheduled spot purchase price variance; consolidating with Lanka Industrial Tech saves 18%.",
            "Estimated LKR 680,000 quarterly procurement savings",
            ["Purchase Order PO-2026-307", "Supplier Quotation RFQ-SUP-007"],
        ),
        (
            "WORKING_CAPITAL",
            "LKR 3.8M in Receivables Approaching 30-Day Credit Window",
            "Automated reminders for 4 corporate accounts can accelerate cash conversion cycle by 6.5 days.",
            "Improve operating cash liquidity by +11%",
            ["Accounts Receivable Ledger 1100", "Customer Aging Schedule"],
        ),
    ]
    for cat, title, summary, impact, refs in insights_spec:
        db.add(
            AIInsight(
                id=new_uuid(),
                organization_id=org.id,
                category=cat,
                title=title,
                summary=summary,
                impact_estimate=impact,
                confidence_score=Decimal("0.92"),
                source_references=refs,
            )
        )

    db.add(
        Notification(
            id=new_uuid(),
            organization_id=org.id,
            user_id=None,
            title="Nexora Intelligence: Daily Forecast & Anomaly Scan Complete",
            message="50 products forecasted across 3 warehouses; 3 high-priority operational anomalies flagged for human review.",
            category="AI_ALERT",
            severity="INFO",
            action_url="/ai/insights",
        )
    )

    db.add(
        AuditLog(
            id=new_uuid(),
            organization_id=org.id,
            actor_user_id=users_by_role["SUPER_ADMIN"].id,
            actor_email=users_by_role["SUPER_ADMIN"].email,
            action="ORGANIZATION_SEED_INITIALIZED",
            entity_type="Organization",
            entity_id=org.id,
            after_state={"organization": org.name, "currency": "LKR", "timezone": "Asia/Colombo"},
            ip_address="127.0.0.1",
            correlation_id="seed-init-001",
        )
    )

    db.commit()

    # Run initial ML Forecast & Anomaly Detection so tables are populated immediately
    run_inventory_demand_forecast(db, organization_id=org.id, model_choice="XGBOOST")
    run_business_anomaly_detection(db, organization_id=org.id)

    return {
        "status": "seeded",
        "organization_id": org.id,
        "secondary_organization_id": secondary_org.id,
        "employees": len(employees),
        "products": len(products),
        "customers": len(customers),
        "suppliers": len(suppliers),
    }
