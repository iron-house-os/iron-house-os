import { Navigate, Route, Routes, useParams } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { BidPackageGeneratorPage } from "./pages/BidPackageGeneratorPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DocumentLibraryPage } from "./pages/DocumentLibraryPage";
import { DocumentOperationsPage } from "./pages/DocumentOperationsPage";
import { DrawingIntelligencePage } from "./pages/DrawingIntelligencePage";
import {
  EmployeePortalPage,
  ForemanPortalPage,
  OperatorPortalPage,
  VehicleTrackingPage,
} from "./pages/EmployeePortalPage";
import { EquipmentPage } from "./pages/EquipmentPage";
import { FinancialControlPage } from "./pages/FinancialControlPage";
import { EstimatingPage } from "./pages/EstimatingPage";
import { MunicipalityIntelligencePage } from "./pages/MunicipalityIntelligencePage";
import { MVPWorkflowPage } from "./pages/MVPWorkflowPage";
import { LoginPage } from "./pages/LoginPage";
import { IronHouseChatPage } from "./pages/IronHouseChatPage";
import { LegalControlCentrePage } from "./pages/LegalControlCentrePage";
import { PasswordRecoveryPage } from "./pages/PasswordRecoveryPage";
import { ProjectOperationsPage } from "./pages/ProjectOperationsPage";
import { ProjectScopedLauncherPage } from "./pages/ProjectScopedLauncherPage";
import { ProjectWorkspacePage } from "./pages/ProjectWorkspacePage";
import { QuantityTakeoffPage } from "./pages/QuantityTakeoffPage";
import { QuoteComparisonPage } from "./pages/QuoteComparisonPage";
import { RFQAutomationPage } from "./pages/RFQAutomationPage";
import { RFQBuilderPage } from "./pages/RFQBuilderPage";
import { ReportingPage } from "./pages/ReportingPage";
import { SafetyOperationsPage } from "./pages/SafetyOperationsPage";
import { SafetyProgramPage } from "./pages/SafetyProgramPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SupplierDatabasePage } from "./pages/SupplierDatabasePage";
import { TenderIntakePage } from "./pages/TenderIntakePage";

function EmployeePortalRoute() { return <EmployeePortalPage section={useParams().section} />; }
function ForemanPortalRoute() { return <ForemanPortalPage section={useParams().section} />; }
function OperatorPortalRoute() { return <OperatorPortalPage section={useParams().section} />; }

function AuthenticatedApp() {
  const { user, portalRole, isLoading } = useAuth();
  if (isLoading) {
    return (
      <main className="grid min-h-screen place-items-center bg-iron-950 text-sm font-medium text-white">
        Loading Iron House OS…
      </main>
    );
  }
  if (!user) return <LoginPage />;
  if (user.password_reset_required) return <PasswordRecoveryPage />;

  if (user.role === "viewer") {
    const root = `/${portalRole ?? "employee"}-portal`;
    const sections = portalRole === "foreman" ? ["time", "schedule", "production", "loads", "forms", "safety", "milestones", "small-equipment", "records"] : portalRole === "operator" ? ["time", "schedule", "loads", "inspections", "small-equipment", "photos", "milestones", "records"] : ["time", "journal", "schedule", "safety", "milestones", "small-equipment", "profile", "records"];
    const Page = portalRole === "foreman" ? ForemanPortalPage : portalRole === "operator" ? OperatorPortalPage : EmployeePortalPage;
    return <AppLayout><Routes><Route path={root} element={<Page />} />{sections.map((section) => <Route key={section} path={`${root}/${section}`} element={<Page section={section} />} />)}<Route path="*" element={<Navigate to={root} replace />} /></Routes></AppLayout>;
  }

  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/employee-portal" element={<EmployeePortalPage />} />
        <Route path="/employee-portal/:section" element={<EmployeePortalRoute />} />
        <Route path="/foreman-portal" element={<ForemanPortalPage />} />
        <Route path="/foreman-portal/:section" element={<ForemanPortalRoute />} />
        <Route path="/operator-portal" element={<OperatorPortalPage />} />
        <Route path="/operator-portal/:section" element={<OperatorPortalRoute />} />
        <Route path="/vehicle-tracking" element={<VehicleTrackingPage />} />
        <Route path="/safety-program" element={<SafetyProgramPage />} />
        <Route path="/safety-operations" element={<SafetyOperationsPage />} />
        <Route path="/iron-house-chat" element={<IronHouseChatPage />} />
        <Route path="/legal" element={user.role === "admin" ? <LegalControlCentrePage /> : <Navigate to="/dashboard" replace />} />
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
        <Route path="/equipment" element={<EquipmentPage />} />
        <Route path="/finance" element={<FinancialControlPage />} />
        <Route path="/reporting" element={<ReportingPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
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
