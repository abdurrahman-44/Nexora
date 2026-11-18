import React, { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Bell,
  BookOpen,
  Bot,
  Briefcase,
  Building2,
  CheckSquare,
  ChevronLeft,
  ChevronRight,
  Command,
  CreditCard,
  FileSpreadsheet,
  FileText,
  FolderKanban,
  GitBranch,
  HelpCircle,
  Landmark,
  Layers,
  LayoutDashboard,
  LogOut,
  Moon,
  Package,
  Receipt,
  Search,
  Settings,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  Sun,
  TrendingUp,
  Truck,
  UserCheck,
  Users,
  Warehouse,
  X,
} from "lucide-react";
import { apiRequest } from "../../api/client";
import { useAuth } from "../../context/AuthContext";

export type NavRoute =
  | "dashboard"
  | "organization"
  | "branches"
  | "departments"
  | "employees"
  | "attendance"
  | "leave"
  | "performance"
  | "inventory"
  | "warehouses"
  | "procurement"
  | "suppliers"
  | "sales"
  | "customers"
  | "accounting"
  | "invoices"
  | "payments"
  | "expenses"
  | "financial-reports"
  | "projects"
  | "tasks"
  | "approvals"
  | "ai-insights"
  | "demand-forecast"
  | "sales-forecast"
  | "anomaly-detection"
  | "ai-copilot"
  | "reports"
  | "notifications"
  | "audit-logs"
  | "users-permissions"
  | "settings";

interface NavItem {
  id: NavRoute;
  label: string;
  icon: React.FC<{ className?: string }>;
  permission?: string;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    title: "OVERVIEW",
    items: [
      { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, permission: "dashboard.view" },
    ],
  },
  {
    title: "ORGANIZATION",
    items: [
      { id: "organization", label: "Organization", icon: Building2, permission: "organizations.view" },
      { id: "branches", label: "Branches", icon: GitBranch, permission: "organizations.view" },
      { id: "departments", label: "Departments", icon: Layers, permission: "organizations.view" },
    ],
  },
  {
    title: "PEOPLE",
    items: [
      { id: "employees", label: "Employees", icon: Users, permission: "employees.view" },
      { id: "attendance", label: "Attendance", icon: UserCheck, permission: "employees.view" },
      { id: "leave", label: "Leave Management", icon: FileText, permission: "leave.view" },
      { id: "performance", label: "Performance", icon: Activity, permission: "employees.view" },
    ],
  },
  {
    title: "OPERATIONS",
    items: [
      { id: "inventory", label: "Inventory", icon: Package, permission: "inventory.view" },
      { id: "warehouses", label: "Warehouses", icon: Warehouse, permission: "inventory.view" },
      { id: "procurement", label: "Procurement", icon: ShoppingBag, permission: "procurement.view" },
      { id: "suppliers", label: "Suppliers", icon: Truck, permission: "procurement.view" },
      { id: "sales", label: "Sales", icon: TrendingUp, permission: "sales.view" },
      { id: "customers", label: "Customers", icon: Briefcase, permission: "sales.view" },
    ],
  },
  {
    title: "FINANCIALS",
    items: [
      { id: "accounting", label: "Accounting", icon: Landmark, permission: "finance.view" },
      { id: "invoices", label: "Invoices", icon: FileText, permission: "invoices.view" },
      { id: "payments", label: "Payments", icon: CreditCard, permission: "payments.view" },
      { id: "expenses", label: "Expenses", icon: Receipt, permission: "expenses.create" },
      { id: "financial-reports", label: "Financial Reports", icon: FileSpreadsheet, permission: "finance.reports.view" },
    ],
  },
  {
    title: "MANAGEMENT",
    items: [
      { id: "projects", label: "Projects", icon: FolderKanban, permission: "projects.view" },
      { id: "tasks", label: "Tasks", icon: CheckSquare, permission: "projects.view" },
      { id: "approvals", label: "Approvals", icon: ShieldCheck, permission: "approvals.view" },
    ],
  },
  {
    title: "INTELLIGENCE",
    items: [
      { id: "ai-insights", label: "AI Insights", icon: Sparkles, permission: "ai.forecast.view" },
      { id: "demand-forecast", label: "Demand Forecasting", icon: Package, permission: "ai.forecast.view" },
      { id: "sales-forecast", label: "Sales Forecasting", icon: TrendingUp, permission: "ai.forecast.view" },
      { id: "anomaly-detection", label: "Anomaly Detection", icon: AlertTriangle, permission: "ai.anomalies.view" },
      { id: "ai-copilot", label: "AI Copilot", icon: Bot, permission: "ai.copilot.use" },
    ],
  },
  {
    title: "SYSTEM",
    items: [
      { id: "reports", label: "Reports", icon: FileSpreadsheet, permission: "reports.view" },
      { id: "notifications", label: "Notifications", icon: Bell },
      { id: "audit-logs", label: "Audit Logs", icon: BookOpen, permission: "audit_logs.view" },
      { id: "users-permissions", label: "Users & Permissions", icon: Users, permission: "users.view" },
      { id: "settings", label: "Settings", icon: Settings },
    ],
  },
];

interface AppShellProps {
  activeRoute: NavRoute;
  onNavigate: (route: NavRoute) => void;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  activeRoute,
  onNavigate,
  children,
}) => {
  const {
    user,
    theme,
    selectedBranchId,
    logout,
    switchOrganization,
    switchBranch,
    toggleTheme,
    hasPermission,
  } = useAuth();

  const [collapsed, setCollapsed] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [notifOpen, setNotifOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  // Keyboard shortcut Ctrl+K / Cmd+K for Command Palette
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandOpen((prev) => !prev);
      }
      if (e.key === "Escape") {
        setCommandOpen(false);
        setNotifOpen(false);
        setHelpOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const loadNotifications = async () => {
    try {
      const res = await apiRequest("/notifications");
      setNotifications(res.items || []);
      setUnreadCount(res.unread_count || 0);
    } catch {
      // Ignore
    }
  };

  useEffect(() => {
    loadNotifications();
  }, [user?.organization_id]);

  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const res = await apiRequest(`/search?q=${encodeURIComponent(searchQuery)}`);
        setSearchResults(res.results || []);
      } catch {
        setSearchResults([]);
      }
    }, 180);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const visibleGroups = NAV_GROUPS.map((g) => ({
    ...g,
    items: g.items.filter((item) => !item.permission || hasPermission(item.permission)),
  })).filter((g) => g.items.length > 0);

  const allVisibleItems = visibleGroups.flatMap((g) => g.items);
  const activeItem = allVisibleItems.find((i) => i.id === activeRoute);

  return (
    <div className="min-h-screen flex relative overflow-hidden">
      {/* Ambient Background Gradient Orbs */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden z-0">
        <div className="absolute -top-36 -left-36 w-96 h-96 rounded-full bg-[#648BFF]/12 blur-[120px]" />
        <div className="absolute top-1/3 -right-36 w-96 h-96 rounded-full bg-[#8B7CFF]/10 blur-[130px]" />
        <div className="absolute -bottom-36 left-1/3 w-96 h-96 rounded-full bg-[#20C997]/8 blur-[130px]" />
      </div>

      {/* Left Glass Navigation Sidebar */}
      <aside
        className={`glass-sidebar z-20 flex flex-col transition-all duration-200 ${
          collapsed ? "w-20" : "w-68"
        } shrink-0 h-screen sticky top-0`}
        style={{ width: collapsed ? "5rem" : "17rem" }}
      >
        <div className="h-16 px-4 flex items-center justify-between border-b border-white/10">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#648BFF] to-[#8B7CFF] flex items-center justify-center shadow-lg shadow-[#648BFF]/25 shrink-0">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            {!collapsed && (
              <div>
                <div className="font-bold tracking-wider text-sm flex items-center gap-1.5">
                  NEXORA <span className="text-[#648BFF]">ERP</span>
                </div>
                <div className="text-[10px] text-[#94A3B8] truncate">
                  Enterprise Intelligence OS
                </div>
              </div>
            )}
          </div>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1.5 rounded-lg hover:bg-white/10 text-[#94A3B8] hover:text-white transition"
            title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Navigation Groups */}
        <div className="flex-1 overflow-y-auto py-3 px-2.5 space-y-4">
          {visibleGroups.map((group) => (
            <div key={group.title}>
              {!collapsed && (
                <div className="px-2.5 mb-1.5 text-[10px] font-semibold tracking-widest text-[#94A3B8]/80 uppercase">
                  {group.title}
                </div>
              )}
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = activeRoute === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => onNavigate(item.id)}
                      className={`w-full flex items-center gap-3 px-2.5 py-2 rounded-xl text-xs font-medium transition-all ${
                        isActive
                          ? "bg-gradient-to-r from-[#648BFF]/25 to-[#8B7CFF]/15 text-white border border-[#648BFF]/40 shadow-sm"
                          : "text-[#94A3B8] hover:text-white hover:bg-white/5"
                      }`}
                      title={collapsed ? item.label : undefined}
                    >
                      <Icon
                        className={`w-4 h-4 shrink-0 ${
                          isActive ? "text-[#648BFF]" : "text-[#94A3B8]"
                        }`}
                      />
                      {!collapsed && <span className="truncate">{item.label}</span>}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* User Footer */}
        <div className="p-3 border-t border-white/10">
          <div className="flex items-center justify-between gap-2">
            {!collapsed && (
              <div className="min-w-0">
                <div className="text-xs font-semibold truncate">{user?.full_name}</div>
                <div className="text-[11px] text-[#648BFF] truncate">
                  {user?.roles.join(", ")}
                </div>
              </div>
            )}
            <button
              onClick={logout}
              className="p-2 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-[#F06464] transition shrink-0"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Shell */}
      <div className="flex-1 flex flex-col min-w-0 z-10">
        {/* Top Glass Navigation Bar */}
        <header className="h-16 px-6 glass-panel border-b border-white/10 sticky top-0 z-20 flex items-center justify-between gap-4 rounded-none">
          {/* Left: Breadcrumbs & Command Palette Trigger */}
          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-2 text-xs">
              <span className="text-[#94A3B8]">{user?.organization_name}</span>
              <span className="text-[#94A3B8]">/</span>
              <span className="font-semibold text-[#648BFF]">
                {activeItem?.label || "Executive Dashboard"}
              </span>
            </div>

            <button
              onClick={() => setCommandOpen(true)}
              className="flex items-center gap-3 px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs text-[#94A3B8] transition"
            >
              <Search className="w-3.5 h-3.5 text-[#648BFF]" />
              <span>Global search or jump...</span>
              <kbd className="px-1.5 py-0.5 text-[10px] rounded bg-white/10 font-mono text-white">
                Ctrl+K
              </kbd>
            </button>
          </div>

          {/* Right: Tenant Switcher, Branch Selector, Theme, Notifications, Help */}
          <div className="flex items-center gap-2.5">
            {user?.organization_name?.includes("Demo") && (
              <span className="hidden lg:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-[#8B7CFF]/15 text-[#8B7CFF] border border-[#8B7CFF]/30">
                <span className="w-1.5 h-1.5 rounded-full bg-[#8B7CFF] animate-pulse" />
                Demo Tenant ({user.currency} • {user.timezone})
              </span>
            )}

            {/* Organization Switcher */}
            {user && user.organizations.length > 1 && (
              <select
                value={user.organization_id}
                onChange={(e) => switchOrganization(e.target.value)}
                className="px-2.5 py-1.5 rounded-xl bg-[#141F31] border border-white/10 text-xs focus:outline-none focus:border-[#648BFF]"
                title="Switch Organization Tenant"
              >
                {user.organizations.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name} ({o.currency})
                  </option>
                ))}
              </select>
            )}

            {/* Branch Selector */}
            {user && user.branches.length > 0 && (
              <select
                value={selectedBranchId}
                onChange={(e) => switchBranch(e.target.value)}
                className="hidden sm:block px-2.5 py-1.5 rounded-xl bg-[#141F31] border border-white/10 text-xs focus:outline-none focus:border-[#648BFF]"
                title="Filter by Branch"
              >
                <option value="ALL">All Branches ({user.branches.length})</option>
                {user.branches.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.code} — {b.city}
                  </option>
                ))}
              </select>
            )}

            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 transition"
              title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Theme`}
            >
              {theme === "dark" ? (
                <Sun className="w-4 h-4 text-[#F4B740]" />
              ) : (
                <Moon className="w-4 h-4 text-[#456FEA]" />
              )}
            </button>

            {/* Notification Center Button */}
            <div className="relative">
              <button
                onClick={() => {
                  setNotifOpen(!notifOpen);
                  loadNotifications();
                }}
                className="p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 transition relative"
                title="Notifications"
              >
                <Bell className="w-4 h-4" />
                {unreadCount > 0 && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-[#F06464] text-white text-[10px] font-bold flex items-center justify-center">
                    {unreadCount}
                  </span>
                )}
              </button>

              {notifOpen && (
                <div className="absolute right-0 mt-2 w-80 glass-panel rounded-2xl p-4 z-50 border border-white/15 shadow-2xl">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-bold">Notifications ({unreadCount} unread)</span>
                    <button
                      onClick={() => {
                        setNotifOpen(false);
                        onNavigate("notifications");
                      }}
                      className="text-[11px] text-[#648BFF] hover:underline"
                    >
                      View All
                    </button>
                  </div>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {notifications.slice(0, 6).map((n) => (
                      <div
                        key={n.id}
                        className="p-2.5 rounded-xl bg-white/5 border border-white/5 text-xs"
                      >
                        <div className="font-semibold flex items-center justify-between">
                          <span>{n.title}</span>
                          <span className="text-[10px] text-[#648BFF]">{n.category}</span>
                        </div>
                        <p className="text-[11px] text-[#94A3B8] mt-1">{n.message}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Help & Architecture Info */}
            <button
              onClick={() => setHelpOpen(true)}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 transition"
              title="Architecture & Documentation"
            >
              <HelpCircle className="w-4 h-4 text-[#94A3B8]" />
            </button>
          </div>
        </header>

        {/* Main View Area */}
        <main className="flex-1 p-6 overflow-y-auto">{children}</main>
      </div>

      {/* Command Palette & Global Search Modal (Ctrl+K) */}
      {commandOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-start justify-center pt-20 px-4">
          <div className="w-full max-w-xl glass-panel rounded-2xl border border-white/20 p-4 shadow-2xl">
            <div className="flex items-center gap-3 pb-3 border-b border-white/10">
              <Command className="w-4 h-4 text-[#648BFF]" />
              <input
                autoFocus
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search employees, SKUs, customers, suppliers, or type a module name..."
                className="flex-1 bg-transparent text-sm focus:outline-none"
              />
              <button onClick={() => setCommandOpen(false)}>
                <X className="w-4 h-4 text-[#94A3B8]" />
              </button>
            </div>

            <div className="mt-3 max-h-80 overflow-y-auto space-y-3">
              {searchResults.length > 0 && (
                <div>
                  <div className="text-[10px] font-semibold uppercase text-[#94A3B8] mb-1.5">
                    Live Database Records ({searchResults.length})
                  </div>
                  <div className="space-y-1">
                    {searchResults.map((r, i) => (
                      <button
                        key={i}
                        onClick={() => {
                          setCommandOpen(false);
                          if (r.type === "Product") onNavigate("inventory");
                          else if (r.type === "Customer") onNavigate("customers");
                          else if (r.type === "Supplier") onNavigate("suppliers");
                          else if (r.type === "Employee") onNavigate("employees");
                        }}
                        className="w-full flex items-center justify-between px-3 py-2 rounded-xl hover:bg-white/10 text-xs text-left"
                      >
                        <div>
                          <span className="font-mono text-[#648BFF] mr-2">{r.code}</span>
                          <span className="font-medium">{r.title}</span>
                        </div>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-white/10 text-[#94A3B8]">
                          {r.type}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <div className="text-[10px] font-semibold uppercase text-[#94A3B8] mb-1.5">
                  Quick Navigation Modules
                </div>
                <div className="grid grid-cols-2 gap-1.5">
                  {allVisibleItems
                    .filter((i) =>
                      !searchQuery.trim() ||
                      i.label.toLowerCase().includes(searchQuery.toLowerCase())
                    )
                    .map((item) => {
                      const Icon = item.icon;
                      return (
                        <button
                          key={item.id}
                          onClick={() => {
                            onNavigate(item.id);
                            setCommandOpen(false);
                          }}
                          className="flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-white/10 text-xs text-left"
                        >
                          <Icon className="w-3.5 h-3.5 text-[#648BFF]" />
                          <span>{item.label}</span>
                        </button>
                      );
                    })}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Help & Documentation Modal */}
      {helpOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-lg glass-panel rounded-2xl p-6 border border-white/20 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#648BFF]" />
                NEXORA ERP — Enterprise Reference Guide
              </h3>
              <button onClick={() => setHelpOpen(false)}>
                <X className="w-4 h-4 text-[#94A3B8]" />
              </button>
            </div>
            <div className="text-xs text-[#94A3B8] space-y-2 leading-relaxed">
              <p>
                <strong className="text-white">Double-Entry Accounting:</strong> Every posted sales invoice, payment receipt, goods receipt note, and expense automatically generates a balanced General Ledger journal entry (<code className="text-[#20C997]">Total Debits = Total Credits</code>).
              </p>
              <p>
                <strong className="text-white">Weighted Average Costing:</strong> Inbound Goods Receipts automatically recalculate SKU Weighted Average Cost and block negative stock issues.
              </p>
              <p>
                <strong className="text-white">Separation of Duties:</strong> Users cannot approve their own Purchase Orders or Leave Requests. Purchase Orders above <code className="text-[#F4B740]">LKR 50,000</code> require 2-step approval.
              </p>
              <p>
                <strong className="text-white">Keyboard Shortcuts:</strong> Press <kbd className="px-1.5 py-0.5 rounded bg-white/10 text-white">Ctrl+K</kbd> anytime to open the Command Palette.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
