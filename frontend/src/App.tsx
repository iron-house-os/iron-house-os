import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { modules } from "./modules";
import { BidPackageGeneratorPage } from "./pages/BidPackageGeneratorPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DocumentLibraryPage } from "./pages/DocumentLibraryPage";
import { DocumentOperationsPage } from "./pages/DocumentOperationsPage";
import { DrawingIntelligencePage } from "./pages/DrawingIntelligencePage";
import { EstimatingPage } from "./pages/EstimatingPage";
import { MunicipalityIntelligencePage } from "./pages/MunicipalityIntelligencePage";
import { MVPWorkflowPage } from "./pages/MVPWorkflowPage";
import { LoginPage } from "./pages/LoginPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { ProjectOperationsPage } from "./pages/ProjectOperationsPage";
import { ProjectScopedLauncherPage } from "./pages/ProjectScopedLauncherPage";
import { ProjectWorkspacePage } from "./pages/ProjectWorkspacePage";
import { QuantityTakeoffPage } from "./pages/QuantityTakeoffPage";
import { QuoteComparisonPage } from "./pages/QuoteComparisonPage";
import { RFQAutomationPage } from "./pages/RFQAutomationPage";
import { RFQBuilderPage } from "./pages/RFQBuilderPage";
import { SupplierDatabasePage } from "./pages/SupplierDatabasePage";
import { TenderIntakePage } from "./pages/TenderIntakePage";

function AuthenticatedApp() {
  const { user, isLoading } = useAuth();
  if (isLoading) {
    return (
      <main className="grid min-h-screen place-items-center bg-iron-950 text-sm font-medium text-white">
        Loading Iron House OS…
      </main>
    );
  }
  if (!user) return <LoginPage />;

  const placeholderModules = modules.filter(
    (module) =>
      ![
        "/dashboard",
        "/mvp-workflow",
        "/project-operations",
        "/document-operations",
        "/rfq-builder",
        "/rfq-automation",
        "/bid-package",
        "/suppliers",
        "/documents",
        "/projects",
        "/tenders",
        "/estimating",
        "/quotes",
        "/drawing-intelligence",
        "/quantity-takeoff",
        "/municipality-intelligence",
      ].includes(module.path),
  );

  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/mvp-workflow" element={<MVPWorkflowPage />} />
        <Route path="/project-operations" element={<ProjectOperationsPage />} />
        <Route path="/document-operations" element={<DocumentOperationsPage />} />
        <Route path="/rfq-builder" element={<RFQBuilderPage />} />
        <Route path="/rfq-builder/:rfqPackageId" element={<RFQBuilderPage />} />
        <Route path="/rfq-automation" element={<RFQAutomationPage />} />
        <Route path="/bid-package" element={<BidPackageGeneratorPage />} />
        <Route path="/suppliers" element={<SupplierDatabasePage />} />
        <Route path="/suppliers/:supplierId" element={<SupplierDatabasePage />} />
        <Route path="/documents" element={<DocumentLibraryPage />} />
        <Route path="/documents/:documentId" element={<DocumentLibraryPage />} />
        <Route path="/projects" element={<ProjectWorkspacePage />} />
        <Route path="/projects/:projectId" element={<ProjectWorkspacePage />} />
        <Route path="/p/:projectId/:tool" element={<ProjectScopedLauncherPage />} />
        <Route path="/tenders" element={<TenderIntakePage />} />
        <Route path="/tenders/:tenderId" element={<TenderIntakePage />} />
        <Route path="/estimating" element={<EstimatingPage />} />
        <Route path="/quotes" element={<QuoteComparisonPage />} />
        <Route path="/drawing-intelligence" element={<DrawingIntelligencePage />} />
        <Route path="/quantity-takeoff" element={<QuantityTakeoffPage />} />
        <Route path="/municipality-intelligence" element={<MunicipalityIntelligencePage />} />
        {placeholderModules.map((module) => (
          <Route key={module.path} path={module.path} element={<PlaceholderPage module={module} />} />
        ))}
      </Routes>
    </AppLayout>
  );
}

export function App() {
  return (
    <AuthProvider>
      <AuthenticatedApp />
    </AuthProvider>
  );
}
