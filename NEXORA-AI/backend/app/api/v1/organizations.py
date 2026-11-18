"""NEXORA ERP — Multi-Tenant Organizations, Branches, Departments, Users, Roles & Audit Logs Router."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    AuthContext,
    get_user_roles_and_permissions,
    record_audit_log,
    require_permissions,
)
from app.core.database import get_db
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.models.entities import (
    AuditLog,
    Branch,
    Department,
    Organization,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
    new_uuid,
)

router = APIRouter(tags=["Organization & Administration"])


class OrganizationUpdateSchema(BaseModel):
    name: str
    registration_number: Optional[str] = None
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    default_currency: str = "LKR"
    timezone: str = "Asia/Colombo"
    fiscal_year_start_month: int = 4
    date_format: str = "DD MMM YYYY"


class OrganizationCreateSchema(OrganizationUpdateSchema):
    code: str


class BranchCreateSchema(BaseModel):
    name: str
    code: str
    city: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    manager_name: Optional[str] = None
    is_headquarters: bool = False


class DepartmentCreateSchema(BaseModel):
    name: str
    code: str
    branch_id: Optional[str] = None
    budget_allocated: float = 0.0


class UserCreateSchema(BaseModel):
    email: EmailStr
    full_name: str
    password: str = "Nexora#2026"
    role_codes: list[str]
    branch_id: Optional[str] = None
    department_id: Optional[str] = None


class RoleCreateSchema(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    permission_codes: list[str]


@router.get("/organizations")
def list_organizations(
    ctx: AuthContext = Depends(require_permissions("organizations.view")),
    db: Session = Depends(get_db),
) -> dict:
    if ctx.user.is_super_admin or "SUPER_ADMIN" in ctx.roles:
        orgs = list(db.execute(select(Organization).order_by(Organization.name)).scalars())
    else:
        orgs = [ctx.organization]

    return {
        "items": [
            {
                "id": o.id,
                "name": o.name,
                "code": o.code,
                "registration_number": o.registration_number,
                "tax_id": o.tax_id,
                "email": o.email,
                "phone": o.phone,
                "address": o.address,
                "default_currency": o.default_currency,
                "timezone": o.timezone,
                "fiscal_year_start_month": o.fiscal_year_start_month,
                "date_format": o.date_format,
                "is_demo": o.is_demo,
                "is_active": o.is_active,
            }
            for o in orgs
        ]
    }


@router.get("/organizations/{org_id}")
def get_organization(
    org_id: str,
    ctx: AuthContext = Depends(require_permissions("organizations.view")),
    db: Session = Depends(get_db),
) -> dict:
    if org_id != ctx.organization.id and not (ctx.user.is_super_admin or "SUPER_ADMIN" in ctx.roles):
        raise ForbiddenError("Cross-organization access denied.", code="TENANT_ISOLATION_VIOLATION")

    org = db.execute(select(Organization).where(Organization.id == org_id)).scalar_one_or_none()
    if not org:
        raise NotFoundError("Organization not found.")

    branches = list(db.execute(select(Branch).where(Branch.organization_id == org.id)).scalars())
    depts = list(db.execute(select(Department).where(Department.organization_id == org.id)).scalars())

    return {
        "id": org.id,
        "name": org.name,
        "code": org.code,
        "registration_number": org.registration_number,
        "tax_id": org.tax_id,
        "email": org.email,
        "phone": org.phone,
        "address": org.address,
        "default_currency": org.default_currency,
        "timezone": org.timezone,
        "fiscal_year_start_month": org.fiscal_year_start_month,
        "date_format": org.date_format,
        "is_demo": org.is_demo,
        "branches": [
            {
                "id": b.id,
                "name": b.name,
                "code": b.code,
                "city": b.city,
                "address": b.address,
                "phone": b.phone,
                "manager_name": b.manager_name,
                "is_headquarters": b.is_headquarters,
            }
            for b in branches
        ],
        "departments": [
            {
                "id": d.id,
                "name": d.name,
                "code": d.code,
                "branch_id": d.branch_id,
                "budget_allocated": float(d.budget_allocated),
            }
            for d in depts
        ],
    }


@router.put("/organizations/{org_id}")
def update_organization(
    org_id: str,
    payload: OrganizationUpdateSchema,
    ctx: AuthContext = Depends(require_permissions("organizations.manage")),
    db: Session = Depends(get_db),
) -> dict:
    if org_id != ctx.organization.id and not ctx.user.is_super_admin:
        raise ForbiddenError("Cannot modify another tenant organization.")

    org = db.execute(select(Organization).where(Organization.id == org_id)).scalar_one_or_none()
    if not org:
        raise NotFoundError("Organization not found.")

    org.name = payload.name
    org.registration_number = payload.registration_number
    org.tax_id = payload.tax_id
    org.email = payload.email
    org.phone = payload.phone
    org.address = payload.address
    org.default_currency = payload.default_currency
    org.timezone = payload.timezone
    org.fiscal_year_start_month = payload.fiscal_year_start_month
    org.date_format = payload.date_format

    record_audit_log(
        db,
        ctx=ctx,
        action="ORGANIZATION_UPDATED",
        entity_type="Organization",
        entity_id=org.id,
        after_state=payload.model_dump(),
    )
    db.commit()
    return get_organization(org.id, ctx, db)


@router.get("/branches")
def list_branches(
    ctx: AuthContext = Depends(require_permissions("organizations.view")),
    db: Session = Depends(get_db),
) -> dict:
    branches = list(
        db.execute(
            select(Branch)
            .where(Branch.organization_id == ctx.organization.id)
            .order_by(Branch.is_headquarters.desc(), Branch.name)
        ).scalars()
    )
    return {
        "items": [
            {
                "id": b.id,
                "name": b.name,
                "code": b.code,
                "city": b.city,
                "address": b.address,
                "phone": b.phone,
                "manager_name": b.manager_name,
                "is_headquarters": b.is_headquarters,
                "is_active": b.is_active,
            }
            for b in branches
        ]
    }


@router.post("/branches")
def create_branch(
    payload: BranchCreateSchema,
    ctx: AuthContext = Depends(require_permissions("organizations.manage")),
    db: Session = Depends(get_db),
) -> dict:
    b = Branch(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        name=payload.name,
        code=payload.code.upper(),
        city=payload.city,
        address=payload.address,
        phone=payload.phone,
        manager_name=payload.manager_name,
        is_headquarters=payload.is_headquarters,
    )
    db.add(b)
    record_audit_log(db, ctx=ctx, action="BRANCH_CREATED", entity_type="Branch", entity_id=b.id)
    db.commit()
    return {"id": b.id, "name": b.name, "code": b.code, "city": b.city}


@router.get("/departments")
def list_departments(
    ctx: AuthContext = Depends(require_permissions("organizations.view")),
    db: Session = Depends(get_db),
) -> dict:
    depts = list(
        db.execute(
            select(Department)
            .where(Department.organization_id == ctx.organization.id)
            .order_by(Department.code)
        ).scalars()
    )
    return {
        "items": [
            {
                "id": d.id,
                "name": d.name,
                "code": d.code,
                "branch_id": d.branch_id,
                "budget_allocated": float(d.budget_allocated),
                "is_active": d.is_active,
            }
            for d in depts
        ]
    }


@router.post("/departments")
def create_department(
    payload: DepartmentCreateSchema,
    ctx: AuthContext = Depends(require_permissions("organizations.manage")),
    db: Session = Depends(get_db),
) -> dict:
    d = Department(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        branch_id=payload.branch_id,
        name=payload.name,
        code=payload.code.upper(),
        budget_allocated=Decimal(str(payload.budget_allocated)),
    )
    db.add(d)
    record_audit_log(db, ctx=ctx, action="DEPARTMENT_CREATED", entity_type="Department", entity_id=d.id)
    db.commit()
    return {"id": d.id, "name": d.name, "code": d.code, "budget_allocated": float(d.budget_allocated)}


@router.get("/users")
def list_users(
    ctx: AuthContext = Depends(require_permissions("users.view")),
    db: Session = Depends(get_db),
) -> dict:
    users = list(
        db.execute(
            select(User)
            .where(User.organization_id == ctx.organization.id)
            .order_by(User.created_at)
        ).scalars()
    )
    items = []
    for u in users:
        r_codes, p_codes = get_user_roles_and_permissions(db, u)
        items.append(
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "roles": r_codes,
                "permissions_count": len(p_codes),
                "mfa_enabled": u.mfa_enabled,
                "is_active": u.is_active,
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            }
        )
    return {"items": items}


@router.post("/users")
def create_user(
    payload: UserCreateSchema,
    ctx: AuthContext = Depends(require_permissions("users.manage")),
    db: Session = Depends(get_db),
) -> dict:
    existing = db.execute(select(User).where(User.email == payload.email.lower())).scalar_one_or_none()
    if existing:
        raise ConflictError(f"User with email '{payload.email}' already exists.")

    u = User(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        branch_id=payload.branch_id,
        department_id=payload.department_id,
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(u)
    db.flush()

    for rc in payload.role_codes:
        role = db.execute(select(Role).where(Role.code == rc)).scalar_one_or_none()
        if role:
            db.add(UserRole(id=new_uuid(), user_id=u.id, role_id=role.id))

    record_audit_log(
        db,
        ctx=ctx,
        action="USER_CREATED",
        entity_type="User",
        entity_id=u.id,
        after_state={"email": u.email, "roles": payload.role_codes},
    )
    db.commit()
    return {"id": u.id, "email": u.email, "full_name": u.full_name, "roles": payload.role_codes}


@router.get("/roles")
def list_roles(
    ctx: AuthContext = Depends(require_permissions("users.view")),
    db: Session = Depends(get_db),
) -> dict:
    roles = list(db.execute(select(Role).order_by(Role.name)).scalars())
    items = []
    for r in roles:
        p_codes = list(
            db.execute(
                select(Permission.code)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .where(RolePermission.role_id == r.id)
            ).scalars()
        )
        items.append(
            {
                "id": r.id,
                "code": r.code,
                "name": r.name,
                "description": r.description,
                "is_system": r.is_system,
                "permissions": sorted(p_codes),
            }
        )
    return {"items": items}


@router.post("/roles")
def create_role(
    payload: RoleCreateSchema,
    ctx: AuthContext = Depends(require_permissions("users.manage")),
    db: Session = Depends(get_db),
) -> dict:
    r = Role(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        code=payload.code.upper(),
        name=payload.name,
        description=payload.description,
        is_system=False,
    )
    db.add(r)
    db.flush()
    for pc in payload.permission_codes:
        perm = db.execute(select(Permission).where(Permission.code == pc)).scalar_one_or_none()
        if perm:
            db.add(RolePermission(id=new_uuid(), role_id=r.id, permission_id=perm.id))
    record_audit_log(db, ctx=ctx, action="ROLE_CREATED", entity_type="Role", entity_id=r.id)
    db.commit()
    return {"id": r.id, "code": r.code, "name": r.name, "permissions": payload.permission_codes}


@router.get("/permissions")
def list_permissions(
    ctx: AuthContext = Depends(require_permissions("users.view")),
    db: Session = Depends(get_db),
) -> dict:
    perms = list(db.execute(select(Permission).order_by(Permission.module, Permission.code)).scalars())
    return {
        "items": [
            {"id": p.id, "code": p.code, "module": p.module, "description": p.description}
            for p in perms
        ]
    }


@router.get("/audit-logs")
def list_audit_logs(
    ctx: AuthContext = Depends(require_permissions("audit_logs.view")),
    db: Session = Depends(get_db),
) -> dict:
    logs = list(
        db.execute(
            select(AuditLog)
            .where(AuditLog.organization_id == ctx.organization.id)
            .order_by(AuditLog.created_at.desc())
            .limit(100)
        ).scalars()
    )
    return {
        "items": [
            {
                "id": l.id,
                "actor_email": l.actor_email,
                "action": l.action,
                "entity_type": l.entity_type,
                "entity_id": l.entity_id,
                "after_state": l.after_state,
                "ip_address": l.ip_address,
                "correlation_id": l.correlation_id,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ]
    }
