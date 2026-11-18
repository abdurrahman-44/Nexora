import React, { useState } from "react";
import { AppShell, NavRoute } from "./components/layout/AppShell";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { DashboardPage } from "./pages/DashboardPage";
import {
  FinanceAccountingView,
  NexoraIntelligenceView,
  ProjectsAndWorkflowsView,
  SalesAndInvoicesView,
  SystemAdminView,
} from "./pages/FinancialAndAIViews";
import { LoginPage } from "./pages/LoginPage";
import {
  HRModuleView,
  InventoryModuleView,
  OrganizationView,
  ProcurementModuleView,
} from "./pages/OperationsViews";

const EnterpriseWorkspace: React.FC = () => {
  const { user, loading } = useAuth();
  const [activeRoute, setActiveRoute] = useState<NavRoute>("dashboard");

  if (loading) {
    return (
      <div className="min-h-screen bg-[#080D18] text-white flex items-center justify-center text-sm">
        Initializing NEXORA ERP Security & Tenant Context...
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  const renderPage = () => {
    switch (activeRoute) {
      case "dashboard":
        return <DashboardPage onNavigate={setActiveRoute} />;
      case "organization":
      case "branches":
      case "departments":
        return <OrganizationView />;
      case "employees":
        return <HRModuleView activeSub="employees" />;
      case "attendance":
        return <HRModuleView activeSub="attendance" />;
      case "leave":
        return <HRModuleView activeSub="leave" />;
      case "performance":
        return <HRModuleView activeSub="performance" />;
      case "inventory":
        return <InventoryModuleView showWarehouses={false} />;
      case "warehouses":
        return <InventoryModuleView showWarehouses={true} />;
      case "procurement":
        return <ProcurementModuleView showSuppliers={false} />;
      case "suppliers":
        return <ProcurementModuleView showSuppliers={true} />;
      case "sales":
        return <SalesAndInvoicesView initialTab="orders" />;
      case "customers":
        return <SalesAndInvoicesView initialTab="customers" />;
      case "invoices":
        return <SalesAndInvoicesView initialTab="invoices" />;
      case "payments":
        return <SalesAndInvoicesView initialTab="payments" />;
      case "accounting":
        return <FinanceAccountingView initialTab="journals" />;
      case "expenses":
        return <FinanceAccountingView initialTab="expenses" />;
      case "financial-reports":
        return <FinanceAccountingView initialTab="trial-balance" />;
      case "projects":
        return <ProjectsAndWorkflowsView mode="projects" />;
      case "tasks":
        return <ProjectsAndWorkflowsView mode="tasks" />;
      case "approvals":
        return <ProjectsAndWorkflowsView mode="approvals" />;
      case "ai-insights":
        return <NexoraIntelligenceView activeFeature="insights" />;
      case "demand-forecast":
        return <NexoraIntelligenceView activeFeature="demand" />;
      case "sales-forecast":
        return <NexoraIntelligenceView activeFeature="sales" />;
      case "anomaly-detection":
        return <NexoraIntelligenceView activeFeature="anomalies" />;
      case "ai-copilot":
        return <NexoraIntelligenceView activeFeature="copilot" />;
      case "reports":
        return <SystemAdminView section="reports" />;
      case "notifications":
        return <SystemAdminView section="notifications" />;
      case "audit-logs":
        return <SystemAdminView section="audit-logs" />;
      case "users-permissions":
        return <SystemAdminView section="users-permissions" />;
      case "settings":
        return <SystemAdminView section="settings" />;
      default:
        return <DashboardPage onNavigate={setActiveRoute} />;
    }
  };

  return (
    <AppShell activeRoute={activeRoute} onNavigate={setActiveRoute}>
      {renderPage()}
    </AppShell>
  );
};

export function App() {
  return (
    <AuthProvider>
      <EnterpriseWorkspace />
    </AuthProvider>
  );
}

export default App;
