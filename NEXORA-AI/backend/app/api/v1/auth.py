"""NEXORA ERP — Authentication & Session Management API Router (/api/v1/auth)."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Request, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    AuthContext,
    get_current_context,
    get_user_roles_and_permissions,
    record_audit_log,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import BusinessRuleError, ForbiddenError, UnauthorizedError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    generate_totp_secret,
    get_totp_code,
    hash_password,
    hash_refresh_token,
    verify_password,
    verify_totp_code,
)
from app.models.entities import (
    Branch,
    Department,
    LoginAttempt,
    Organization,
    RefreshToken,
    User,
    new_uuid,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    reset_token: str
    new_password: str


class MFAVerifyRequest(BaseModel):
    code: str


class ThemeUpdateRequest(BaseModel):
    theme: str


def _serialize_user_session(db: Session, user: User) -> dict:
    roles, perms = get_user_roles_and_permissions(db, user)
    org = db.execute(select(Organization).where(Organization.id == user.organization_id)).scalar_one()
    branches = list(
        db.execute(
            select(Branch).where(Branch.organization_id == org.id, Branch.is_active.is_(True))
        ).scalars()
    )
    depts = list(
        db.execute(
            select(Department).where(Department.organization_id == org.id, Department.is_active.is_(True))
        ).scalars()
    )
    if user.is_super_admin or "SUPER_ADMIN" in roles:
        accessible_orgs = list(
            db.execute(select(Organization).where(Organization.is_active.is_(True))).scalars()
        )
    else:
        accessible_orgs = [org]

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "organization_id": org.id,
        "organization_name": org.name,
        "currency": org.default_currency,
        "timezone": org.timezone,
        "date_format": org.date_format,
        "branch_id": user.branch_id,
        "department_id": user.department_id,
        "mfa_enabled": user.mfa_enabled,
        "is_super_admin": user.is_super_admin,
        "theme_preference": user.theme_preference,
        "roles": roles,
        "permissions": sorted(list(perms)),
        "organizations": [
            {
                "id": o.id,
                "name": o.name,
                "code": o.code,
                "currency": o.default_currency,
                "timezone": o.timezone,
                "is_demo": o.is_demo,
            }
            for o in accessible_orgs
        ],
        "branches": [{"id": b.id, "name": b.name, "code": b.code, "city": b.city} for b in branches],
        "departments": [{"id": d.id, "name": d.name, "code": d.code} for d in depts],
    }


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    ip_addr = request.client.host if request.client else "127.0.0.1"
    ua = request.headers.get("user-agent", "Nexora-Client")[:250]
    email_norm = payload.email.strip().lower()

    user = db.execute(select(User).where(User.email == email_norm)).scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if user and user.locked_until:
        locked_until = (
            user.locked_until
            if user.locked_until.tzinfo
            else user.locked_until.replace(tzinfo=timezone.utc)
        )
        if locked_until > now:
            db.add(
                LoginAttempt(
                    id=new_uuid(),
                    email=email_norm,
                    user_id=user.id,
                    ip_address=ip_addr,
                    user_agent=ua,
                    succeeded=False,
                    failure_reason="ACCOUNT_LOCKED",
                )
            )
            db.commit()
            raise ForbiddenError(
                f"Account is temporarily locked due to repeated failed login attempts. Try again after {locked_until.strftime('%H:%M UTC')}.",
                code="ACCOUNT_LOCKED",
            )

    if not user or not verify_password(payload.password, user.password_hash):
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= settings.max_failed_login_attempts:
                user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
        db.add(
            LoginAttempt(
                id=new_uuid(),
                email=email_norm,
                user_id=user.id if user else None,
                ip_address=ip_addr,
                user_agent=ua,
                succeeded=False,
                failure_reason="INVALID_CREDENTIALS",
            )
        )
        db.commit()
        raise UnauthorizedError("Invalid email or password.", code="INVALID_CREDENTIALS")

    if not user.is_active:
        raise ForbiddenError("User account has been deactivated.", code="ACCOUNT_INACTIVE")

    if user.mfa_enabled and user.mfa_secret:
        if not payload.totp_code:
            return {
                "mfa_required": True,
                "email": user.email,
                "message": "Please enter your 6-digit authenticator TOTP verification code.",
            }
        if not verify_totp_code(user.mfa_secret, payload.totp_code):
            raise UnauthorizedError("Invalid MFA verification code.", code="INVALID_MFA_CODE")

    # Reset lockout counters on successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now

    roles, perms = get_user_roles_and_permissions(db, user)
    access_token = create_access_token(
        subject=user.id,
        organization_id=user.organization_id,
        roles=roles,
        permissions=sorted(list(perms)),
    )

    raw_refresh, refresh_hash = generate_refresh_token()
    family_id = secrets.token_hex(16)
    db.add(
        RefreshToken(
            id=new_uuid(),
            user_id=user.id,
            token_hash=refresh_hash,
            family_id=family_id,
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
            ip_address=ip_addr,
            user_agent=ua,
        )
    )
    db.add(
        LoginAttempt(
            id=new_uuid(),
            email=email_norm,
            user_id=user.id,
            ip_address=ip_addr,
            user_agent=ua,
            succeeded=True,
        )
    )
    db.commit()

    response.set_cookie(
        key="nexora_refresh_token",
        value=raw_refresh,
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/api/v1/auth",
    )

    return {
        "mfa_required": False,
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": _serialize_user_session(db, user),
    }


@router.post("/refresh")
def refresh_token(
    request: Request,
    response: Response,
    nexora_refresh_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
) -> dict:
    if not nexora_refresh_token:
        raise UnauthorizedError("No refresh token cookie present.", code="MISSING_REFRESH_TOKEN")

    token_hash = hash_refresh_token(nexora_refresh_token)
    rt = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).scalar_one_or_none()

    if not rt:
        raise UnauthorizedError("Invalid refresh token.", code="INVALID_REFRESH_TOKEN")

    now = datetime.now(timezone.utc)
    if rt.revoked_at is not None:
        # Token reuse detected! Revoke entire family
        family_tokens = list(
            db.execute(
                select(RefreshToken).where(RefreshToken.family_id == rt.family_id)
            ).scalars()
        )
        for ft in family_tokens:
            ft.revoked_at = now
        db.commit()
        raise UnauthorizedError("Refresh token has already been used and revoked.", code="TOKEN_REUSE_DETECTED")

    expires_at = rt.expires_at if rt.expires_at.tzinfo else rt.expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        raise UnauthorizedError("Refresh token has expired.", code="REFRESH_TOKEN_EXPIRED")

    rt.revoked_at = now
    user = db.execute(select(User).where(User.id == rt.user_id)).scalar_one()
    roles, perms = get_user_roles_and_permissions(db, user)

    new_access = create_access_token(
        subject=user.id,
        organization_id=user.organization_id,
        roles=roles,
        permissions=sorted(list(perms)),
    )
    new_raw_refresh, new_refresh_hash = generate_refresh_token()
    db.add(
        RefreshToken(
            id=new_uuid(),
            user_id=user.id,
            token_hash=new_refresh_hash,
            family_id=rt.family_id,
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
            ip_address=request.client.host if request.client else "127.0.0.1",
            user_agent=request.headers.get("user-agent", "Nexora-Client")[:250],
        )
    )
    db.commit()

    response.set_cookie(
        key="nexora_refresh_token",
        value=new_raw_refresh,
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/api/v1/auth",
    )

    return {
        "access_token": new_access,
        "token_type": "bearer",
        "user": _serialize_user_session(db, user),
    }


@router.post("/logout")
def logout(
    response: Response,
    nexora_refresh_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
) -> dict:
    if nexora_refresh_token:
        token_hash = hash_refresh_token(nexora_refresh_token)
        rt = db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        ).scalar_one_or_none()
        if rt:
            rt.revoked_at = datetime.now(timezone.utc)
            db.commit()
    response.delete_cookie("nexora_refresh_token", path="/api/v1/auth")
    return {"status": "logged_out"}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> dict:
    user = db.execute(
        select(User).where(User.email == payload.email.strip().lower())
    ).scalar_one_or_none()
    reset_token = secrets.token_urlsafe(24)
    return {
        "status": "reset_instructions_dispatched",
        "message": "If an account exists for that email, a password reset link has been generated.",
        "demo_reset_token": reset_token if settings.app_debug and user else None,
    }


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> dict:
    if len(payload.new_password) < 8:
        raise BusinessRuleError("Password must be at least 8 characters long.")
    user = db.execute(
        select(User).where(User.email == payload.email.strip().lower())
    ).scalar_one_or_none()
    if not user:
        raise BusinessRuleError("Unable to reset password for the specified account.")
    user.password_hash = hash_password(payload.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    return {"status": "password_updated", "message": "Password has been securely hashed with Argon2id and updated."}


@router.post("/mfa/setup")
def setup_mfa(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    secret = generate_totp_secret()
    ctx.user.mfa_secret = secret
    db.commit()
    return {
        "secret": secret,
        "otpauth_url": f"otpauth://totp/NEXORA-ERP:{ctx.user.email}?secret={secret}&issuer=NEXORA-ERP",
        "current_demo_code": get_totp_code(secret) if settings.app_debug else None,
    }


@router.post("/mfa/verify")
def verify_mfa(
    payload: MFAVerifyRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    if not ctx.user.mfa_secret or not verify_totp_code(ctx.user.mfa_secret, payload.code):
        raise BusinessRuleError("Invalid 6-digit TOTP verification code.", code="INVALID_MFA_CODE")
    ctx.user.mfa_enabled = True
    record_audit_log(db, ctx=ctx, action="MFA_ENABLED", entity_type="User", entity_id=ctx.user.id)
    db.commit()
    return {"status": "mfa_enabled", "mfa_enabled": True}


@router.get("/me")
def get_me(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    session_data = _serialize_user_session(db, ctx.user)
    session_data["organization_id"] = ctx.organization.id
    session_data["organization_name"] = ctx.organization.name
    session_data["currency"] = ctx.organization.default_currency
    session_data["timezone"] = ctx.organization.timezone
    return session_data


@router.put("/theme")
def update_theme(
    payload: ThemeUpdateRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> dict:
    theme = "light" if payload.theme.lower() == "light" else "dark"
    ctx.user.theme_preference = theme
    db.commit()
    return {"theme_preference": theme}


@router.get("/demo-accounts")
def list_demo_accounts(db: Session = Depends(get_db)) -> dict:
    """List demo accounts across all 12 RBAC roles for portfolio evaluation."""
    users = list(db.execute(select(User).order_by(User.created_at)).scalars())
    items = []
    for u in users:
        roles, _ = get_user_roles_and_permissions(db, u)
        org = db.execute(select(Organization).where(Organization.id == u.organization_id)).scalar_one_or_none()
        items.append(
            {
                "email": u.email,
                "full_name": u.full_name,
                "roles": roles,
                "organization_name": org.name if org else "Nexora",
                "default_password": "Nexora#2026",
            }
        )
    return {"accounts": items}
