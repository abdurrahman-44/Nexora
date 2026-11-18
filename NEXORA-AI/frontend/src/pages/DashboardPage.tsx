import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowUpRight,
  Briefcase,
  CheckCircle2,
  Download,
  FolderKanban,
  Landmark,
  Package,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  Users,
} from "lucide-react";
import { apiRequest } from "../api/client";
import { NavRoute } from "../components/layout/AppShell";
import { useAuth } from "../context/AuthContext";
import { exportRowsToCSV, formatCurrency } from "../utils/formatters";

interface DashboardPageProps {
  onNavigate: (route: NavRoute) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
  const { user, selectedBranchId } = useAuth();
  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const q = selectedBranchId !== "ALL" ? `?branch_id=${selectedBranchId}` : "";
      const res = await apiRequest(`/analytics/dashboard${q}`);
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load executive KPIs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, [user?.organization_id, selectedBranchId]);

  if (loading && !data) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="glass-panel rounded-2xl h-28 animate-pulse p-5" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-panel rounded-2xl p-6 border border-[#F06464]/40 text-sm text-[#F06464]">
        {error}
      </div>
    );
  }

  const kpis = data?.kpis || {};
  const trends: any[] = data?.charts?.monthly_trends || [];
  const depts: any[] = data?.charts?.department_performance || [];
  const currency = data?.organization?.currency || "LKR";

  const maxTrendVal = Math.max(
    1,
    ...trends.map((t) => Math.max(t.revenue || 0, t.expenses || 0, t.purchases || 0))
  );

  const kpiCards = [
    {
      label: "Total Posted Revenue",
      value: formatCurrency(kpis.total_revenue, currency),
      sub: "Posted GL Accounts 4000–4999",
      color: "text-[#20C997]",
      icon: TrendingUp,
      route: "financial-reports" as NavRoute,
    },
    {
      label: "Total Combined Expenses",
      value: formatCurrency(kpis.total_expenses, currency),
      sub: "COGS + Operating Expenses",
      color: "text-[#F4B740]",
      icon: Landmark,
      route: "expenses" as NavRoute,
    },
    {
      label: "Net Profit (Double-Entry)",
      value: formatCurrency(kpis.net_profit, currency),
      sub: `Net Margin: ${kpis.net_margin_percent ?? 0}%`,
      color: kpis.net_profit >= 0 ? "text-[#20C997]" : "text-[#F06464]",
      icon: Sparkles,
      route: "financial-reports" as NavRoute,
    },
    {
      label: "Outstanding Receivables",
      value: formatCurrency(kpis.outstanding_receivables, currency),
      sub: "Trade Debtors (GL 1100)",
      color: "text-[#648BFF]",
      icon: Briefcase,
      route: "invoices" as NavRoute,
    },
    {
      label: "Outstanding Payables",
      value: formatCurrency(kpis.outstanding_payables, currency),
      sub: "Trade Creditors (GL 2000)",
      color: "text-[#8B7CFF]",
      icon: Landmark,
      route: "procurement" as NavRoute,
    },
    {
      label: "Inventory Valuation (WAC)",
      value: formatCurrency(kpis.inventory_valuation, currency),
      sub: "Weighted Average Cost Basis",
      color: "text-[#648BFF]",
      icon: Package,
      route: "inventory" as NavRoute,
    },
    {
      label: "Low-Stock Products",
      value: String(kpis.low_stock_products ?? 0),
      sub: "At or below reorder threshold",
      color: (kpis.low_stock_products ?? 0) > 0 ? "text-[#F06464]" : "text-[#20C997]",
      icon: AlertTriangle,
      route: "demand-forecast" as NavRoute,
    },
    {
      label: "Pending Approvals",
      value: String(kpis.pending_approvals ?? 0),
      sub: "Workflow Engine Queue",
      color: (kpis.pending_approvals ?? 0) > 0 ? "text-[#F4B740]" : "text-[#20C997]",
      icon: ShieldAlert,
      route: "approvals" as NavRoute,
    },
    {
      label: "Active Workforce",
      value: String(kpis.total_employees ?? 0),
      sub: "Across 4 Sri Lankan Branches",
      color: "text-[#20C997]",
      icon: Users,
      route: "employees" as NavRoute,
    },
    {
      label: "Active Enterprise Projects",
      value: String(kpis.active_projects ?? 0),
      sub: "Tracked via Kanban & Milestones",
      color: "text-[#8B7CFF]",
      icon: FolderKanban,
      route: "projects" as NavRoute,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight">
              Executive Command Center
            </h1>
            {data?.organization?.is_demo_data && (
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[#648BFF]/15 text-[#648BFF] border border-[#648BFF]/30">
                Synthetic Demonstration Dataset • {data.organization.name}
              </span>
            )}
          </div>
          <p className="text-xs text-[#94A3B8] mt-1">
            All financial and operational KPIs below are calculated in real time from posted PostgreSQL/SQLAlchemy double-entry ledger lines and warehouse stock balances.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => exportRowsToCSV("nexora_monthly_financial_trends.csv", trends)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl glass-panel text-xs font-medium hover:bg-white/10 transition"
          >
            <Download className="w-3.5 h-3.5 text-[#648BFF]" />
            Export Trends CSV
          </button>
          <button
            onClick={fetchDashboard}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#648BFF] hover:bg-[#648BFF]/90 text-white text-xs font-semibold transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh Live Ledger
          </button>
        </div>
      </div>

      {/* 10 Database-Derived KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {kpiCards.map((card) => {
          const Icon = card.icon;
          return (
            <button
              key={card.label}
              onClick={() => onNavigate(card.route)}
              className="glass-panel rounded-2xl p-4 text-left hover:-translate-y-0.5 transition group"
            >
              <div className="flex items-center justify-between text-xs text-[#94A3B8]">
                <span className="font-medium truncate">{card.label}</span>
                <Icon className={`w-4 h-4 ${card.color} shrink-0`} />
              </div>
              <div className={`text-lg font-bold tabular-nums mt-2 ${card.color}`}>
                {card.value}
              </div>
              <div className="flex items-center justify-between mt-2 text-[11px] text-[#94A3B8]">
                <span className="truncate">{card.sub}</span>
                <ArrowUpRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition text-[#648BFF]" />
              </div>
            </button>
          );
        })}
      </div>

      {/* Charts Row: Revenue vs Expenses & Department Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Monthly Revenue vs Expenses & Cash Flow Visual Chart */}
        <div className="lg:col-span-8 glass-panel rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold">
                Revenue vs. Expenses & Procurement Trends (Last 6 Months)
              </h2>
              <p className="text-xs text-[#94A3B8]">
                Synchronized with Customer Invoices, Operating Expenses, and Purchase Orders ({currency})
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#648BFF]" /> Revenue
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#F06464]" /> Expenses
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#20C997]" /> Net Cash Flow
              </span>
            </div>
          </div>

          <div className="grid grid-cols-6 gap-3 pt-4 items-end h-56 border-b border-white/10 pb-3">
            {trends.map((t) => {
              const revH = Math.max(8, Math.round(((t.revenue || 0) / maxTrendVal) * 160));
              const expH = Math.max(6, Math.round(((t.expenses || 0) / maxTrendVal) * 160));
              return (
                <div key={t.month} className="flex flex-col items-center gap-2 h-full justify-end">
                  <div className="flex items-end gap-1.5 w-full justify-center">
                    <div
                      style={{ height: `${revH}px` }}
                      className="w-4 sm:w-5 rounded-t-lg bg-gradient-to-t from-[#648BFF]/60 to-[#648BFF] transition-all"
                      title={`Revenue: ${formatCurrency(t.revenue, currency)}`}
                    />
                    <div
                      style={{ height: `${expH}px` }}
                      className="w-4 sm:w-5 rounded-t-lg bg-gradient-to-t from-[#F06464]/60 to-[#F06464] transition-all"
                      title={`Expenses: ${formatCurrency(t.expenses, currency)}`}
                    />
                  </div>
                  <div className="text-[11px] font-medium text-[#94A3B8]">{t.month}</div>
                </div>
              );
            })}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs tabular-nums">
              <thead>
                <tr className="text-[#94A3B8] border-b border-white/10">
                  <th className="py-2 text-left">Period</th>
                  <th className="py-2 text-right">Invoiced Revenue</th>
                  <th className="py-2 text-right">Operating Expenses</th>
                  <th className="py-2 text-right">Procurement POs</th>
                  <th className="py-2 text-right">Net Cash Flow</th>
                </tr>
              </thead>
              <tbody>
                {trends.map((t) => (
                  <tr key={t.month} className="border-b border-white/5">
                    <td className="py-2 font-medium">{t.month}</td>
                    <td className="py-2 text-right text-[#648BFF]">
                      {formatCurrency(t.revenue, currency)}
                    </td>
                    <td className="py-2 text-right text-[#F4B740]">
                      {formatCurrency(t.expenses, currency)}
                    </td>
                    <td className="py-2 text-right text-[#8B7CFF]">
                      {formatCurrency(t.purchases, currency)}
                    </td>
                    <td
                      className={`py-2 text-right font-semibold ${
                        t.cash_flow >= 0 ? "text-[#20C997]" : "text-[#F06464]"
                      }`}
                    >
                      {formatCurrency(t.cash_flow, currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Departmental Budget & Workforce Distribution */}
        <div className="lg:col-span-4 glass-panel rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold">Departmental Budget & Workforce</h2>
              <p className="text-xs text-[#94A3B8]">8 Active Corporate Divisions</p>
            </div>
            <CheckCircle2 className="w-4 h-4 text-[#20C997]" />
          </div>

          <div className="space-y-3">
            {depts.map((d) => (
              <div
                key={d.code}
                className="p-3 rounded-xl bg-white/5 border border-white/5 space-y-1.5"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold truncate">{d.department}</span>
                  <span className="text-[11px] font-mono text-[#648BFF]">
                    {d.headcount} Staff
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-[#94A3B8] tabular-nums">
                  <span>{d.code}</span>
                  <span>Budget: {formatCurrency(d.budget_lkr, currency, true)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
