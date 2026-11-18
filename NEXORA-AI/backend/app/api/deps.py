"""NEXORA ERP — Authentication, Tenant Context & Granular RBAC Dependencies."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db, set_tenant_rls_context
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.logging import correlation_id_ctx
from app.core.security import decode_access_token
from app.models.entities import (
    AuditLog,
    Organization,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
    new_uuid,
)

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    user: User
    organization: Organization
    roles: list[str]
    permissions: set[str]


def get_user_roles_and_permissions(db: Session, user: User) -> tuple[list[str], set[str]]:
    role_rows = list(
        db.execute(
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id)
        ).scalars()
    )
    role_codes = [r.code for r in role_rows]
    if user.is_super_admin or "SUPER_ADMIN" in role_codes:
        all_perms = list(db.execute(select(Permission.code)).scalars())
        return role_codes, set(all_perms) | {"*"}

    role_ids = [r.id for r in role_rows]
    if not role_ids:
        return [], set()

    perm_codes = list(
        db.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id.in_(role_ids))
        ).scalars()
    )
    return role_codes, set(perm_codes)


def get_current_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_organization_id: str | None = Header(default=None, alias="X-Organization-ID"),
    db: Session = Depends(get_db),
) -> AuthContext:
    if not credentials or not credentials.credentials:
        raise UnauthorizedError("Missing bearer access token.")

    try:
        payload = decode_access_token(credentials.credentials)
    except Exception as exc:
        raise UnauthorizedError(f"Invalid or expired access token: {exc}")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Malformed token payload.")

    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedError("User account is inactive or does not exist.")

    roles, permissions = get_user_roles_and_permissions(db, user)

    target_org_id = x_organization_id or payload.get("org_id") or user.organization_id

    # Enforce strict tenant isolation: non-super-admins can ONLY access their assigned organization
    if target_org_id != user.organization_id and not (user.is_super_admin or "SUPER_ADMIN" in roles):
        raise ForbiddenError(
            "Cross-organization access denied: You do not have membership in the requested tenant.",
            code="TENANT_ISOLATION_VIOLATION",
        )

    org = db.execute(select(Organization).where(Organization.id == target_org_id)).scalar_one_or_none()
    if not org or not org.is_active:
        raise ForbiddenError("Target organization is inactive or does not exist.")

    set_tenant_rls_context(db, org.id)
    return AuthContext(user=user, organization=org, roles=roles, permissions=permissions)


def require_permissions(*required_codes: str) -> Callable[[AuthContext], AuthContext]:
    """Dependency factory enforcing one or more granular RBAC permissions on the server."""

    def _checker(ctx: AuthContext = Depends(get_current_context)) -> AuthContext:
        if "*" in ctx.permissions or ctx.user.is_super_admin:
            return ctx
        missing = [c for c in required_codes if c not in ctx.permissions]
        if missing:
            raise ForbiddenError(
                f"Access denied. Missing required permission(s): {', '.join(missing)}",
                code="INSUFFICIENT_PERMISSIONS",
            )
        return ctx

    return _checker


def require_any_permission(*any_codes: str) -> Callable[[AuthContext], AuthContext]:
    """Dependency factory enforcing at least one of the specified permissions."""

    def _checker(ctx: AuthContext = Depends(get_current_context)) -> AuthContext:
        if "*" in ctx.permissions or ctx.user.is_super_admin:
            return ctx
        if not any(c in ctx.permissions for c in any_codes):
            raise ForbiddenError(
                f"Access denied. Requires at least one of: {', '.join(any_codes)}",
                code="INSUFFICIENT_PERMISSIONS",
            )
        return ctx

    return _checker


def record_audit_log(
    db: Session,
    *,
    ctx: AuthContext,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    before_state: dict | None = None,
    after_state: dict | None = None,
    ip_address: str = "127.0.0.1",
) -> None:
    db.add(
        AuditLog(
            id=new_uuid(),
            organization_id=ctx.organization.id,
            actor_user_id=ctx.user.id,
            actor_email=ctx.user.email,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address,
            correlation_id=correlation_id_ctx.get(),
        )
    )
