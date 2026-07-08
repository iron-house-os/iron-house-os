import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { modules } from "./modules";
import { BidPackageGeneratorPage } from "./pages/BidPackageGeneratorPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DocumentLibraryPage } from "./pages/DocumentLibraryPage";
import { DrawingIntelligencePage } from "./pages/DrawingIntelligencePage";
import { EstimatingPage } from "./pages/EstimatingPage";
import { MunicipalityIntelligencePage } from "./pages/MunicipalityIntelligencePage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { ProjectScopedLauncherPage } from "./pages/ProjectScopedLauncherPage";
import { ProjectWorkspacePage } from "./pages/ProjectWorkspacePage";
import { QuantityTakeoffPage } from "./pages/QuantityTakeoffPage";
import { QuoteComparisonPage } from "./pages/QuoteComparisonPage";
import { RFQAutomationPage } from "./pages/RFQAutomationPage";
import { RFQBuilderPage } from "./pages/RFQBuilderPage";
import { SupplierDatabasePage } from "./pages/SupplierDatabasePage";
import { TenderIntakePage } from "./pages/TenderIntakePage";

export function App() {
  const placeholderModules = modules.filter(
    (module) =>
      ![
        "/dashboard",
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
