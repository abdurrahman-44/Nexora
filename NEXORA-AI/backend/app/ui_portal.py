"""NEXORA ERP — Full-Featured Glassmorphism Enterprise Web Application Portal Served at /."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(include_in_schema=False)

NEXORA_PORTAL_HTML = r"""<!doctype html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>NEXORA ERP — AI-Powered Enterprise Resource Planning Platform</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
  <style>
    :root {
      --bg-main: #080D18;
      --bg-secondary: #101827;
      --surface-primary: #141F31;
      --surface-glass: rgba(255, 255, 255, 0.055);
      --border-glass: rgba(255, 255, 255, 0.10);
      --text-main: #F5F7FC;
      --text-muted: #94A3B8;
    }
    html.light {
      --bg-main: #F4F7FC;
      --bg-secondary: #FFFFFF;
      --surface-primary: #FFFFFF;
      --surface-glass: rgba(255, 255, 255, 0.85);
      --border-glass: rgba(15, 23, 42, 0.10);
      --text-main: #172033;
      --text-muted: #667085;
    }
    body {
      background-color: var(--bg-main);
      color: var(--text-main);
      font-family: 'Inter', system-ui, sans-serif;
      transition: background-color 0.2s ease, color 0.2s ease;
    }
    .glass-panel {
      background: var(--surface-glass);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid var(--border-glass);
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.16);
    }
    .glass-sidebar {
      background: rgba(15, 23, 42, 0.84);
      backdrop-filter: blur(24px);
      border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    html.light .glass-sidebar {
      background: rgba(255, 255, 255, 0.90);
      border-right: 1px solid rgba(15, 23, 42, 0.08);
    }
    .glass-table {
      background: rgba(20, 31, 49, 0.86);
      backdrop-filter: blur(16px);
      border: 1px solid var(--border-glass);
    }
    html.light .glass-table {
      background: rgba(255, 255, 255, 0.95);
      border: 1px solid rgba(15, 23, 42, 0.09);
    }
    .tabular-nums { font-variant-numeric: tabular-nums; }
  </style>
</head>
<body class="min-h-screen">
  <div id="root"></div>
  <script type="text/babel">
    const { useState, useEffect } = React;

    const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    const fmtLKR = (n, cur = "LKR") => `${cur} ` + Number(n || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const fmtDate = (s) => {
      if (!s) return "—";
      const d = new Date(s);
      if (isNaN(d.getTime())) return String(s);
      return `${String(d.getDate()).padStart(2, "0")} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
    };

    const NAV_GROUPS = [
      { title: "OVERVIEW", items: [{ id: "dashboard", label: "Executive Dashboard", perm: "dashboard.view" }] },
      { title: "ORGANIZATION", items: [
        { id: "organization", label: "Organization Profile", perm: "organizations.view" },
        { id: "branches", label: "Branches", perm: "organizations.view" },
        { id: "departments", label: "Departments", perm: "organizations.view" },
      ]},
      { title: "PEOPLE (HR)", items: [
        { id: "employees", label: "Employees Directory", perm: "employees.view" },
        { id: "attendance", label: "Attendance Logs", perm: "employees.view" },
        { id: "leave", label: "Leave Management", perm: "leave.view" },
        { id: "performance", label: "Performance Reviews", perm: "employees.view" },
      ]},
      { title: "OPERATIONS", items: [
        { id: "inventory", label: "Inventory & WAC", perm: "inventory.view" },
        { id: "warehouses", label: "Warehouses", perm: "inventory.view" },
        { id: "procurement", label: "Procurement & POs", perm: "procurement.view" },
        { id: "suppliers", label: "Suppliers", perm: "procurement.view" },
        { id: "sales", label: "Sales Orders", perm: "sales.view" },
        { id: "customers", label: "Customers", perm: "sales.view" },
      ]},
      { title: "FINANCIALS", items: [
        { id: "accounting", label: "Journal Entries (GL)", perm: "finance.view" },
        { id: "invoices", label: "Tax Invoices", perm: "invoices.view" },
        { id: "payments", label: "Payments & Receipts", perm: "payments.view" },
        { id: "expenses", label: "Expenses", perm: "expenses.create" },
        { id: "financial-reports", label: "Trial Balance, P&L, BS", perm: "finance.reports.view" },
      ]},
      { title: "MANAGEMENT", items: [
        { id: "projects", label: "Projects & Kanban", perm: "projects.view" },
        { id: "approvals", label: "Approval Center", perm: "approvals.view" },
      ]},
      { title: "INTELLIGENCE (AI)", items: [
        { id: "demand-forecast", label: "Demand Forecasting", perm: "ai.forecast.view" },
        { id: "sales-forecast", label: "Sales Forecasting", perm: "ai.forecast.view" },
        { id: "anomaly-detection", label: "Anomaly Detection", perm: "ai.anomalies.view" },
        { id: "ai-copilot", label: "Nexora AI Copilot", perm: "ai.copilot.use" },
      ]},
      { title: "SYSTEM", items: [
        { id: "reports", label: "BI Reports & Export", perm: "reports.view" },
        { id: "audit-logs", label: "Security Audit Logs", perm: "audit_logs.view" },
        { id: "users-permissions", label: "Users & 12 Roles", perm: "users.view" },
      ]},
    ];

    function App() {
      const [token, setToken] = useState(sessionStorage.getItem("nexora_access_token"));
      const [orgId, setOrgId] = useState(sessionStorage.getItem("nexora_org_id"));
      const [user, setUser] = useState(null);
      const [theme, setTheme] = useState(localStorage.getItem("nexora_theme") || "dark");
      const [route, setRoute] = useState("dashboard");
      const [email, setEmail] = useState("admin@nexora.lk");
      const [password, setPassword] = useState("Nexora#2026");
      const [demoAccounts, setDemoAccounts] = useState([]);
      const [banner, setBanner] = useState(null);
      const [errBanner, setErrBanner] = useState(null);

      // Module data states
      const [dashboard, setDashboard] = useState(null);
      const [orgDetails, setOrgDetails] = useState(null);
      const [employees, setEmployees] = useState([]);
      const [attendance, setAttendance] = useState([]);
      const [leaves, setLeaves] = useState([]);
      const [reviews, setReviews] = useState([]);
      const [products, setProducts] = useState([]);
      const [warehouses, setWarehouses] = useState([]);
      const [movements, setMovements] = useState([]);
      const [pos, setPos] = useState([]);
      const [suppliers, setSuppliers] = useState([]);
      const [customers, setCustomers] = useState([]);
      const [salesOrders, setSalesOrders] = useState([]);
      const [invoices, setInvoices] = useState([]);
      const [payments, setPayments] = useState([]);
      const [expenses, setExpenses] = useState([]);
      const [journals, setJournals] = useState([]);
      const [trialBalance, setTrialBalance] = useState(null);
      const [pnl, setPnl] = useState(null);
      const [balanceSheet, setBalanceSheet] = useState(null);
      const [projects, setProjects] = useState([]);
      const [tasks, setTasks] = useState([]);
      const [approvals, setApprovals] = useState([]);
      const [demandFc, setDemandFc] = useState(null);
      const [salesFc, setSalesFc] = useState(null);
      const [anomalies, setAnomalies] = useState(null);
      const [copilotQ, setCopilotQ] = useState("");
      const [copilotMsgs, setCopilotMsgs] = useState([]);
      const [auditLogs, setAuditLogs] = useState([]);
      const [usersList, setUsersList] = useState([]);
      const [rolesList, setRolesList] = useState([]);
      const [biReport, setBiReport] = useState(null);

      // Interactive form states
      const [newProdSku, setNewProdSku] = useState("");
      const [newProdName, setNewProdName] = useState("");
      const [newProdCost, setNewProdCost] = useState("45000");
      const [newProdSell, setNewProdSell] = useState("65000");
      const [newProdQty, setNewProdQty] = useState("20");

      useEffect(() => {
        document.documentElement.className = theme;
        localStorage.setItem("nexora_theme", theme);
      }, [theme]);

      useEffect(() => {
        fetch("/api/v1/auth/demo-accounts").then(r => r.json()).then(d => setDemoAccounts(d.accounts || [])).catch(() => {});
      }, []);

      const api = async (path, opts = {}) => {
        const headers = { ...(opts.headers || {}) };
        if (opts.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
        if (token) headers["Authorization"] = `Bearer ${token}`;
        if (orgId) headers["X-Organization-ID"] = orgId;
        const r = await fetch(`/api/v1${path}`, { ...opts, headers });
        const d = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(d?.error?.message || `Error ${r.status}`);
        return d;
      };

      const loadRouteData = async (activeRoute) => {
        if (!token) return;
        setErrBanner(null);
        try {
          if (activeRoute === "dashboard") {
            setDashboard(await api("/analytics/dashboard"));
          } else if (["organization","branches","departments"].includes(activeRoute)) {
            if (user) setOrgDetails(await api(`/organizations/${orgId || user.organization_id}`));
          } else if (activeRoute === "employees") {
            const r = await api("/employees"); setEmployees(r.items || []);
          } else if (activeRoute === "attendance") {
            const r = await api("/hr/attendance"); setAttendance(r.items || []);
          } else if (activeRoute === "leave") {
            const r = await api("/leave-requests"); setLeaves(r.items || []);
          } else if (activeRoute === "performance") {
            const r = await api("/hr/performance"); setReviews(r.items || []);
          } else if (activeRoute === "inventory") {
            const [p, w, m] = await Promise.all([api("/inventory/products"), api("/inventory/warehouses"), api("/inventory/movements")]);
            setProducts(p.items || []); setWarehouses(w.items || []); setMovements(m.items || []);
          } else if (activeRoute === "warehouses") {
            const w = await api("/inventory/warehouses"); setWarehouses(w.items || []);
          } else if (activeRoute === "procurement") {
            const [po, s, p] = await Promise.all([api("/purchase-orders"), api("/suppliers"), api("/inventory/products")]);
            setPos(po.items || []); setSuppliers(s.items || []); setProducts(p.items || []);
          } else if (activeRoute === "suppliers") {
            const s = await api("/suppliers"); setSuppliers(s.items || []);
          } else if (activeRoute === "sales") {
            const o = await api("/sales/orders"); setSalesOrders(o.items || []);
          } else if (activeRoute === "customers") {
            const c = await api("/customers"); setCustomers(c.items || []);
          } else if (activeRoute === "invoices") {
            const [inv, c, p] = await Promise.all([api("/invoices"), api("/customers"), api("/inventory/products")]);
            setInvoices(inv.items || []); setCustomers(c.items || []); setProducts(p.items || []);
          } else if (activeRoute === "payments") {
            const pay = await api("/payments"); setPayments(pay.items || []);
          } else if (activeRoute === "expenses") {
            const ex = await api("/finance/expenses"); setExpenses(ex.items || []);
          } else if (activeRoute === "accounting") {
            const j = await api("/finance/journal-entries"); setJournals(j.items || []);
          } else if (activeRoute === "financial-reports") {
            const [tb, pl, bs] = await Promise.all([api("/finance/trial-balance"), api("/finance/profit-loss"), api("/finance/balance-sheet")]);
            setTrialBalance(tb); setPnl(pl); setBalanceSheet(bs);
          } else if (activeRoute === "projects") {
            const [pr, tk] = await Promise.all([api("/projects"), api("/tasks")]);
            setProjects(pr.items || []); setTasks(tk.items || []);
          } else if (activeRoute === "approvals") {
            const ap = await api("/workflows/approvals"); setApprovals(ap.items || []);
          } else if (activeRoute === "demand-forecast") {
            setDemandFc(await api("/ai/forecast/inventory", { method: "POST", body: JSON.stringify({ model_choice: "XGBOOST" }) }));
          } else if (activeRoute === "sales-forecast") {
            setSalesFc(await api("/ai/forecast/sales", { method: "POST", body: JSON.stringify({ horizon_months: 6 }) }));
          } else if (activeRoute === "anomaly-detection") {
            setAnomalies(await api("/ai/anomalies/analyze", { method: "POST" }));
          } else if (activeRoute === "reports") {
            setBiReport(await api("/analytics/reports/trial-balance"));
          } else if (activeRoute === "audit-logs") {
            const al = await api("/audit-logs"); setAuditLogs(al.items || []);
          } else if (activeRoute === "users-permissions") {
            const [ul, rl] = await Promise.all([api("/users"), api("/roles")]);
            setUsersList(ul.items || []); setRolesList(rl.items || []);
          }
        } catch (err) {
          setErrBanner(err.message);
        }
      };

      useEffect(() => {
        if (token) {
          api("/auth/me")
            .then(u => { setUser(u); if (!orgId) setOrgId(u.organization_id); })
            .catch(() => { setToken(null); sessionStorage.removeItem("nexora_access_token"); });
        }
      }, [token, orgId]);

      useEffect(() => {
        if (token && user) loadRouteData(route);
      }, [route, token, user, orgId]);

      const handleLogin = async (e) => {
        e.preventDefault();
        setErrBanner(null);
        try {
          const d = await api("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
          sessionStorage.setItem("nexora_access_token", d.access_token);
          sessionStorage.setItem("nexora_org_id", d.user.organization_id);
          setOrgId(d.user.organization_id);
          setToken(d.access_token);
          setUser(d.user);
        } catch (err) {
          setErrBanner(err.message);
        }
      };

      if (!token || !user) {
        return (
          <div className="min-h-screen flex items-center justify-center p-6 relative overflow-hidden">
            <div className="max-w-5xl w-full grid grid-cols-1 lg:grid-cols-12 gap-8 items-center z-10">
              <div className="lg:col-span-7 space-y-5">
                <span className="inline-block px-3.5 py-1.5 rounded-full glass-panel text-xs text-[#648BFF] font-semibold">
                  NEXORA ERP • AI-Powered Enterprise Resource Planning Platform
                </span>
                <h1 className="text-3xl sm:text-4xl font-extrabold leading-tight">
                  One intelligent platform.{" "}
                  <span className="bg-gradient-to-r from-[#648BFF] via-[#8B7CFF] to-[#20C997] bg-clip-text text-transparent">
                    Every business operation.
                  </span>{" "}
                  Better decisions.
                </h1>
                <p className="text-xs text-[#94A3B8] leading-relaxed">
                  Pre-populated with <strong className="text-white">Nexora Demo Holdings</strong> (LKR • Asia/Colombo • DD MMM YYYY): 4 branches, 8 departments, 35 employees, 50 SKUs across 3 warehouses, double-entry General Ledger, threshold approvals, and ML forecasting.
                </p>
                <div className="glass-panel rounded-2xl p-4 space-y-2.5">
                  <div className="text-xs font-bold text-[#20C997]">Click Any Role to Auto-Fill Credentials (Password: Nexora#2026)</div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-64 overflow-y-auto pr-1">
                    {demoAccounts.map(acc => (
                      <button key={acc.email} type="button"
                        onClick={() => { setEmail(acc.email); setPassword("Nexora#2026"); setErrBanner(null); }}
                        className={`p-2.5 rounded-xl border text-left text-xs transition flex items-center justify-between ${
                          email === acc.email ? "bg-[#648BFF]/25 border-[#648BFF] text-white" : "bg-white/5 border-white/10 hover:bg-white/10"
                        }`}>
                        <div className="truncate">
                          <div className="font-bold truncate">{acc.full_name}</div>
                          <div className="font-mono text-[11px] text-[#648BFF]">{acc.email}</div>
                        </div>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-white/10 ml-2 shrink-0">{acc.roles?.[0]}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <form onSubmit={handleLogin} className="lg:col-span-5 glass-panel rounded-3xl p-8 space-y-5">
                <div>
                  <h2 className="text-lg font-bold">Sign in to NEXORA ERP</h2>
                  <p className="text-xs text-[#94A3B8]">Argon2id • JWT + HttpOnly Refresh Rotation • Granular RBAC</p>
                </div>
                {errBanner && <div className="p-3 rounded-xl bg-red-500/20 border border-red-500/40 text-red-300 text-xs">{errBanner}</div>}
                <div>
                  <label className="block text-xs text-[#94A3B8] mb-1">Corporate Email</label>
                  <input value={email} onChange={e => setEmail(e.target.value)} className="w-full px-3.5 py-2.5 rounded-xl bg-[#141F31] text-white border border-white/10 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-[#94A3B8] mb-1">Password</label>
                  <input type="password" value={password} onChange={e => setPassword(e.target.value)} className="w-full px-3.5 py-2.5 rounded-xl bg-[#141F31] text-white border border-white/10 text-sm" />
                </div>
                <button type="submit" className="w-full py-3 rounded-xl bg-gradient-to-r from-[#648BFF] to-[#8B7CFF] text-white font-semibold text-sm shadow-lg shadow-[#648BFF]/30">
                  Access Enterprise Workspace
                </button>
              </form>
            </div>
          </div>
        );
      }

      const kpis = dashboard?.kpis || {};
      const trends = dashboard?.charts?.monthly_trends || [];

      return (
        <div className="min-h-screen flex">
          {/* Glass Sidebar */}
          <aside className="w-64 glass-sidebar flex flex-col justify-between h-screen sticky top-0 shrink-0">
            <div className="p-4 border-b border-white/10 flex items-center justify-between">
              <div>
                <div className="font-extrabold text-sm tracking-wider">NEXORA <span className="text-[#648BFF]">ERP</span></div>
                <div className="text-[10px] text-[#94A3B8]">{user.organization_name}</div>
              </div>
              <span className="px-2 py-0.5 rounded bg-[#648BFF]/20 text-[#648BFF] text-[10px] font-mono">{user.currency}</span>
            </div>

            <div className="flex-1 overflow-y-auto p-2.5 space-y-3">
              {NAV_GROUPS.map(g => (
                <div key={g.title}>
                  <div className="px-2.5 mb-1 text-[10px] font-bold tracking-widest text-[#94A3B8]">{g.title}</div>
                  <div className="space-y-0.5">
                    {g.items.map(it => (
                      <button key={it.id} onClick={() => { setBanner(null); setRoute(it.id); }}
                        className={`w-full text-left px-3 py-1.5 rounded-xl text-xs font-medium transition ${
                          route === it.id ? "bg-gradient-to-r from-[#648BFF]/30 to-[#8B7CFF]/20 text-white border border-[#648BFF]/40" : "text-[#94A3B8] hover:text-white hover:bg-white/5"
                        }`}>
                        {it.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="p-3 border-t border-white/10 space-y-2">
              <div className="text-xs font-semibold truncate">{user.full_name}</div>
              <div className="text-[10px] text-[#648BFF] font-mono">{user.roles?.join(", ")}</div>
              <button onClick={() => { sessionStorage.clear(); setToken(null); setUser(null); }}
                className="w-full py-1.5 rounded-xl bg-red-500/15 hover:bg-red-500/25 text-red-400 text-xs font-semibold">
                Sign Out
              </button>
            </div>
          </aside>

          {/* Main Area */}
          <div className="flex-1 flex flex-col min-w-0">
            <header className="h-14 px-6 glass-panel border-b border-white/10 flex items-center justify-between sticky top-0 z-20">
              <div className="text-xs flex items-center gap-2">
                <span className="text-[#94A3B8]">{user.organization_name}</span>
                <span>/</span>
                <span className="font-bold text-[#648BFF] uppercase">{route.replace("-", " ")}</span>
              </div>
              <div className="flex items-center gap-3">
                {user.organizations?.length > 1 && (
                  <select value={orgId || user.organization_id}
                    onChange={e => { sessionStorage.setItem("nexora_org_id", e.target.value); setOrgId(e.target.value); }}
                    className="px-2.5 py-1 rounded-xl bg-[#141F31] text-white border border-white/10 text-xs">
                    {user.organizations.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
                  </select>
                )}
                <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                  className="px-3 py-1 rounded-xl glass-panel text-xs">
                  Theme: {theme.toUpperCase()}
                </button>
                <a href="/docs" target="_blank" className="px-3 py-1 rounded-xl bg-[#648BFF]/20 text-[#648BFF] text-xs font-semibold">
                  OpenAPI Docs ↗
                </a>
              </div>
            </header>

            <main className="p-6 space-y-6">
              {banner && <div className="p-3 rounded-xl bg-[#20C997]/20 border border-[#20C997]/40 text-[#20C997] text-xs">{banner}</div>}
              {errBanner && <div className="p-3 rounded-xl bg-red-500/20 border border-red-500/40 text-red-400 text-xs">{errBanner}</div>}

              {/* DASHBOARD */}
              {route === "dashboard" && (
                <div className="space-y-6">
                  <div>
                    <h1 className="text-2xl font-bold">Executive Command Center</h1>
                    <p className="text-xs text-[#94A3B8]">Live KPIs calculated directly from posted General Ledger lines & warehouse stock balances ({user.currency} • {user.timezone})</p>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 tabular-nums">
                    {[
                      ["Total Posted Revenue", fmtLKR(kpis.total_revenue), "text-[#20C997]", "financial-reports"],
                      ["Total Expenses", fmtLKR(kpis.total_expenses), "text-[#F4B740]", "expenses"],
                      ["Net Profit", fmtLKR(kpis.net_profit), "text-[#20C997]", "financial-reports"],
                      ["Receivables (AR)", fmtLKR(kpis.outstanding_receivables), "text-[#648BFF]", "invoices"],
                      ["Payables (AP)", fmtLKR(kpis.outstanding_payables), "text-[#8B7CFF]", "procurement"],
                      ["Inventory Valuation (WAC)", fmtLKR(kpis.inventory_valuation), "text-[#648BFF]", "inventory"],
                      ["Low-Stock SKUs", String(kpis.low_stock_products ?? 0), "text-[#F06464]", "demand-forecast"],
                      ["Pending Approvals", String(kpis.pending_approvals ?? 0), "text-[#F4B740]", "approvals"],
                      ["Active Workforce", String(kpis.total_employees ?? 0), "text-[#20C997]", "employees"],
                      ["Active Projects", String(kpis.active_projects ?? 0), "text-[#8B7CFF]", "projects"],
                    ].map(([label, val, col, target]) => (
                      <button key={label} onClick={() => setRoute(target)} className="glass-panel p-4 rounded-2xl text-left hover:border-[#648BFF] transition">
                        <div className="text-xs text-[#94A3B8]">{label}</div>
                        <div className={`text-lg font-bold mt-1.5 ${col}`}>{val}</div>
                      </button>
                    ))}
                  </div>

                  <div className="glass-table rounded-2xl p-5">
                    <h2 className="text-sm font-bold mb-3">6-Month Revenue vs. Expenses & Net Cash Flow</h2>
                    <table className="w-full text-xs tabular-nums">
                      <thead>
                        <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                          <th className="py-2">Period</th>
                          <th className="py-2 text-right">Invoiced Revenue</th>
                          <th className="py-2 text-right">Operating Expenses</th>
                          <th className="py-2 text-right">Purchase Orders</th>
                          <th className="py-2 text-right">Net Cash Flow</th>
                        </tr>
                      </thead>
                      <tbody>
                        {trends.map(t => (
                          <tr key={t.month} className="border-b border-white/5">
                            <td className="py-2 font-semibold">{t.month}</td>
                            <td className="py-2 text-right text-[#648BFF]">{fmtLKR(t.revenue)}</td>
                            <td className="py-2 text-right text-[#F4B740]">{fmtLKR(t.expenses)}</td>
                            <td className="py-2 text-right text-[#8B7CFF]">{fmtLKR(t.purchases)}</td>
                            <td className="py-2 text-right font-bold text-[#20C997]">{fmtLKR(t.cash_flow)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* ORGANIZATION / BRANCHES / DEPARTMENTS */}
              {["organization","branches","departments"].includes(route) && orgDetails && (
                <div className="space-y-6">
                  <div className="glass-panel p-5 rounded-2xl">
                    <h2 className="text-lg font-bold">{orgDetails.name} ({orgDetails.code})</h2>
                    <p className="text-xs text-[#94A3B8] mt-1">{orgDetails.address} • Reg: {orgDetails.registration_number} • Tax ID: {orgDetails.tax_id}</p>
                  </div>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="glass-table p-5 rounded-2xl">
                      <h3 className="text-sm font-bold mb-3">Branches ({orgDetails.branches?.length || 0})</h3>
                      <table className="w-full text-xs">
                        <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">Code</th><th className="py-2">Name</th><th className="py-2">City</th><th className="py-2">Manager</th></tr></thead>
                        <tbody>
                          {(orgDetails.branches || []).map(b => (
                            <tr key={b.id} className="border-b border-white/5"><td className="py-2 font-mono text-[#648BFF]">{b.code}</td><td className="py-2">{b.name}</td><td className="py-2">{b.city}</td><td className="py-2">{b.manager_name}</td></tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="glass-table p-5 rounded-2xl">
                      <h3 className="text-sm font-bold mb-3">Departments ({orgDetails.departments?.length || 0})</h3>
                      <table className="w-full text-xs tabular-nums">
                        <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">Code</th><th className="py-2">Department</th><th className="py-2 text-right">Allocated Budget</th></tr></thead>
                        <tbody>
                          {(orgDetails.departments || []).map(d => (
                            <tr key={d.id} className="border-b border-white/5"><td className="py-2 font-mono text-[#8B7CFF]">{d.code}</td><td className="py-2">{d.name}</td><td className="py-2 text-right text-[#20C997]">{fmtLKR(d.budget_allocated)}</td></tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {/* EMPLOYEES */}
              {route === "employees" && (
                <div className="glass-table p-5 rounded-2xl space-y-3">
                  <h2 className="text-base font-bold">Employee Directory ({employees.length})</h2>
                  <table className="w-full text-xs tabular-nums">
                    <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">Code</th><th className="py-2">Full Name</th><th className="py-2">Department</th><th className="py-2">Designation</th><th className="py-2">Branch</th><th className="py-2 text-right">Base Salary</th></tr></thead>
                    <tbody>
                      {employees.map(e => (
                        <tr key={e.id} className="border-b border-white/5">
                          <td className="py-2 font-mono text-[#648BFF]">{e.employee_code}</td>
                          <td className="py-2 font-medium">{e.full_name}</td>
                          <td className="py-2">{e.department_name}</td>
                          <td className="py-2 text-[#94A3B8]">{e.designation_title}</td>
                          <td className="py-2">{e.branch_name}</td>
                          <td className="py-2 text-right text-[#20C997]">{e.base_salary ? fmtLKR(e.base_salary) : "🔒 Redacted"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* ATTENDANCE */}
              {route === "attendance" && (
                <div className="glass-table p-5 rounded-2xl space-y-3">
                  <h2 className="text-base font-bold">Attendance Records ({attendance.length})</h2>
                  <table className="w-full text-xs tabular-nums">
                    <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">Date</th><th className="py-2">Code</th><th className="py-2">Employee</th><th className="py-2">Check-In</th><th className="py-2">Check-Out</th><th className="py-2">Status</th></tr></thead>
                    <tbody>
                      {attendance.map(a => (
                        <tr key={a.id} className="border-b border-white/5"><td className="py-2">{fmtDate(a.attendance_date)}</td><td className="py-2 font-mono text-[#648BFF]">{a.employee_code}</td><td className="py-2">{a.employee_name}</td><td className="py-2">{a.check_in}</td><td className="py-2">{a.check_out}</td><td className="py-2 text-[#20C997]">{a.status}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* LEAVE */}
              {route === "leave" && (
                <div className="glass-table p-5 rounded-2xl space-y-3">
                  <h2 className="text-base font-bold">Leave Requests & Approvals</h2>
                  <table className="w-full text-xs">
                    <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">Employee</th><th className="py-2">Leave Type</th><th className="py-2">Dates</th><th className="py-2">Days</th><th className="py-2">Status</th></tr></thead>
                    <tbody>
                      {leaves.map(l => (
                        <tr key={l.id} className="border-b border-white/5"><td className="py-2 font-medium">{l.employee_name}</td><td className="py-2">{l.leave_type}</td><td className="py-2">{fmtDate(l.start_date)} → {fmtDate(l.end_date)}</td><td className="py-2">{l.days_count}</td><td className="py-2 font-bold text-[#648BFF]">{l.status}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* PERFORMANCE */}
              {route === "performance" && (
                <div className="glass-table p-5 rounded-2xl space-y-3">
                  <h2 className="text-base font-bold">Employee Performance Evaluations</h2>
                  <table className="w-full text-xs">
                    <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">Employee</th><th className="py-2">Period</th><th className="py-2">KPI Score</th><th className="py-2">Competency</th><th className="py-2">Rating</th></tr></thead>
                    <tbody>
                      {reviews.map(r => (
                        <tr key={r.id} className="border-b border-white/5"><td className="py-2 font-medium">{r.employee_name}</td><td className="py-2">{r.review_period}</td><td className="py-2 text-[#648BFF] font-bold">{r.kpi_score}/5.0</td><td className="py-2 text-[#8B7CFF] font-bold">{r.competency_score}/5.0</td><td className="py-2 text-[#20C997]">{r.overall_rating}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* INVENTORY */}
              {route === "inventory" && (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                  <div className="lg:col-span-9 glass-table p-5 rounded-2xl space-y-3">
                    <h2 className="text-base font-bold">Product Catalogue & Weighted Average Cost Valuation ({products.length} SKUs)</h2>
                    <div className="max-h-[500px] overflow-y-auto">
                      <table className="w-full text-xs tabular-nums">
                        <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">SKU</th><th className="py-2">Product</th><th className="py-2 text-right">Available</th><th className="py-2 text-right">WAC Cost</th><th className="py-2 text-right">Sell Price</th><th className="py-2 text-right">Valuation</th></tr></thead>
                        <tbody>
                          {products.map(p => (
                            <tr key={p.id} className="border-b border-white/5">
                              <td className="py-2 font-mono text-[#648BFF]">{p.sku}</td>
                              <td className="py-2 font-medium">{p.name}</td>
                              <td className={`py-2 text-right font-bold ${p.is_low_stock ? "text-[#F06464]" : "text-[#20C997]"}`}>{p.quantity_available} {p.uom}</td>
                              <td className="py-2 text-right">{fmtLKR(p.weighted_avg_cost)}</td>
                              <td className="py-2 text-right">{fmtLKR(p.selling_price)}</td>
                              <td className="py-2 text-right font-semibold">{fmtLKR(p.total_valuation)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                  <form onSubmit={async e => {
                    e.preventDefault();
                    await api("/inventory/products", { method: "POST", body: JSON.stringify({ sku: newProdSku, name: newProdName, cost_price: Number(newProdCost), selling_price: Number(newProdSell), initial_stock: Number(newProdQty) }) });
                    setNewProdSku(""); setNewProdName(""); setBanner("Product created with opening stock!"); loadRouteData("inventory");
                  }} className="lg:col-span-3 glass-panel p-5 rounded-2xl space-y-3 h-fit">
                    <h3 className="text-sm font-bold">+ Register New SKU</h3>
                    <input required placeholder="SKU (e.g. NEX-AI-900)" value={newProdSku} onChange={e => setNewProdSku(e.target.value)} className="w-full px-3 py-2 rounded-xl bg-[#141F31] text-white border border-white/10 text-xs" />
                    <input required placeholder="Product Name" value={newProdName} onChange={e => setNewProdName(e.target.value)} className="w-full px-3 py-2 rounded-xl bg-[#141F31] text-white border border-white/10 text-xs" />
                    <input type="number" required placeholder="Cost (LKR)" value={newProdCost} onChange={e => setNewProdCost(e.target.value)} className="w-full px-3 py-2 rounded-xl bg-[#141F31] text-white border border-white/10 text-xs" />
                    <input type="number" required placeholder="Selling Price (LKR)" value={newProdSell} onChange={e => setNewProdSell(e.target.value)} className="w-full px-3 py-2 rounded-xl bg-[#141F31] text-white border border-white/10 text-xs" />
                    <input type="number" required placeholder="Opening Stock" value={newProdQty} onChange={e => setNewProdQty(e.target.value)} className="w-full px-3 py-2 rounded-xl bg-[#141F31] text-white border border-white/10 text-xs" />
                    <button type="submit" className="w-full py-2 rounded-xl bg-[#648BFF] text-white text-xs font-semibold">Create Product</button>
                  </form>
                </div>
              )}

              {/* WAREHOUSES */}
              {route === "warehouses" && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                  {warehouses.map(w => (
                    <div key={w.id} className="glass-panel p-5 rounded-2xl space-y-2">
                      <div className="flex justify-between text-xs"><span className="font-mono text-[#648BFF]">{w.code}</span><span className="text-[#20C997]">{w.utilization_percent}% Utilized</span></div>
                      <h3 className="text-base font-bold">{w.name}</h3>
                      <div className="text-xs text-[#94A3B8]">Manager: {w.manager_name} • {w.sku_count} SKUs</div>
                      <div className="text-sm font-bold text-[#648BFF] pt-2 border-t border-white/10">{fmtLKR(w.total_valuation)}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* PROCUREMENT */}
              {route === "procurement" && (
                <div className="glass-table p-5 rounded-2xl space-y-3">
                  <h2 className="text-base font-bold">Purchase Orders & Multi-Step Approval / GRN Workflow ({pos.length})</h2>
                  <table className="w-full text-xs tabular-nums">
                    <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">PO Number</th><th className="py-2">Supplier</th><th className="py-2 text-right">Total (LKR)</th><th className="py-2">Approval Tier</th><th className="py-2">Status</th><th className="py-2 text-right">Actions</th></tr></thead>
                    <tbody>
                      {pos.map(po => (
                        <tr key={po.id} className="border-b border-white/5">
                          <td className="py-2 font-mono text-[#648BFF]">{po.po_number}</td>
                          <td className="py-2 font-medium">{po.supplier_name}</td>
                          <td className="py-2 text-right font-bold">{fmtLKR(po.total_amount)}</td>
                          <td className="py-2">{po.approval_step_required}-Step</td>
                          <td className="py-2 text-[#20C997] font-semibold">{po.status}</td>
                          <td className="py-2 text-right space-x-1.5">
                            {po.status === "PENDING_APPROVAL" && (
                              <button onClick={async () => {
                                try { await api(`/purchase-orders/${po.id}/approve`, { method: "POST", body: JSON.stringify({ action: "APPROVE" }) }); setBanner(`Approved ${po.po_number}`); loadRouteData("procurement"); } catch (e) { setErrBanner(e.message); }
                              }} className="px-2.5 py-1 rounded bg-[#20C997]/20 text-[#20C997]">Approve</button>
                            )}
                            {po.status === "APPROVED" && (
                              <button onClick={async () => {
                                try { await api("/goods-receipts", { method: "POST", body: JSON.stringify({ purchase_order_id: po.id }) }); setBanner(`Posted GRN & AP Journal for ${po.po_number}`); loadRouteData("procurement"); } catch (e) { setErrBanner(e.message); }
                              }} className="px-2.5 py-1 rounded bg-[#648BFF] text-white">Receive GRN</button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* SUPPLIERS */}
              {route === "suppliers" && (
                <div className="glass-table p-5 rounded-2xl">
                  <h2 className="text-base font-bold mb-3">Registered Suppliers ({suppliers.length})</h2>
                  <table className="w-full text-xs">
                    <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">Code</th><th className="py-2">Supplier</th><th className="py-2">Contact</th><th className="py-2">On-Time Delivery</th><th className="py-2">Rating</th></tr></thead>
                    <tbody>
                      {suppliers.map(s => (
                        <tr key={s.id} className="border-b border-white/5"><td className="py-2 font-mono text-[#648BFF]">{s.supplier_code}</td><td className="py-2 font-medium">{s.name}</td><td className="py-2">{s.contact_person}</td><td className="py-2 text-[#20C997]">{s.on_time_delivery_rate}%</td><td className="py-2 font-bold text-[#F4B740]">{s.rating}/5.0</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* SALES ORDERS & CUSTOMERS */}
              {route === "sales" && (
                <div className="glass-table p-5 rounded-2xl">
                  <h2 className="text-base font-bold mb-3">Sales Orders ({salesOrders.length})</h2>
                  <table className="w-full text-xs tabular-nums">
                    <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">SO #</th><th className="py-2">Customer</th><th className="py-2">Date</th><th className="py-2 text-right">Total (LKR)</th><th className="py-2">Status</th></tr></thead>
                    <tbody>
                      {salesOrders.map(so => (
                        <tr key={so.id} className="border-b border-white/5"><td className="py-2 font-mono text-[#648BFF]">{so.so_number}</td><td className="py-2 font-medium">{so.customer_name}</td><td className="py-2">{fmtDate(so.order_date)}</td><td className="py-2 text-right font-bold">{fmtLKR(so.total_amount)}</td><td className="py-2 text-[#20C997]">{so.status}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {route === "customers" && (
                <div className="glass-table p-5 rounded-2xl">
                  <h2 className="text-base font-bold mb-3">Corporate & Retail Customers ({customers.length})</h2>
                  <table className="w-full text-xs tabular-nums">
                    <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">Code</th><th className="py-2">Customer Name</th><th className="py-2">Segment</th><th className="py-2 text-right">Credit Limit</th><th className="py-2 text-right">Outstanding AR</th></tr></thead>
                    <tbody>
                      {customers.map(c => (
                        <tr key={c.id} className="border-b border-white/5"><td className="py-2 font-mono text-[#648BFF]">{c.customer_code}</td><td className="py-2 font-medium">{c.name}</td><td className="py-2">{c.customer_type}</td><td className="py-2 text-right">{fmtLKR(c.credit_limit)}</td><td className="py-2 text-right font-bold text-[#F4B740]">{fmtLKR(c.outstanding_balance)}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* INVOICES & PAYMENTS */}
              {route === "invoices" && (
                <div className="glass-table p-5 rounded-2xl">
                  <h2 className="text-base font-bold mb-3">Tax Invoices ({invoices.length})</h2>
                  <table className="w-full text-xs tabular-nums">
                    <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">Invoice #</th><th className="py-2">Customer</th><th className="py-2">Issue Date</th><th className="py-2 text-right">Total</th><th className="py-2 text-right">Paid</th><th className="py-2 text-right">Balance Due</th><th className="py-2">Status</th></tr></thead>
                    <tbody>
                      {invoices.map(i => (
                        <tr key={i.id} className="border-b border-white/5"><td className="py-2 font-mono text-[#648BFF]">{i.invoice_number}</td><td className="py-2 font-medium">{i.customer_name}</td><td className="py-2">{fmtDate(i.issue_date)}</td><td className="py-2 text-right">{fmtLKR(i.total_amount)}</td><td className="py-2 text-right text-[#20C997]">{fmtLKR(i.amount_paid)}</td><td className="py-2 text-right font-bold text-[#F4B740]">{fmtLKR(i.balance_due)}</td><td className="py-2">{i.status}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {route === "payments" && (
                <div className="glass-table p-5 rounded-2xl">
                  <h2 className="text-base font-bold mb-3">Recorded Payments ({payments.length})</h2>
                  <table className="w-full text-xs tabular-nums">
                    <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">Payment #</th><th className="py-2">Invoice #</th><th className="py-2">Customer</th><th className="py-2">Date</th><th className="py-2 text-right">Amount</th></tr></thead>
                    <tbody>
                      {payments.map(p => (
                        <tr key={p.id} className="border-b border-white/5"><td className="py-2 font-mono text-[#20C997]">{p.payment_number}</td><td className="py-2 font-mono text-[#648BFF]">{p.invoice_number}</td><td className="py-2">{p.customer_name}</td><td className="py-2">{fmtDate(p.payment_date)}</td><td className="py-2 text-right font-bold text-[#20C997]">{fmtLKR(p.amount)}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* EXPENSES & ACCOUNTING */}
              {route === "expenses" && (
                <div className="glass-table p-5 rounded-2xl">
                  <h2 className="text-base font-bold mb-3">Operating Expenses ({expenses.length})</h2>
                  <table className="w-full text-xs tabular-nums">
                    <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">Expense #</th><th className="py-2">Category</th><th className="py-2">Vendor</th><th className="py-2">Date</th><th className="py-2 text-right">Amount (LKR)</th></tr></thead>
                    <tbody>
                      {expenses.map(ex => (
                        <tr key={ex.id} className="border-b border-white/5"><td className="py-2 font-mono text-[#648BFF]">{ex.expense_number}</td><td className="py-2 font-medium">{ex.category}</td><td className="py-2">{ex.vendor_name}</td><td className="py-2">{fmtDate(ex.expense_date)}</td><td className="py-2 text-right font-bold text-[#F4B740]">{fmtLKR(ex.total_amount)}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {route === "accounting" && (
                <div className="glass-table p-5 rounded-2xl space-y-3">
                  <h2 className="text-base font-bold">Posted Double-Entry General Ledger Journal Entries ({journals.length})</h2>
                  <table className="w-full text-xs tabular-nums">
                    <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">Entry #</th><th className="py-2">Date</th><th className="py-2">Reference</th><th className="py-2">Description</th><th className="py-2 text-right">Total Debit</th><th className="py-2 text-right">Total Credit</th><th className="py-2">Status</th></tr></thead>
                    <tbody>
                      {journals.map(j => (
                        <tr key={j.id} className="border-b border-white/5"><td className="py-2 font-mono text-[#648BFF]">{j.entry_number}</td><td className="py-2">{fmtDate(j.entry_date)}</td><td className="py-2 font-mono">{j.reference_number}</td><td className="py-2">{j.description}</td><td className="py-2 text-right text-[#20C997]">{fmtLKR(j.total_debit)}</td><td className="py-2 text-right text-[#20C997]">{fmtLKR(j.total_credit)}</td><td className="py-2">{j.status}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* FINANCIAL REPORTS (TRIAL BALANCE, P&L, BALANCE SHEET) */}
              {route === "financial-reports" && trialBalance && (
                <div className="space-y-6 tabular-nums">
                  {pnl && balanceSheet && (
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                      <div className="glass-panel p-4 rounded-2xl"><div className="text-xs text-[#94A3B8]">Total Revenue (P&L)</div><div className="text-lg font-bold text-[#20C997] mt-1">{fmtLKR(pnl.total_revenue)}</div></div>
                      <div className="glass-panel p-4 rounded-2xl"><div className="text-xs text-[#94A3B8]">Net Profit (P&L)</div><div className="text-lg font-bold text-[#20C997] mt-1">{fmtLKR(pnl.net_profit)}</div></div>
                      <div className="glass-panel p-4 rounded-2xl"><div className="text-xs text-[#94A3B8]">Total Assets (BS)</div><div className="text-lg font-bold text-[#648BFF] mt-1">{fmtLKR(balanceSheet.total_assets)}</div></div>
                      <div className="glass-panel p-4 rounded-2xl"><div className="text-xs text-[#94A3B8]">Liabilities + Equity (BS)</div><div className="text-lg font-bold text-[#8B7CFF] mt-1">{fmtLKR(balanceSheet.total_liabilities_and_equity)}</div></div>
                    </div>
                  )}
                  <div className="glass-table p-5 rounded-2xl">
                    <div className="flex justify-between items-center mb-3">
                      <h2 className="text-base font-bold">General Ledger Trial Balance</h2>
                      <span className="px-3 py-1 rounded-full bg-[#20C997]/20 text-[#20C997] text-xs font-bold">
                        {trialBalance.is_balanced ? "VERIFIED: TOTAL DEBITS == TOTAL CREDITS" : "CHECK"}
                      </span>
                    </div>
                    <table className="w-full text-xs">
                      <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">Code</th><th className="py-2">Account</th><th className="py-2">Type</th><th className="py-2 text-right">Debit Balance</th><th className="py-2 text-right">Credit Balance</th></tr></thead>
                      <tbody>
                        {(trialBalance.accounts || []).map(a => (
                          <tr key={a.code} className="border-b border-white/5"><td className="py-2 font-mono text-[#648BFF]">{a.code}</td><td className="py-2 font-medium">{a.name}</td><td className="py-2">{a.account_type}</td><td className="py-2 text-right">{a.debit_balance > 0 ? fmtLKR(a.debit_balance) : "—"}</td><td className="py-2 text-right">{a.credit_balance > 0 ? fmtLKR(a.credit_balance) : "—"}</td></tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr className="border-t-2 border-[#648BFF] font-bold text-sm text-[#20C997]">
                          <td colSpan="3" className="py-3">GRAND TOTAL</td>
                          <td className="py-3 text-right">{fmtLKR(trialBalance.total_debit)}</td>
                          <td className="py-3 text-right">{fmtLKR(trialBalance.total_credit)}</td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
              )}

              {/* PROJECTS & KANBAN */}
              {route === "projects" && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {projects.map(p => (
                      <div key={p.id} className="glass-panel p-4 rounded-2xl space-y-2">
                        <div className="flex justify-between text-xs"><span className="font-mono text-[#648BFF]">{p.project_code}</span><span className="text-[#20C997]">{p.progress_percent}%</span></div>
                        <div className="font-bold text-sm">{p.name}</div>
                        <div className="text-xs text-[#94A3B8]">Budget: {fmtLKR(p.budget)}</div>
                      </div>
                    ))}
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                    {["BACKLOG","TODO","IN_PROGRESS","REVIEW","DONE"].map(col => (
                      <div key={col} className="glass-panel p-3.5 rounded-2xl space-y-2.5">
                        <div className="text-xs font-bold border-b border-white/10 pb-2">{col}</div>
                        {tasks.filter(t => t.status === col).map(t => (
                          <div key={t.id} className="p-3 rounded-xl bg-[#141F31] border border-white/10 text-xs space-y-1.5">
                            <div className="font-mono text-[10px] text-[#648BFF]">{t.task_code}</div>
                            <div className="font-semibold">{t.title}</div>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* APPROVALS */}
              {route === "approvals" && (
                <div className="glass-table p-5 rounded-2xl">
                  <h2 className="text-base font-bold mb-3">Workflow Approval Center (Separation-of-Duties Enforced)</h2>
                  <table className="w-full text-xs tabular-nums">
                    <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">Document</th><th className="py-2">Type</th><th className="py-2">Requested By</th><th className="py-2 text-right">Amount</th><th className="py-2">Steps</th><th className="py-2">Status</th></tr></thead>
                    <tbody>
                      {approvals.map(a => (
                        <tr key={a.id} className="border-b border-white/5"><td className="py-2 font-mono text-[#648BFF]">{a.document_number}</td><td className="py-2">{a.document_type}</td><td className="py-2">{a.requested_by_name}</td><td className="py-2 text-right font-bold">{fmtLKR(a.amount)}</td><td className="py-2">Step {a.current_step_order}/{a.total_steps_required}</td><td className="py-2 font-semibold text-[#F4B740]">{a.status}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* AI DEMAND FORECASTING */}
              {route === "demand-forecast" && demandFc && (
                <div className="space-y-5 tabular-nums">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="glass-panel p-4 rounded-2xl"><div className="text-xs text-[#94A3B8]">Model Algorithm</div><div className="text-base font-bold text-[#648BFF] mt-1">{demandFc.algorithm}</div></div>
                    <div className="glass-panel p-4 rounded-2xl"><div className="text-xs text-[#94A3B8]">MAE</div><div className="text-base font-bold text-[#20C997] mt-1">{demandFc.evaluation_metrics?.mae}</div></div>
                    <div className="glass-panel p-4 rounded-2xl"><div className="text-xs text-[#94A3B8]">RMSE</div><div className="text-base font-bold text-[#648BFF] mt-1">{demandFc.evaluation_metrics?.rmse}</div></div>
                    <div className="glass-panel p-4 rounded-2xl"><div className="text-xs text-[#94A3B8]">WAPE (%)</div><div className="text-base font-bold text-[#8B7CFF] mt-1">{demandFc.evaluation_metrics?.wape_percent}%</div></div>
                  </div>
                  <div className="glass-table p-5 rounded-2xl max-h-[500px] overflow-y-auto">
                    <h2 className="text-sm font-bold mb-3">7D / 30D / 90D Product Demand Forecasts & Stockout Risk</h2>
                    <table className="w-full text-xs">
                      <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">SKU</th><th className="py-2">Product</th><th className="py-2 text-right">Stock</th><th className="py-2 text-right">7D</th><th className="py-2 text-right">30D</th><th className="py-2 text-right">90D</th><th className="py-2">Risk</th><th className="py-2 text-right">Suggested Reorder</th></tr></thead>
                      <tbody>
                        {(demandFc.forecasts || []).map(f => (
                          <tr key={f.sku} className="border-b border-white/5"><td className="py-2 font-mono text-[#648BFF]">{f.sku}</td><td className="py-2">{f.product_name}</td><td className="py-2 text-right font-bold">{f.current_stock}</td><td className="py-2 text-right">{f.forecast_7d}</td><td className="py-2 text-right font-bold text-[#648BFF]">{f.forecast_30d}</td><td className="py-2 text-right">{f.forecast_90d}</td><td className="py-2 font-bold text-[#F06464]">{f.stockout_risk}</td><td className="py-2 text-right font-bold text-[#20C997]">+{f.suggested_reorder_qty}</td></tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* AI SALES FORECASTING */}
              {route === "sales-forecast" && salesFc && (
                <div className="glass-table p-5 rounded-2xl tabular-nums space-y-3">
                  <h2 className="text-base font-bold">Monthly Sales & Revenue Forecast (Next Month: {fmtLKR(salesFc.next_month_predicted_revenue)})</h2>
                  <table className="w-full text-xs">
                    <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">Period</th><th className="py-2">Type</th><th className="py-2 text-right">Actual Revenue</th><th className="py-2 text-right">Predicted Revenue</th><th className="py-2 text-right">90% Confidence Band</th></tr></thead>
                    <tbody>
                      {(salesFc.timeline || []).map(r => (
                        <tr key={r.period_key} className="border-b border-white/5"><td className="py-2 font-bold">{r.period}</td><td className="py-2">{r.type}</td><td className="py-2 text-right">{r.actual_revenue !== null ? fmtLKR(r.actual_revenue) : "—"}</td><td className="py-2 text-right font-bold text-[#20C997]">{fmtLKR(r.predicted_revenue)}</td><td className="py-2 text-right text-[#94A3B8]">{fmtLKR(r.lower_bound)} – {fmtLKR(r.upper_bound)}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* AI ANOMALY DETECTION */}
              {route === "anomaly-detection" && anomalies && (
                <div className="space-y-4">
                  <div className="p-3.5 rounded-2xl glass-panel text-xs text-[#F4B740]">{anomalies.disclaimer}</div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {(anomalies.events || []).map(ev => (
                      <div key={ev.id} className="glass-panel p-5 rounded-2xl space-y-2 border border-red-500/30">
                        <div className="flex justify-between text-xs font-mono"><span className="text-[#F06464] font-bold">{ev.domain} • {ev.reference_number}</span><span>Score: {ev.anomaly_score} ({ev.severity})</span></div>
                        <div className="text-sm font-bold">{ev.title}</div>
                        <p className="text-xs text-[#94A3B8]">{ev.reason}</p>
                        <div className="text-xs text-[#20C997] pt-1">Recommended Review: {ev.recommended_action}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* AI COPILOT */}
              {route === "ai-copilot" && (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                  <div className="lg:col-span-8 glass-panel p-5 rounded-2xl space-y-4">
                    <h2 className="text-base font-bold">Nexora Conversational AI Business Copilot</h2>
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {copilotMsgs.map((m, i) => (
                        <div key={i} className="p-4 rounded-2xl bg-[#141F31] border border-white/10 text-xs space-y-2">
                          <div className="font-bold text-[#648BFF]">Q: {m.question}</div>
                          <div className="whitespace-pre-line leading-relaxed">{m.answer}</div>
                          <div className="text-[10px] text-[#20C997] font-mono">Sources: {(m.source_references || []).join(" | ")}</div>
                        </div>
                      ))}
                    </div>
                    <form onSubmit={async e => {
                      e.preventDefault();
                      if (!copilotQ.trim()) return;
                      const res = await api("/ai/copilot/chat", { method: "POST", body: JSON.stringify({ question: copilotQ }) });
                      setCopilotMsgs(prev => [...prev, res]);
                      setCopilotQ("");
                    }} className="flex gap-2">
                      <input value={copilotQ} onChange={e => setCopilotQ(e.target.value)} placeholder="Ask about monthly expenses, low-stock replenishment, top suppliers, or delayed projects..." className="flex-1 px-4 py-2.5 rounded-xl bg-[#141F31] text-white border border-white/10 text-xs" />
                      <button type="submit" className="px-4 py-2.5 rounded-xl bg-[#648BFF] text-white text-xs font-bold">Ask Copilot</button>
                    </form>
                  </div>
                  <div className="lg:col-span-4 glass-panel p-5 rounded-2xl space-y-2">
                    <div className="text-xs font-bold text-[#8B7CFF]">One-Click Analytical Queries</div>
                    {[
                      "What were our total expenses this month?",
                      "Which products need replenishment?",
                      "Show our highest-value suppliers.",
                      "Which projects are behind schedule?",
                    ].map(q => (
                      <button key={q} onClick={async () => {
                        const res = await api("/ai/copilot/chat", { method: "POST", body: JSON.stringify({ question: q }) });
                        setCopilotMsgs(prev => [...prev, res]);
                      }} className="w-full p-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-left text-xs">{q}</button>
                    ))}
                  </div>
                </div>
              )}

              {/* BI REPORTS, AUDIT LOGS & USERS */}
              {route === "reports" && biReport && (
                <div className="glass-table p-5 rounded-2xl">
                  <h2 className="text-base font-bold mb-3">{biReport.report_type}</h2>
                  <table className="w-full text-xs tabular-nums">
                    <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left">{(biReport.columns || []).map(c => <th key={c} className="py-2 uppercase">{c}</th>)}</tr></thead>
                    <tbody>
                      {(biReport.rows || []).map((r, i) => (
                        <tr key={i} className="border-b border-white/5">{(biReport.columns || []).map(c => <td key={c} className="py-2">{String(r[c] ?? "—")}</td>)}</tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {route === "audit-logs" && (
                <div className="glass-table p-5 rounded-2xl">
                  <h2 className="text-base font-bold mb-3">Immutable Audit Logs ({auditLogs.length})</h2>
                  <table className="w-full text-xs">
                    <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">Date</th><th className="py-2">Actor</th><th className="py-2">Action</th><th className="py-2">Entity</th><th className="py-2">Correlation ID</th></tr></thead>
                    <tbody>
                      {auditLogs.map(l => (
                        <tr key={l.id} className="border-b border-white/5"><td className="py-2">{fmtDate(l.created_at)}</td><td className="py-2 text-[#648BFF]">{l.actor_email}</td><td className="py-2 font-bold">{l.action}</td><td className="py-2">{l.entity_type}</td><td className="py-2 font-mono text-[#94A3B8]">{l.correlation_id}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {route === "users-permissions" && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="glass-table p-5 rounded-2xl">
                    <h2 className="text-sm font-bold mb-3">Tenant Users ({usersList.length})</h2>
                    <table className="w-full text-xs">
                      <thead><tr className="text-[#94A3B8] border-b border-white/10 text-left"><th className="py-2">Name</th><th className="py-2">Email</th><th className="py-2">Roles</th></tr></thead>
                      <tbody>
                        {usersList.map(u => (
                          <tr key={u.id} className="border-b border-white/5"><td className="py-2 font-medium">{u.full_name}</td><td className="py-2 font-mono text-[#648BFF]">{u.email}</td><td className="py-2">{u.roles?.join(", ")}</td></tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="glass-table p-5 rounded-2xl">
                    <h2 className="text-sm font-bold mb-3">12 Enterprise RBAC Roles</h2>
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {rolesList.map(r => (
                        <div key={r.id} className="p-3 rounded-xl bg-white/5 text-xs">
                          <div className="flex justify-between font-bold text-[#648BFF]"><span>{r.name} ({r.code})</span><span>{r.permissions?.length} perms</span></div>
                          <div className="text-[11px] text-[#94A3B8] mt-1">{r.description}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </main>
          </div>
        </div>
      );
    }

    ReactDOM.createRoot(document.getElementById("root")).render(<App />);
  </script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
def serve_portal() -> HTMLResponse:
    return HTMLResponse(content=NEXORA_PORTAL_HTML)
