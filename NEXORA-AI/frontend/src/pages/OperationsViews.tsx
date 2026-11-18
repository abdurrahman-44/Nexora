import React, { useEffect, useState } from "react";
import {
  ArrowLeftRight,
  Building2,
  CheckCircle2,
  Download,
  Lock,
  Package,
  Plus,
  ShoppingBag,
  Truck,
  Users,
  XCircle,
} from "lucide-react";
import { apiRequest } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { exportRowsToCSV, formatCurrency, formatDate } from "../utils/formatters";

// ============================================================================
// 1. ORGANIZATION, BRANCHES & DEPARTMENTS VIEW
// ============================================================================
export const OrganizationView: React.FC<{ subTab?: "org" | "branches" | "departments" }> = ({
  subTab = "org",
}) => {
  const { user, hasPermission } = useAuth();
  const [orgData, setOrgData] = useState<any | null>(null);
  const [branchName, setBranchName] = useState("");
  const [branchCode, setBranchCode] = useState("");
  const [branchCity, setBranchCity] = useState("");
  const [deptName, setDeptName] = useState("");
  const [deptCode, setDeptCode] = useState("");
  const [deptBudget, setDeptBudget] = useState("12000000");
  const [msg, setMsg] = useState<string | null>(null);

  const loadOrg = async () => {
    if (!user) return;
    const res = await apiRequest(`/organizations/${user.organization_id}`);
    setOrgData(res);
  };

  useEffect(() => {
    loadOrg();
  }, [user?.organization_id]);

  const handleCreateBranch = async (e: React.FormEvent) => {
    e.preventDefault();
    await apiRequest("/branches", {
      method: "POST",
      body: JSON.stringify({ name: branchName, code: branchCode, city: branchCity }),
    });
    setBranchName("");
    setBranchCode("");
    setBranchCity("");
    setMsg("Branch created and isolated under current tenant.");
    loadOrg();
  };

  const handleCreateDept = async (e: React.FormEvent) => {
    e.preventDefault();
    await apiRequest("/departments", {
      method: "POST",
      body: JSON.stringify({
        name: deptName,
        code: deptCode,
        budget_allocated: Number(deptBudget),
      }),
    });
    setDeptName("");
    setDeptCode("");
    setMsg("Department created successfully.");
    loadOrg();
  };

  if (!orgData) return <div className="glass-panel p-6 rounded-2xl">Loading organization...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Building2 className="w-5 h-5 text-[#648BFF]" />
            {orgData.name} ({orgData.code})
          </h1>
          <p className="text-xs text-[#94A3B8]">
            Reg No: {orgData.registration_number} • Tax ID: {orgData.tax_id} • Currency: {orgData.default_currency} • Timezone: {orgData.timezone}
          </p>
        </div>
      </div>

      {msg && (
        <div className="p-3 rounded-xl bg-[#20C997]/15 border border-[#20C997]/40 text-xs text-[#20C997]">
          {msg}
        </div>
      )}

      {/* Branches Table & Form */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8 glass-table-container rounded-2xl p-5 space-y-4">
          <h2 className="text-sm font-bold">Active Regional Branches ({orgData.branches?.length || 0})</h2>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                <th className="py-2">Code</th>
                <th className="py-2">Branch Name</th>
                <th className="py-2">City</th>
                <th className="py-2">Manager</th>
                <th className="py-2">HQ</th>
              </tr>
            </thead>
            <tbody>
              {(orgData.branches || []).map((b: any) => (
                <tr key={b.id} className="border-b border-white/5">
                  <td className="py-2.5 font-mono text-[#648BFF]">{b.code}</td>
                  <td className="py-2.5 font-medium">{b.name}</td>
                  <td className="py-2.5">{b.city}</td>
                  <td className="py-2.5 text-[#94A3B8]">{b.manager_name || "—"}</td>
                  <td className="py-2.5">
                    {b.is_headquarters ? (
                      <span className="px-2 py-0.5 rounded bg-[#20C997]/20 text-[#20C997] text-[10px]">HQ</span>
                    ) : (
                      "Regional"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {hasPermission("organizations.manage") && (
          <form onSubmit={handleCreateBranch} className="lg:col-span-4 glass-panel rounded-2xl p-5 space-y-3">
            <h3 className="text-sm font-bold">Register New Branch</h3>
            <input
              required
              placeholder="Branch Code (e.g. BR-JAF-NTH)"
              value={branchCode}
              onChange={(e) => setBranchCode(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
            />
            <input
              required
              placeholder="Branch Name"
              value={branchName}
              onChange={(e) => setBranchName(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
            />
            <input
              required
              placeholder="City (e.g. Jaffna)"
              value={branchCity}
              onChange={(e) => setBranchCity(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
            />
            <button
              type="submit"
              className="w-full py-2 rounded-xl bg-[#648BFF] text-white text-xs font-semibold"
            >
              + Add Branch
            </button>
          </form>
        )}
      </div>

      {/* Departments Table & Form */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8 glass-table-container rounded-2xl p-5 space-y-4">
          <h2 className="text-sm font-bold">Corporate Departments ({orgData.departments?.length || 0})</h2>
          <table className="w-full text-xs tabular-nums">
            <thead>
              <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                <th className="py-2">Code</th>
                <th className="py-2">Department Name</th>
                <th className="py-2 text-right">Annual Budget Allocated</th>
              </tr>
            </thead>
            <tbody>
              {(orgData.departments || []).map((d: any) => (
                <tr key={d.id} className="border-b border-white/5">
                  <td className="py-2.5 font-mono text-[#8B7CFF]">{d.code}</td>
                  <td className="py-2.5 font-medium">{d.name}</td>
                  <td className="py-2.5 text-right text-[#20C997]">
                    {formatCurrency(d.budget_allocated, orgData.default_currency)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {hasPermission("organizations.manage") && (
          <form onSubmit={handleCreateDept} className="lg:col-span-4 glass-panel rounded-2xl p-5 space-y-3">
            <h3 className="text-sm font-bold">Create Department</h3>
            <input
              required
              placeholder="Department Code (e.g. DEPT-RND)"
              value={deptCode}
              onChange={(e) => setDeptCode(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
            />
            <input
              required
              placeholder="Department Name"
              value={deptName}
              onChange={(e) => setDeptName(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
            />
            <input
              type="number"
              required
              placeholder="Annual Budget (LKR)"
              value={deptBudget}
              onChange={(e) => setDeptBudget(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
            />
            <button
              type="submit"
              className="w-full py-2 rounded-xl bg-[#8B7CFF] text-white text-xs font-semibold"
            >
              + Create Department
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// 2. HUMAN RESOURCES MODULE (Employees, Attendance, Leave, Performance)
// ============================================================================
export const HRModuleView: React.FC<{ activeSub?: string }> = ({ activeSub = "employees" }) => {
  const { user, hasPermission } = useAuth();
  const [tab, setTab] = useState(activeSub);
  const [employees, setEmployees] = useState<any[]>([]);
  const [confidentialVisible, setConfidentialVisible] = useState(false);
  const [attendance, setAttendance] = useState<any[]>([]);
  const [leaves, setLeaves] = useState<any[]>([]);
  const [reviews, setReviews] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Add Employee form state
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [empEmail, setEmpEmail] = useState("");
  const [baseSalary, setBaseSalary] = useState("185000");

  // Leave request form state
  const [leaveEmpId, setLeaveEmpId] = useState("");
  const [leaveType, setLeaveType] = useState("ANNUAL");
  const [leaveDays, setLeaveDays] = useState("2");
  const [leaveReason, setLeaveReason] = useState("");

  useEffect(() => {
    setTab(activeSub);
  }, [activeSub]);

  const loadHRData = async () => {
    try {
      const [empRes, attRes, lvRes, revRes] = await Promise.all([
        apiRequest("/employees"),
        apiRequest("/hr/attendance"),
        apiRequest("/leave-requests"),
        apiRequest("/hr/performance"),
      ]);
      setEmployees(empRes.items || []);
      setConfidentialVisible(Boolean(empRes.confidential_visible));
      if (empRes.items?.length && !leaveEmpId) {
        setLeaveEmpId(empRes.items[0].id);
      }
      setAttendance(attRes.items || []);
      setLeaves(lvRes.items || []);
      setReviews(revRes.items || []);
    } catch (e: any) {
      setErrorMsg(e.message);
    }
  };

  useEffect(() => {
    loadHRData();
  }, [user?.organization_id]);

  const handleAddEmployee = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    try {
      await apiRequest("/employees", {
        method: "POST",
        body: JSON.stringify({
          first_name: firstName,
          last_name: lastName,
          email: empEmail,
          branch_id: user?.branches?.[0]?.id,
          department_id: user?.departments?.[0]?.id,
          base_salary: Number(baseSalary),
        }),
      });
      setShowAddModal(false);
      setFirstName("");
      setLastName("");
      setEmpEmail("");
      setStatusMsg("New employee registered and leave balances initialized.");
      loadHRData();
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleCreateLeave = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    try {
      const todayStr = new Date().toISOString().slice(0, 10);
      await apiRequest("/leave-requests", {
        method: "POST",
        body: JSON.stringify({
          employee_id: leaveEmpId,
          leave_type: leaveType,
          start_date: todayStr,
          end_date: todayStr,
          days_count: Number(leaveDays),
          reason: leaveReason || "Personal leave request",
        }),
      });
      setLeaveReason("");
      setStatusMsg("Leave request submitted to approval workflow.");
      loadHRData();
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleApproveLeave = async (id: string, action: "APPROVE" | "REJECT") => {
    setErrorMsg(null);
    try {
      await apiRequest(`/leave-requests/${id}/approve`, {
        method: "POST",
        body: JSON.stringify({ action, rejection_reason: action === "REJECT" ? "Operational coverage required" : null }),
      });
      setStatusMsg(`Leave request ${action.toLowerCase()}d.`);
      loadHRData();
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const filteredEmployees = employees.filter(
    (e) =>
      !search.trim() ||
      e.full_name.toLowerCase().includes(search.toLowerCase()) ||
      e.employee_code.toLowerCase().includes(search.toLowerCase()) ||
      e.department_name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Users className="w-5 h-5 text-[#648BFF]" />
            Human Capital & Workforce Management
          </h1>
          <p className="text-xs text-[#94A3B8]">
            {employees.length} Active Employees • Confidential Salary Access:{" "}
            <strong className={confidentialVisible ? "text-[#20C997]" : "text-[#F4B740]"}>
              {confidentialVisible ? "Granted (HR / Executive)" : "Masked by RBAC Policy"}
            </strong>
          </p>
        </div>

        <div className="flex items-center gap-2">
          {(["employees", "attendance", "leave", "performance"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium capitalize transition ${
                tab === t ? "bg-[#648BFF] text-white" : "glass-panel text-[#94A3B8]"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {statusMsg && (
        <div className="p-3 rounded-xl bg-[#20C997]/15 border border-[#20C997]/40 text-xs text-[#20C997]">
          {statusMsg}
        </div>
      )}
      {errorMsg && (
        <div className="p-3 rounded-xl bg-[#F06464]/15 border border-[#F06464]/40 text-xs text-[#F06464]">
          {errorMsg}
        </div>
      )}

      {tab === "employees" && (
        <div className="glass-table-container rounded-2xl p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter employees by name, code, or department..."
              className="px-3.5 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs w-72"
            />
            <div className="flex items-center gap-2">
              <button
                onClick={() => exportRowsToCSV("nexora_employees.csv", filteredEmployees)}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl glass-panel text-xs"
              >
                <Download className="w-3.5 h-3.5" /> Export CSV
              </button>
              {hasPermission("employees.create") && (
                <button
                  onClick={() => setShowAddModal(true)}
                  className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#648BFF] text-white text-xs font-semibold"
                >
                  <Plus className="w-3.5 h-3.5" /> Add Employee
                </button>
              )}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs tabular-nums">
              <thead>
                <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                  <th className="py-2.5">Code</th>
                  <th className="py-2.5">Employee Name</th>
                  <th className="py-2.5">Department</th>
                  <th className="py-2.5">Designation</th>
                  <th className="py-2.5">Branch</th>
                  <th className="py-2.5">Join Date</th>
                  <th className="py-2.5 text-right">Base Salary (LKR)</th>
                  <th className="py-2.5">Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredEmployees.map((emp) => (
                  <tr key={emp.id} className="border-b border-white/5 hover:bg-white/5">
                    <td className="py-2.5 font-mono text-[#648BFF]">{emp.employee_code}</td>
                    <td className="py-2.5 font-medium">
                      <div>{emp.full_name}</div>
                      <div className="text-[10px] text-[#94A3B8]">{emp.email}</div>
                    </td>
                    <td className="py-2.5">{emp.department_name}</td>
                    <td className="py-2.5 text-[#94A3B8]">{emp.designation_title}</td>
                    <td className="py-2.5">{emp.branch_name}</td>
                    <td className="py-2.5">{formatDate(emp.join_date)}</td>
                    <td className="py-2.5 text-right font-mono">
                      {emp.base_salary !== null ? (
                        <span className="text-[#20C997]">{formatCurrency(emp.base_salary)}</span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[#94A3B8]">
                          <Lock className="w-3 h-3" /> Protected
                        </span>
                      )}
                    </td>
                    <td className="py-2.5">
                      <span className="px-2 py-0.5 rounded-full text-[10px] bg-[#20C997]/15 text-[#20C997]">
                        {emp.employment_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "attendance" && (
        <div className="glass-table-container rounded-2xl p-5 space-y-4">
          <h2 className="text-sm font-bold">Biometric & Hybrid Attendance Logs</h2>
          <table className="w-full text-xs tabular-nums">
            <thead>
              <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                <th className="py-2">Date</th>
                <th className="py-2">Code</th>
                <th className="py-2">Employee</th>
                <th className="py-2">Check-In</th>
                <th className="py-2">Check-Out</th>
                <th className="py-2 text-right">Hours</th>
                <th className="py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {attendance.map((a) => (
                <tr key={a.id} className="border-b border-white/5">
                  <td className="py-2">{formatDate(a.attendance_date)}</td>
                  <td className="py-2 font-mono text-[#648BFF]">{a.employee_code}</td>
                  <td className="py-2 font-medium">{a.employee_name}</td>
                  <td className="py-2 font-mono">{a.check_in}</td>
                  <td className="py-2 font-mono">{a.check_out}</td>
                  <td className="py-2 text-right">{a.hours_worked}h</td>
                  <td className="py-2">
                    <span className="px-2 py-0.5 rounded bg-[#20C997]/15 text-[#20C997] text-[10px]">
                      {a.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "leave" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 glass-table-container rounded-2xl p-5 space-y-4">
            <h2 className="text-sm font-bold">Employee Leave Requests & Workflow Actions</h2>
            <table className="w-full text-xs tabular-nums">
              <thead>
                <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                  <th className="py-2">Employee</th>
                  <th className="py-2">Type</th>
                  <th className="py-2">Dates</th>
                  <th className="py-2">Days</th>
                  <th className="py-2">Status</th>
                  <th className="py-2 text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {leaves.map((l) => (
                  <tr key={l.id} className="border-b border-white/5">
                    <td className="py-2.5 font-medium">{l.employee_name}</td>
                    <td className="py-2.5">{l.leave_type}</td>
                    <td className="py-2.5">
                      {formatDate(l.start_date)} → {formatDate(l.end_date)}
                    </td>
                    <td className="py-2.5">{l.days_count}</td>
                    <td className="py-2.5">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] ${
                          l.status === "APPROVED"
                            ? "bg-[#20C997]/20 text-[#20C997]"
                            : l.status === "REJECTED"
                            ? "bg-[#F06464]/20 text-[#F06464]"
                            : "bg-[#F4B740]/20 text-[#F4B740]"
                        }`}
                      >
                        {l.status}
                      </span>
                    </td>
                    <td className="py-2.5 text-right space-x-1.5">
                      {l.status === "PENDING" && hasPermission("leave.approve") && (
                        <>
                          <button
                            onClick={() => handleApproveLeave(l.id, "APPROVE")}
                            className="px-2 py-1 rounded bg-[#20C997]/20 text-[#20C997] hover:bg-[#20C997]/30 text-[11px]"
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => handleApproveLeave(l.id, "REJECT")}
                            className="px-2 py-1 rounded bg-[#F06464]/20 text-[#F06464] hover:bg-[#F06464]/30 text-[11px]"
                          >
                            Reject
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <form onSubmit={handleCreateLeave} className="lg:col-span-4 glass-panel rounded-2xl p-5 space-y-3">
            <h3 className="text-sm font-bold">Submit Leave Request</h3>
            <select
              value={leaveEmpId}
              onChange={(e) => setLeaveEmpId(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
            >
              {employees.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.employee_code} — {e.full_name}
                </option>
              ))}
            </select>
            <select
              value={leaveType}
              onChange={(e) => setLeaveType(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
            >
              <option value="ANNUAL">Annual Leave</option>
              <option value="CASUAL">Casual Leave</option>
              <option value="MEDICAL">Medical Leave</option>
            </select>
            <input
              type="number"
              min="0.5"
              step="0.5"
              value={leaveDays}
              onChange={(e) => setLeaveDays(e.target.value)}
              placeholder="Number of Days"
              className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
            />
            <textarea
              required
              value={leaveReason}
              onChange={(e) => setLeaveReason(e.target.value)}
              placeholder="Reason for leave..."
              className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
            />
            <button
              type="submit"
              className="w-full py-2 rounded-xl bg-[#648BFF] text-white text-xs font-semibold"
            >
              Submit Leave Request
            </button>
          </form>
        </div>
      )}

      {tab === "performance" && (
        <div className="glass-table-container rounded-2xl p-5 space-y-4">
          <h2 className="text-sm font-bold">Employee KPI & Competency Evaluations</h2>
          <table className="w-full text-xs tabular-nums">
            <thead>
              <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                <th className="py-2">Employee</th>
                <th className="py-2">Review Period</th>
                <th className="py-2 text-right">KPI Score</th>
                <th className="py-2 text-right">Competency</th>
                <th className="py-2">Rating</th>
                <th className="py-2">Strengths</th>
              </tr>
            </thead>
            <tbody>
              {reviews.map((r) => (
                <tr key={r.id} className="border-b border-white/5">
                  <td className="py-2.5 font-medium">{r.employee_name}</td>
                  <td className="py-2.5">{r.review_period}</td>
                  <td className="py-2.5 text-right text-[#648BFF] font-bold">{r.kpi_score}/5.0</td>
                  <td className="py-2.5 text-right text-[#8B7CFF] font-bold">{r.competency_score}/5.0</td>
                  <td className="py-2.5">
                    <span className="px-2 py-0.5 rounded bg-[#20C997]/15 text-[#20C997] text-[10px]">
                      {r.overall_rating}
                    </span>
                  </td>
                  <td className="py-2.5 text-[#94A3B8] max-w-md truncate">{r.strengths}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Employee Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <form
            onSubmit={handleAddEmployee}
            className="w-full max-w-md glass-panel rounded-2xl p-6 border border-white/20 space-y-4"
          >
            <h3 className="text-base font-bold">Register New Employee</h3>
            <input
              required
              placeholder="First Name"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
            />
            <input
              required
              placeholder="Last Name"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
            />
            <input
              type="email"
              required
              placeholder="Corporate Email"
              value={empEmail}
              onChange={(e) => setEmpEmail(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
            />
            <input
              type="number"
              required
              placeholder="Monthly Base Salary (LKR)"
              value={baseSalary}
              onChange={(e) => setBaseSalary(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 rounded-xl bg-white/10 text-xs"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 rounded-xl bg-[#648BFF] text-white text-xs font-semibold"
              >
                Save Employee
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// 3. INVENTORY & WAREHOUSES MODULE
// ============================================================================
export const InventoryModuleView: React.FC<{ showWarehouses?: boolean }> = ({
  showWarehouses = false,
}) => {
  const { user, hasPermission } = useAuth();
  const [tab, setTab] = useState<"products" | "warehouses" | "movements">(
    showWarehouses ? "warehouses" : "products"
  );
  const [products, setProducts] = useState<any[]>([]);
  const [warehouses, setWarehouses] = useState<any[]>([]);
  const [movements, setMovements] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // Add Product & Movement forms
  const [sku, setSku] = useState("");
  const [prodName, setProdName] = useState("");
  const [costPrice, setCostPrice] = useState("45000");
  const [sellPrice, setSellPrice] = useState("62000");
  const [initStock, setInitStock] = useState("25");

  const [movProdId, setMovProdId] = useState("");
  const [movWhId, setMovWhId] = useState("");
  const [movType, setMovType] = useState("RECEIPT");
  const [movQty, setMovQty] = useState("10");
  const [movCost, setMovCost] = useState("48000");

  useEffect(() => {
    setTab(showWarehouses ? "warehouses" : "products");
  }, [showWarehouses]);

  const loadInventory = async () => {
    try {
      const [pRes, wRes, mRes] = await Promise.all([
        apiRequest("/inventory/products"),
        apiRequest("/inventory/warehouses"),
        apiRequest("/inventory/movements"),
      ]);
      setProducts(pRes.items || []);
      setWarehouses(wRes.items || []);
      setMovements(mRes.items || []);
      if (pRes.items?.length && !movProdId) setMovProdId(pRes.items[0].id);
      if (wRes.items?.length && !movWhId) setMovWhId(wRes.items[0].id);
    } catch (e: any) {
      setErr(e.message);
    }
  };

  useEffect(() => {
    loadInventory();
  }, [user?.organization_id]);

  const handleCreateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    setMsg(null);
    try {
      await apiRequest("/inventory/products", {
        method: "POST",
        body: JSON.stringify({
          sku,
          name: prodName,
          cost_price: Number(costPrice),
          selling_price: Number(sellPrice),
          initial_stock: Number(initStock),
          warehouse_id: warehouses[0]?.id,
        }),
      });
      setSku("");
      setProdName("");
      setMsg("Product registered and initial stock receipt posted.");
      loadInventory();
    } catch (e: any) {
      setErr(e.message);
    }
  };

  const handleRecordMovement = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    setMsg(null);
    try {
      const res = await apiRequest("/inventory/movements", {
        method: "POST",
        body: JSON.stringify({
          product_id: movProdId,
          warehouse_id: movWhId,
          movement_type: movType,
          quantity: Number(movQty),
          unit_cost: movType === "RECEIPT" ? Number(movCost) : undefined,
        }),
      });
      setMsg(
        `Movement ${res.reference_number} posted! New Balance: ${res.balance_after} | Updated Weighted Avg Cost: LKR ${res.weighted_avg_cost}`
      );
      loadInventory();
    } catch (e: any) {
      setErr(e.message);
    }
  };

  const filteredProducts = products.filter((p) => {
    if (lowStockOnly && !p.is_low_stock) return false;
    if (
      search.trim() &&
      !p.name.toLowerCase().includes(search.toLowerCase()) &&
      !p.sku.toLowerCase().includes(search.toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Package className="w-5 h-5 text-[#648BFF]" />
            Inventory & Multi-Warehouse Valuation (Weighted Average Cost)
          </h1>
          <p className="text-xs text-[#94A3B8]">
            {products.length} Active SKUs • Negative Stock Prevention Active • Real-Time WAC Recalculation
          </p>
        </div>

        <div className="flex items-center gap-2">
          {(["products", "warehouses", "movements"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium capitalize ${
                tab === t ? "bg-[#648BFF] text-white" : "glass-panel text-[#94A3B8]"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {msg && (
        <div className="p-3 rounded-xl bg-[#20C997]/15 border border-[#20C997]/40 text-xs text-[#20C997]">
          {msg}
        </div>
      )}
      {err && (
        <div className="p-3 rounded-xl bg-[#F06464]/15 border border-[#F06464]/40 text-xs text-[#F06464]">
          {err}
        </div>
      )}

      {tab === "products" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-9 glass-table-container rounded-2xl p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search SKU or product name..."
                  className="px-3 py-1.5 rounded-xl bg-[#141F31] border border-white/10 text-xs w-64"
                />
                <label className="flex items-center gap-1.5 text-xs text-[#94A3B8] cursor-pointer">
                  <input
                    type="checkbox"
                    checked={lowStockOnly}
                    onChange={(e) => setLowStockOnly(e.target.checked)}
                  />
                  Low-Stock Only
                </label>
              </div>
              <button
                onClick={() => exportRowsToCSV("nexora_inventory_valuation.csv", filteredProducts)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl glass-panel text-xs"
              >
                <Download className="w-3.5 h-3.5" /> Export Valuation CSV
              </button>
            </div>

            <div className="overflow-x-auto max-h-[520px]">
              <table className="w-full text-xs tabular-nums">
                <thead>
                  <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                    <th className="py-2">SKU</th>
                    <th className="py-2">Product Name</th>
                    <th className="py-2 text-right">Available</th>
                    <th className="py-2 text-right">Reorder Lvl</th>
                    <th className="py-2 text-right">Weighted Avg Cost</th>
                    <th className="py-2 text-right">Selling Price</th>
                    <th className="py-2 text-right">Valuation (LKR)</th>
                    <th className="py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredProducts.map((p) => (
                    <tr key={p.id} className="border-b border-white/5 hover:bg-white/5">
                      <td className="py-2 font-mono text-[#648BFF]">{p.sku}</td>
                      <td className="py-2 font-medium">{p.name}</td>
                      <td className="py-2 text-right font-bold">
                        {p.quantity_available} {p.uom}
                      </td>
                      <td className="py-2 text-right text-[#94A3B8]">{p.reorder_level}</td>
                      <td className="py-2 text-right">{formatCurrency(p.weighted_avg_cost)}</td>
                      <td className="py-2 text-right text-[#20C997]">
                        {formatCurrency(p.selling_price)}
                      </td>
                      <td className="py-2 text-right font-semibold">
                        {formatCurrency(p.total_valuation)}
                      </td>
                      <td className="py-2">
                        {p.is_low_stock ? (
                          <span className="px-2 py-0.5 rounded bg-[#F06464]/20 text-[#F06464] text-[10px]">
                            LOW STOCK
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded bg-[#20C997]/20 text-[#20C997] text-[10px]">
                            OPTIMAL
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="lg:col-span-3 space-y-5">
            {hasPermission("inventory.manage") && (
              <form onSubmit={handleCreateProduct} className="glass-panel rounded-2xl p-4 space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#648BFF]">
                  + Register New Product SKU
                </h3>
                <input
                  required
                  placeholder="SKU (e.g. NEX-SRV-999)"
                  value={sku}
                  onChange={(e) => setSku(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
                />
                <input
                  required
                  placeholder="Product Name"
                  value={prodName}
                  onChange={(e) => setProdName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="number"
                    required
                    placeholder="Cost (LKR)"
                    value={costPrice}
                    onChange={(e) => setCostPrice(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
                  />
                  <input
                    type="number"
                    required
                    placeholder="Sell (LKR)"
                    value={sellPrice}
                    onChange={(e) => setSellPrice(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
                  />
                </div>
                <input
                  type="number"
                  required
                  placeholder="Opening Stock Qty"
                  value={initStock}
                  onChange={(e) => setInitStock(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
                />
                <button
                  type="submit"
                  className="w-full py-2 rounded-xl bg-[#648BFF] text-white text-xs font-semibold"
                >
                  Create Product
                </button>
              </form>
            )}

            {hasPermission("inventory.adjust") && (
              <form onSubmit={handleRecordMovement} className="glass-panel rounded-2xl p-4 space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#20C997]">
                  Record Stock Receipt / Issue
                </h3>
                <select
                  value={movProdId}
                  onChange={(e) => setMovProdId(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
                >
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.sku} ({p.quantity_available} avail)
                    </option>
                  ))}
                </select>
                <select
                  value={movWhId}
                  onChange={(e) => setMovWhId(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
                >
                  {warehouses.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.code} — {w.name}
                    </option>
                  ))}
                </select>
                <select
                  value={movType}
                  onChange={(e) => setMovType(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
                >
                  <option value="RECEIPT">RECEIPT (Inbound + WAC Update)</option>
                  <option value="ISSUE">ISSUE (Outbound — Blocks Negative)</option>
                  <option value="ADJUSTMENT_IN">ADJUSTMENT_IN</option>
                  <option value="ADJUSTMENT_OUT">ADJUSTMENT_OUT</option>
                </select>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="number"
                    required
                    placeholder="Qty"
                    value={movQty}
                    onChange={(e) => setMovQty(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
                  />
                  {movType === "RECEIPT" && (
                    <input
                      type="number"
                      required
                      placeholder="Unit Cost"
                      value={movCost}
                      onChange={(e) => setMovCost(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
                    />
                  )}
                </div>
                <button
                  type="submit"
                  className="w-full py-2 rounded-xl bg-[#20C997] text-[#080D18] text-xs font-bold"
                >
                  Execute Atomic Movement
                </button>
              </form>
            )}
          </div>
        </div>
      )}

      {tab === "warehouses" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {warehouses.map((w) => (
            <div key={w.id} className="glass-panel rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-[#648BFF]">{w.code}</span>
                <span className="text-xs text-[#20C997] font-semibold">
                  {w.utilization_percent}% Utilized
                </span>
              </div>
              <h3 className="text-base font-bold">{w.name}</h3>
              <p className="text-xs text-[#94A3B8]">Manager: {w.manager_name}</p>
              <div className="pt-2 border-t border-white/10 flex items-center justify-between text-xs tabular-nums">
                <span>{w.sku_count} SKUs ({w.total_units} units)</span>
                <span className="font-bold text-[#648BFF]">
                  {formatCurrency(w.total_valuation)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "movements" && (
        <div className="glass-table-container rounded-2xl p-5 space-y-4">
          <h2 className="text-sm font-bold">Immutable Stock Movement Ledger</h2>
          <table className="w-full text-xs tabular-nums">
            <thead>
              <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                <th className="py-2">Reference</th>
                <th className="py-2">SKU & Product</th>
                <th className="py-2">Warehouse</th>
                <th className="py-2">Type</th>
                <th className="py-2 text-right">Quantity</th>
                <th className="py-2 text-right">Balance After</th>
                <th className="py-2 text-right">Unit Cost</th>
              </tr>
            </thead>
            <tbody>
              {movements.map((m) => (
                <tr key={m.id} className="border-b border-white/5">
                  <td className="py-2 font-mono text-[#648BFF]">{m.reference_number}</td>
                  <td className="py-2">
                    <span className="font-mono mr-1.5">{m.sku}</span>
                    {m.product_name}
                  </td>
                  <td className="py-2 text-[#94A3B8]">{m.warehouse_name}</td>
                  <td className="py-2">
                    <span className="px-2 py-0.5 rounded bg-white/10 text-[10px]">
                      {m.movement_type}
                    </span>
                  </td>
                  <td className="py-2 text-right font-semibold">{m.quantity}</td>
                  <td className="py-2 text-right">{m.balance_after}</td>
                  <td className="py-2 text-right">{formatCurrency(m.unit_cost)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// 4. PROCUREMENT & SUPPLIERS MODULE
// ============================================================================
export const ProcurementModuleView: React.FC<{ showSuppliers?: boolean }> = ({
  showSuppliers = false,
}) => {
  const { user, hasPermission } = useAuth();
  const [tab, setTab] = useState<"pos" | "prs" | "grns" | "suppliers">(
    showSuppliers ? "suppliers" : "pos"
  );
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [prs, setPrs] = useState<any[]>([]);
  const [pos, setPos] = useState<any[]>([]);
  const [grns, setGrns] = useState<any[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [poSupId, setPoSupId] = useState("");
  const [poProdId, setPoProdId] = useState("");
  const [poQty, setPoQty] = useState("10");
  const [poPrice, setPoPrice] = useState("42000");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setTab(showSuppliers ? "suppliers" : "pos");
  }, [showSuppliers]);

  const loadProcurement = async () => {
    try {
      const [sRes, prRes, poRes, grnRes, prodRes] = await Promise.all([
        apiRequest("/suppliers"),
        apiRequest("/purchase-requests"),
        apiRequest("/purchase-orders"),
        apiRequest("/goods-receipts"),
        apiRequest("/inventory/products"),
      ]);
      setSuppliers(sRes.items || []);
      setPrs(prRes.items || []);
      setPos(poRes.items || []);
      setGrns(grnRes.items || []);
      setProducts(prodRes.items || []);
      if (sRes.items?.length && !poSupId) setPoSupId(sRes.items[0].id);
      if (prodRes.items?.length && !poProdId) setPoProdId(prodRes.items[0].id);
    } catch (e: any) {
      setErr(e.message);
    }
  };

  useEffect(() => {
    loadProcurement();
  }, [user?.organization_id]);

  const handleCreatePO = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    setMsg(null);
    try {
      const res = await apiRequest("/purchase-orders", {
        method: "POST",
        body: JSON.stringify({
          supplier_id: poSupId,
          items: [
            {
              product_id: poProdId,
              ordered_qty: Number(poQty),
              unit_price: Number(poPrice),
              tax_rate: 8.0,
            },
          ],
        }),
      });
      setMsg(
        `Purchase Order ${res.po_number} created (Total: ${formatCurrency(res.total_amount)}). Requires ${res.approval_step_required}-step approval.`
      );
      loadProcurement();
    } catch (e: any) {
      setErr(e.message);
    }
  };

  const handleApprovePO = async (poId: string, action: "APPROVE" | "REJECT") => {
    setErr(null);
    setMsg(null);
    try {
      const res = await apiRequest(`/purchase-orders/${poId}/approve`, {
        method: "POST",
        body: JSON.stringify({
          action,
          comments: action === "REJECT" ? "Budget threshold exceeded" : "Approved for fulfillment",
        }),
      });
      setMsg(`PO ${res.po_number} status updated to ${res.status}.`);
      loadProcurement();
    } catch (e: any) {
      setErr(e.message);
    }
  };

  const handleReceiveGRN = async (poId: string) => {
    setErr(null);
    setMsg(null);
    try {
      const res = await apiRequest("/goods-receipts", {
        method: "POST",
        body: JSON.stringify({ purchase_order_id: poId }),
      });
      setMsg(
        `GRN ${res.grn_number} posted! Inventory Weighted Average Cost updated and AP Journal Entry (${res.journal_entry_id.slice(0, 8)}) posted.`
      );
      loadProcurement();
    } catch (e: any) {
      setErr(e.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <ShoppingBag className="w-5 h-5 text-[#648BFF]" />
            Procurement, Supplier Quotations & Goods Receipt Workflow
          </h1>
          <p className="text-xs text-[#94A3B8]">
            PR → RFQ Comparison → Threshold Approval (&gt; LKR 50,000 = 2-Step) → PO → GRN → Inventory WAC & AP Journal
          </p>
        </div>
        <div className="flex items-center gap-2">
          {[
            { id: "pos", label: "Purchase Orders" },
            { id: "prs", label: "PRs & Quotations" },
            { id: "grns", label: "Goods Receipts (GRN)" },
            { id: "suppliers", label: "Suppliers" },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id as any)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium ${
                tab === t.id ? "bg-[#648BFF] text-white" : "glass-panel text-[#94A3B8]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {msg && (
        <div className="p-3 rounded-xl bg-[#20C997]/15 border border-[#20C997]/40 text-xs text-[#20C997]">
          {msg}
        </div>
      )}
      {err && (
        <div className="p-3 rounded-xl bg-[#F06464]/15 border border-[#F06464]/40 text-xs text-[#F06464]">
          {err}
        </div>
      )}

      {tab === "pos" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 glass-table-container rounded-2xl p-5 space-y-4">
            <h2 className="text-sm font-bold">Purchase Orders ({pos.length})</h2>
            <table className="w-full text-xs tabular-nums">
              <thead>
                <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                  <th className="py-2">PO Number</th>
                  <th className="py-2">Supplier</th>
                  <th className="py-2 text-right">Total (LKR)</th>
                  <th className="py-2">Approval Tier</th>
                  <th className="py-2">Status</th>
                  <th className="py-2 text-right">Workflow Actions</th>
                </tr>
              </thead>
              <tbody>
                {pos.map((po) => (
                  <tr key={po.id} className="border-b border-white/5">
                    <td className="py-2.5 font-mono text-[#648BFF]">{po.po_number}</td>
                    <td className="py-2.5 font-medium">{po.supplier_name}</td>
                    <td className="py-2.5 text-right font-semibold">
                      {formatCurrency(po.total_amount)}
                    </td>
                    <td className="py-2.5 text-[#94A3B8]">
                      {po.approval_step_required === 2 ? "2-Step (>50K)" : "1-Step"}
                    </td>
                    <td className="py-2.5">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] ${
                          po.status === "RECEIVED" || po.status === "APPROVED"
                            ? "bg-[#20C997]/20 text-[#20C997]"
                            : po.status === "REJECTED"
                            ? "bg-[#F06464]/20 text-[#F06464]"
                            : "bg-[#F4B740]/20 text-[#F4B740]"
                        }`}
                      >
                        {po.status}
                      </span>
                    </td>
                    <td className="py-2.5 text-right space-x-1.5">
                      {po.status === "PENDING_APPROVAL" && hasPermission("purchase_orders.approve") && (
                        <>
                          <button
                            onClick={() => handleApprovePO(po.id, "APPROVE")}
                            className="px-2.5 py-1 rounded bg-[#20C997]/20 text-[#20C997] hover:bg-[#20C997]/30 text-[11px]"
                            title="Approve PO (Enforces Creator != Approver)"
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => handleApprovePO(po.id, "REJECT")}
                            className="px-2 py-1 rounded bg-[#F06464]/20 text-[#F06464] text-[11px]"
                          >
                            Reject
                          </button>
                        </>
                      )}
                      {po.status === "APPROVED" && hasPermission("goods_receipts.create") && (
                        <button
                          onClick={() => handleReceiveGRN(po.id)}
                          className="px-2.5 py-1 rounded bg-[#648BFF] text-white text-[11px] font-semibold"
                        >
                          Receive GRN
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {hasPermission("purchase_orders.create") && (
            <form onSubmit={handleCreatePO} className="lg:col-span-4 glass-panel rounded-2xl p-5 space-y-3">
              <h3 className="text-sm font-bold">Create Purchase Order</h3>
              <select
                value={poSupId}
                onChange={(e) => setPoSupId(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
              >
                {suppliers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.supplier_code} — {s.name}
                  </option>
                ))}
              </select>
              <select
                value={poProdId}
                onChange={(e) => setPoProdId(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
              >
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.sku} — {p.name}
                  </option>
                ))}
              </select>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  required
                  placeholder="Quantity"
                  value={poQty}
                  onChange={(e) => setPoQty(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
                />
                <input
                  type="number"
                  required
                  placeholder="Unit Price (LKR)"
                  value={poPrice}
                  onChange={(e) => setPoPrice(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
                />
              </div>
              <button
                type="submit"
                className="w-full py-2.5 rounded-xl bg-[#648BFF] text-white text-xs font-semibold"
              >
                Submit PO to Approval Engine
              </button>
            </form>
          )}
        </div>
      )}

      {tab === "prs" && (
        <div className="glass-table-container rounded-2xl p-5 space-y-4">
          <h2 className="text-sm font-bold">Purchase Requests & Supplier RFQ Comparison</h2>
          <table className="w-full text-xs tabular-nums">
            <thead>
              <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                <th className="py-2">PR Number</th>
                <th className="py-2">Justification</th>
                <th className="py-2">Required Date</th>
                <th className="py-2 text-right">Estimated Total</th>
                <th className="py-2">Selected RFQ Quotation</th>
                <th className="py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {prs.map((pr) => (
                <tr key={pr.id} className="border-b border-white/5">
                  <td className="py-2.5 font-mono text-[#648BFF]">{pr.pr_number}</td>
                  <td className="py-2.5 font-medium">{pr.justification}</td>
                  <td className="py-2.5">{formatDate(pr.required_date)}</td>
                  <td className="py-2.5 text-right">{formatCurrency(pr.estimated_total)}</td>
                  <td className="py-2.5 text-[#20C997]">
                    {pr.quotations?.[0]
                      ? `${pr.quotations[0].quotation_number} (${pr.quotations[0].supplier_name})`
                      : "Pending RFQ"}
                  </td>
                  <td className="py-2.5">{pr.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "grns" && (
        <div className="glass-table-container rounded-2xl p-5 space-y-4">
          <h2 className="text-sm font-bold">Posted Goods Receipt Notes (GRNs)</h2>
          <table className="w-full text-xs tabular-nums">
            <thead>
              <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                <th className="py-2">GRN Number</th>
                <th className="py-2">PO Reference</th>
                <th className="py-2">Supplier</th>
                <th className="py-2">Warehouse</th>
                <th className="py-2">Received Date</th>
                <th className="py-2 text-right">Received Valuation</th>
              </tr>
            </thead>
            <tbody>
              {grns.map((g) => (
                <tr key={g.id} className="border-b border-white/5">
                  <td className="py-2.5 font-mono text-[#20C997]">{g.grn_number}</td>
                  <td className="py-2.5 font-mono text-[#648BFF]">{g.po_number}</td>
                  <td className="py-2.5 font-medium">{g.supplier_name}</td>
                  <td className="py-2.5">{g.warehouse_name}</td>
                  <td className="py-2.5">{formatDate(g.received_date)}</td>
                  <td className="py-2.5 text-right font-semibold">
                    {formatCurrency(g.total_received_value)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "suppliers" && (
        <div className="glass-table-container rounded-2xl p-5 space-y-4">
          <h2 className="text-sm font-bold">Registered Enterprise Suppliers ({suppliers.length})</h2>
          <table className="w-full text-xs tabular-nums">
            <thead>
              <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                <th className="py-2">Code</th>
                <th className="py-2">Supplier Name</th>
                <th className="py-2">Contact Person</th>
                <th className="py-2">Terms</th>
                <th className="py-2 text-right">On-Time Delivery</th>
                <th className="py-2 text-right">Rating</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map((s) => (
                <tr key={s.id} className="border-b border-white/5">
                  <td className="py-2.5 font-mono text-[#648BFF]">{s.supplier_code}</td>
                  <td className="py-2.5 font-medium">{s.name}</td>
                  <td className="py-2.5">{s.contact_person}</td>
                  <td className="py-2.5">{s.payment_terms_days} Days</td>
                  <td className="py-2.5 text-right text-[#20C997]">{s.on_time_delivery_rate}%</td>
                  <td className="py-2.5 text-right font-bold text-[#F4B740]">{s.rating}/5.0</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
