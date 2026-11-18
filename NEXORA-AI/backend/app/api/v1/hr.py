"""NEXORA ERP — Human Resource Management API Router (/api/v1/employees, /leave-requests, /hr)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, record_audit_log, require_permissions
from app.core.database import get_db
from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.models.entities import (
    AttendanceRecord,
    Branch,
    Department,
    Designation,
    Employee,
    LeaveBalance,
    LeaveRequest,
    PerformanceReview,
    new_uuid,
)

router = APIRouter(tags=["Human Resources"])


class EmployeeCreateSchema(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    national_id: Optional[str] = None
    branch_id: str
    department_id: str
    designation_id: Optional[str] = None
    employment_type: str = "FULL_TIME"
    employment_status: str = "ACTIVE"
    join_date: Optional[date] = None
    base_salary: float = 165000.0
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class EmployeeUpdateSchema(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    employment_status: Optional[str] = None
    department_id: Optional[str] = None
    base_salary: Optional[float] = None


class AttendanceCreateSchema(BaseModel):
    employee_id: str
    attendance_date: date
    check_in: str = "08:30"
    check_out: str = "17:30"
    status: str = "PRESENT"
    hours_worked: float = 8.5
    notes: Optional[str] = None


class LeaveRequestCreateSchema(BaseModel):
    employee_id: str
    leave_type: str = "ANNUAL"
    start_date: date
    end_date: date
    days_count: float
    reason: str


class LeaveApprovalSchema(BaseModel):
    action: str = "APPROVE"  # APPROVE or REJECT
    rejection_reason: Optional[str] = None


class PerformanceCreateSchema(BaseModel):
    employee_id: str
    review_period: str = "FY 2026"
    kpi_score: float = 4.4
    competency_score: float = 4.3
    overall_rating: str = "EXCEEDS"
    strengths: Optional[str] = None
    improvements: Optional[str] = None


def _can_view_confidential_hr(ctx: AuthContext) -> bool:
    return (
        "*" in ctx.permissions
        or "hr.confidential.view" in ctx.permissions
        or "HR_MANAGER" in ctx.roles
        or "ORG_ADMIN" in ctx.roles
        or "SUPER_ADMIN" in ctx.roles
    )


@router.get("/employees")
def list_employees(
    search: Optional[str] = Query(default=None),
    department_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    ctx: AuthContext = Depends(require_permissions("employees.view")),
    db: Session = Depends(get_db),
) -> dict:
    stmt = (
        select(Employee, Department.name, Branch.name, Designation.title)
        .join(Department, Department.id == Employee.department_id)
        .join(Branch, Branch.id == Employee.branch_id)
        .join(Designation, Designation.id == Employee.designation_id)
        .where(Employee.organization_id == ctx.organization.id)
        .order_by(Employee.employee_code)
    )
    if department_id:
        stmt = stmt.where(Employee.department_id == department_id)
    if status:
        stmt = stmt.where(Employee.employment_status == status)

    rows = db.execute(stmt).all()
    show_confidential = _can_view_confidential_hr(ctx)

    items = []
    for emp, dept_name, branch_name, desig_title in rows:
        full_name = f"{emp.first_name} {emp.last_name}"
        if search and search.lower() not in full_name.lower() and search.lower() not in emp.employee_code.lower():
            continue
        items.append(
            {
                "id": emp.id,
                "employee_code": emp.employee_code,
                "first_name": emp.first_name,
                "last_name": emp.last_name,
                "full_name": full_name,
                "email": emp.email,
                "phone": emp.phone,
                "national_id": emp.national_id if show_confidential else "REDACTED",
                "branch_id": emp.branch_id,
                "branch_name": branch_name,
                "department_id": emp.department_id,
                "department_name": dept_name,
                "designation_id": emp.designation_id,
                "designation_title": desig_title,
                "employment_type": emp.employment_type,
                "employment_status": emp.employment_status,
                "join_date": emp.join_date.isoformat(),
                "base_salary": float(emp.base_salary) if show_confidential else None,
                "confidential_visible": show_confidential,
                "emergency_contact_name": emp.emergency_contact_name,
                "emergency_contact_phone": emp.emergency_contact_phone,
            }
        )

    return {
        "items": items,
        "total": len(items),
        "confidential_visible": show_confidential,
    }


@router.get("/employees/{employee_id}")
def get_employee(
    employee_id: str,
    ctx: AuthContext = Depends(require_permissions("employees.view")),
    db: Session = Depends(get_db),
) -> dict:
    row = db.execute(
        select(Employee, Department.name, Branch.name, Designation.title)
        .join(Department, Department.id == Employee.department_id)
        .join(Branch, Branch.id == Employee.branch_id)
        .join(Designation, Designation.id == Employee.designation_id)
        .where(
            Employee.id == employee_id,
            Employee.organization_id == ctx.organization.id,
        )
    ).first()
    if not row:
        raise NotFoundError("Employee not found in organization.")

    emp, dept_name, branch_name, desig_title = row
    show_confidential = _can_view_confidential_hr(ctx)

    balances = list(
        db.execute(
            select(LeaveBalance).where(LeaveBalance.employee_id == emp.id)
        ).scalars()
    )
    attendance = list(
        db.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.employee_id == emp.id)
            .order_by(AttendanceRecord.attendance_date.desc())
            .limit(15)
        ).scalars()
    )
    reviews = list(
        db.execute(
            select(PerformanceReview)
            .where(PerformanceReview.employee_id == emp.id)
            .order_by(PerformanceReview.review_date.desc())
        ).scalars()
    )

    return {
        "id": emp.id,
        "employee_code": emp.employee_code,
        "first_name": emp.first_name,
        "last_name": emp.last_name,
        "full_name": f"{emp.first_name} {emp.last_name}",
        "email": emp.email,
        "phone": emp.phone,
        "national_id": emp.national_id if show_confidential else "REDACTED",
        "branch_id": emp.branch_id,
        "branch_name": branch_name,
        "department_id": emp.department_id,
        "department_name": dept_name,
        "designation_id": emp.designation_id,
        "designation_title": desig_title,
        "employment_type": emp.employment_type,
        "employment_status": emp.employment_status,
        "join_date": emp.join_date.isoformat(),
        "base_salary": float(emp.base_salary) if show_confidential else None,
        "leave_balances": [
            {
                "leave_type": b.leave_type,
                "entitled_days": float(b.entitled_days),
                "used_days": float(b.used_days),
                "remaining_days": float(b.remaining_days),
            }
            for b in balances
        ],
        "recent_attendance": [
            {
                "date": a.attendance_date.isoformat(),
                "check_in": a.check_in,
                "check_out": a.check_out,
                "status": a.status,
                "hours_worked": float(a.hours_worked),
            }
            for a in attendance
        ],
        "performance_reviews": [
            {
                "id": r.id,
                "review_period": r.review_period,
                "kpi_score": float(r.kpi_score),
                "competency_score": float(r.competency_score),
                "overall_rating": r.overall_rating,
                "strengths": r.strengths,
                "improvements": r.improvements,
                "review_date": r.review_date.isoformat(),
            }
            for r in reviews
        ],
    }


@router.post("/employees", status_code=201)
def create_employee(
    payload: EmployeeCreateSchema,
    ctx: AuthContext = Depends(require_permissions("employees.create")),
    db: Session = Depends(get_db),
) -> dict:
    count = (
        db.execute(
            select(func.count(Employee.id)).where(Employee.organization_id == ctx.organization.id)
        ).scalar_one()
        or 0
    )
    emp_code = f"EMP-{2024001 + count + 1}"

    desig_id = payload.designation_id
    if not desig_id:
        first_desig = db.execute(
            select(Designation).where(Designation.organization_id == ctx.organization.id)
        ).scalars().first()
        if not first_desig:
            first_desig = Designation(
                id=new_uuid(),
                organization_id=ctx.organization.id,
                title="Associate Specialist",
                grade="L3",
            )
            db.add(first_desig)
            db.flush()
        desig_id = first_desig.id

    emp = Employee(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        branch_id=payload.branch_id,
        department_id=payload.department_id,
        designation_id=desig_id,
        employee_code=emp_code,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email.lower(),
        phone=payload.phone,
        national_id=payload.national_id,
        employment_type=payload.employment_type,
        employment_status=payload.employment_status,
        join_date=payload.join_date or date.today(),
        base_salary=Decimal(str(payload.base_salary)),
        emergency_contact_name=payload.emergency_contact_name,
        emergency_contact_phone=payload.emergency_contact_phone,
    )
    db.add(emp)
    db.flush()

    for l_type, ent in [("ANNUAL", 14), ("CASUAL", 7), ("MEDICAL", 7)]:
        db.add(
            LeaveBalance(
                id=new_uuid(),
                organization_id=ctx.organization.id,
                employee_id=emp.id,
                year=date.today().year,
                leave_type=l_type,
                entitled_days=Decimal(str(ent)),
                used_days=Decimal("0.0"),
                remaining_days=Decimal(str(ent)),
            )
        )

    record_audit_log(
        db,
        ctx=ctx,
        action="EMPLOYEE_CREATED",
        entity_type="Employee",
        entity_id=emp.id,
        after_state={"employee_code": emp.employee_code, "email": emp.email},
    )
    db.commit()
    return get_employee(emp.id, ctx, db)


@router.put("/employees/{employee_id}")
def update_employee(
    employee_id: str,
    payload: EmployeeUpdateSchema,
    ctx: AuthContext = Depends(require_permissions("employees.update")),
    db: Session = Depends(get_db),
) -> dict:
    emp = db.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.organization_id == ctx.organization.id,
        )
    ).scalar_one_or_none()
    if not emp:
        raise NotFoundError("Employee not found.")

    if payload.first_name is not None:
        emp.first_name = payload.first_name
    if payload.last_name is not None:
        emp.last_name = payload.last_name
    if payload.phone is not None:
        emp.phone = payload.phone
    if payload.employment_status is not None:
        emp.employment_status = payload.employment_status
    if payload.department_id is not None:
        emp.department_id = payload.department_id
    if payload.base_salary is not None:
        emp.base_salary = Decimal(str(payload.base_salary))

    record_audit_log(db, ctx=ctx, action="EMPLOYEE_UPDATED", entity_type="Employee", entity_id=emp.id)
    db.commit()
    return get_employee(emp.id, ctx, db)


@router.get("/hr/designations")
def list_designations(
    ctx: AuthContext = Depends(require_permissions("employees.view")),
    db: Session = Depends(get_db),
) -> dict:
    desigs = list(
        db.execute(
            select(Designation).where(Designation.organization_id == ctx.organization.id)
        ).scalars()
    )
    return {"items": [{"id": d.id, "title": d.title, "grade": d.grade} for d in desigs]}


@router.get("/hr/attendance")
def list_attendance(
    ctx: AuthContext = Depends(require_permissions("employees.view")),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.execute(
        select(AttendanceRecord, Employee.first_name, Employee.last_name, Employee.employee_code)
        .join(Employee, Employee.id == AttendanceRecord.employee_id)
        .where(AttendanceRecord.organization_id == ctx.organization.id)
        .order_by(AttendanceRecord.attendance_date.desc())
        .limit(100)
    ).all()
    return {
        "items": [
            {
                "id": a.id,
                "employee_id": a.employee_id,
                "employee_code": code,
                "employee_name": f"{fn} {ln}",
                "attendance_date": a.attendance_date.isoformat(),
                "check_in": a.check_in,
                "check_out": a.check_out,
                "status": a.status,
                "hours_worked": float(a.hours_worked),
                "notes": a.notes,
            }
            for a, fn, ln, code in rows
        ]
    }


@router.post("/hr/attendance", status_code=201)
def record_attendance(
    payload: AttendanceCreateSchema,
    ctx: AuthContext = Depends(require_permissions("employees.update")),
    db: Session = Depends(get_db),
) -> dict:
    existing = db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.employee_id == payload.employee_id,
            AttendanceRecord.attendance_date == payload.attendance_date,
        )
    ).scalar_one_or_none()
    if existing:
        existing.check_in = payload.check_in
        existing.check_out = payload.check_out
        existing.status = payload.status
        existing.hours_worked = Decimal(str(payload.hours_worked))
        existing.notes = payload.notes
        db.commit()
        return {"id": existing.id, "status": existing.status}

    rec = AttendanceRecord(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        employee_id=payload.employee_id,
        attendance_date=payload.attendance_date,
        check_in=payload.check_in,
        check_out=payload.check_out,
        status=payload.status,
        hours_worked=Decimal(str(payload.hours_worked)),
        notes=payload.notes,
    )
    db.add(rec)
    db.commit()
    return {"id": rec.id, "status": rec.status}


@router.get("/leave-requests")
def list_leave_requests(
    ctx: AuthContext = Depends(require_permissions("leave.view")),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.execute(
        select(LeaveRequest, Employee.first_name, Employee.last_name, Employee.employee_code)
        .join(Employee, Employee.id == LeaveRequest.employee_id)
        .where(LeaveRequest.organization_id == ctx.organization.id)
        .order_by(LeaveRequest.created_at.desc())
    ).all()
    return {
        "items": [
            {
                "id": lr.id,
                "employee_id": lr.employee_id,
                "employee_code": code,
                "employee_name": f"{fn} {ln}",
                "leave_type": lr.leave_type,
                "start_date": lr.start_date.isoformat(),
                "end_date": lr.end_date.isoformat(),
                "days_count": float(lr.days_count),
                "reason": lr.reason,
                "status": lr.status,
                "rejection_reason": lr.rejection_reason,
                "created_at": lr.created_at.isoformat() if lr.created_at else None,
            }
            for lr, fn, ln, code in rows
        ]
    }


@router.post("/leave-requests", status_code=201)
def create_leave_request(
    payload: LeaveRequestCreateSchema,
    ctx: AuthContext = Depends(require_permissions("leave.create")),
    db: Session = Depends(get_db),
) -> dict:
    emp = db.execute(
        select(Employee).where(
            Employee.id == payload.employee_id,
            Employee.organization_id == ctx.organization.id,
        )
    ).scalar_one_or_none()
    if not emp:
        raise NotFoundError("Employee not found in organization.")

    lr = LeaveRequest(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        employee_id=emp.id,
        requested_by_user_id=ctx.user.id,
        leave_type=payload.leave_type.upper(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        days_count=Decimal(str(payload.days_count)),
        reason=payload.reason,
        status="PENDING",
    )
    db.add(lr)
    db.commit()
    return {
        "id": lr.id,
        "employee_id": lr.employee_id,
        "leave_type": lr.leave_type,
        "days_count": float(lr.days_count),
        "status": lr.status,
    }


@router.post("/leave-requests/{leave_id}/approve")
def approve_leave_request(
    leave_id: str,
    payload: LeaveApprovalSchema,
    ctx: AuthContext = Depends(require_permissions("leave.approve")),
    db: Session = Depends(get_db),
) -> dict:
    lr = db.execute(
        select(LeaveRequest).where(
            LeaveRequest.id == leave_id,
            LeaveRequest.organization_id == ctx.organization.id,
        )
    ).scalar_one_or_none()
    if not lr:
        raise NotFoundError("Leave request not found.")
    if lr.status != "PENDING":
        raise BusinessRuleError(f"Leave request is already {lr.status}.")

    if lr.requested_by_user_id == ctx.user.id and payload.action.upper() == "APPROVE":
        raise ForbiddenError(
            "Separation of Duties: You cannot approve your own leave request.",
            code="SELF_APPROVAL_FORBIDDEN",
        )

    act = payload.action.upper()
    if act == "REJECT":
        lr.status = "REJECTED"
        lr.rejection_reason = payload.rejection_reason or "Declined by manager"
    else:
        lr.status = "APPROVED"
        lr.approved_by_id = ctx.user.id
        bal = db.execute(
            select(LeaveBalance).where(
                LeaveBalance.employee_id == lr.employee_id,
                LeaveBalance.leave_type == lr.leave_type,
            )
        ).scalar_one_or_none()
        if bal:
            bal.used_days = bal.used_days + lr.days_count
            bal.remaining_days = max(Decimal("0.0"), bal.entitled_days - bal.used_days)

    record_audit_log(db, ctx=ctx, action=f"LEAVE_{lr.status}", entity_type="LeaveRequest", entity_id=lr.id)
    db.commit()
    return {"id": lr.id, "status": lr.status}


@router.get("/hr/performance")
def list_performance_reviews(
    ctx: AuthContext = Depends(require_permissions("employees.view")),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.execute(
        select(PerformanceReview, Employee.first_name, Employee.last_name, Employee.employee_code)
        .join(Employee, Employee.id == PerformanceReview.employee_id)
        .where(PerformanceReview.organization_id == ctx.organization.id)
        .order_by(PerformanceReview.review_date.desc())
    ).all()
    return {
        "items": [
            {
                "id": r.id,
                "employee_id": r.employee_id,
                "employee_code": code,
                "employee_name": f"{fn} {ln}",
                "review_period": r.review_period,
                "kpi_score": float(r.kpi_score),
                "competency_score": float(r.competency_score),
                "overall_rating": r.overall_rating,
                "strengths": r.strengths,
                "improvements": r.improvements,
                "status": r.status,
                "review_date": r.review_date.isoformat(),
            }
            for r, fn, ln, code in rows
        ]
    }


@router.post("/hr/performance", status_code=201)
def create_performance_review(
    payload: PerformanceCreateSchema,
    ctx: AuthContext = Depends(require_permissions("employees.update")),
    db: Session = Depends(get_db),
) -> dict:
    rev = PerformanceReview(
        id=new_uuid(),
        organization_id=ctx.organization.id,
        employee_id=payload.employee_id,
        reviewer_id=ctx.user.id,
        review_period=payload.review_period,
        kpi_score=Decimal(str(payload.kpi_score)),
        competency_score=Decimal(str(payload.competency_score)),
        overall_rating=payload.overall_rating,
        strengths=payload.strengths,
        improvements=payload.improvements,
        status="COMPLETED",
        review_date=date.today(),
    )
    db.add(rev)
    db.commit()
    return {"id": rev.id, "overall_rating": rev.overall_rating}
