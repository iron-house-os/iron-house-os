import { Profiler } from "react";
import { Navigate, Route, Routes, useLocation, useParams } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { BackupsPage } from "./pages/BackupsPage";
import { CustomerQuotesPage } from "./pages/CustomerQuotesPage";
import { BidPackageGeneratorPage } from "./pages/BidPackageGeneratorPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DocumentLibraryPage } from "./pages/DocumentLibraryPage";
import { DocumentOperationsPage } from "./pages/DocumentOperationsPage";
import { DrawingIntelligencePage } from "./pages/DrawingIntelligencePage";
import {
  EmployeePortalPage,
  ForemanPortalPage,
  VehicleTrackingPage,
} from "./pages/EmployeePortalPage";
import { EmployeeOnboardingPage } from "./pages/EmployeeOnboardingPage";
import { EmployeeOnboardingPortalPage } from "./pages/EmployeeOnboardingPortalPage";
import { EquipmentPage } from "./pages/EquipmentPage";
import { EquipmentFieldPage } from "./pages/EquipmentFieldPage";
import { FinancialControlPage } from "./pages/FinancialControlPage";
import { EstimatingPage } from "./pages/EstimatingPage";
import { MunicipalityIntelligencePage } from "./pages/MunicipalityIntelligencePage";
import { MVPWorkflowPage } from "./pages/MVPWorkflowPage";
import { LoginPage } from "./pages/LoginPage";
import { IronHouseChatPage } from "./pages/IronHouseChatPage";
import { MeetingMinutesPage } from "./pages/MeetingMinutesPage";
import { GoogleCalendarPage } from "./pages/GoogleCalendarPage";
import { PasswordRecoveryPage } from "./pages/PasswordRecoveryPage";
import { ProjectOperationsPage } from "./pages/ProjectOperationsPage";
import { ProjectScopedLauncherPage } from "./pages/ProjectScopedLauncherPage";
import { ProjectWorkspacePage } from "./pages/ProjectWorkspacePage";
import { PurchaseOrderRequestPage } from "./pages/PurchaseOrderRequestPage";
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
import { WorkerOrientationsPage } from "./pages/WorkerOrientationsPage";
import {
  isPerformanceObservabilityEnabled,
  observeCoreRender,
} from "./observability/performance";

function EmployeePortalRoute() { return <EmployeePortalPage section={useParams().section} />; }
function EmployeeOperatorRoute() { return <EmployeePortalPage section="operator" operatorSection={useParams().operatorSection} />; }
function ForemanPortalRoute() { return <ForemanPortalPage section={useParams().section} />; }

export function legacyOperatorTarget(section?: string) {
  if (!section || section === "dashboard") return "/employee-portal/operator";
  const employeeSections: Record<string, string> = {
    backups: "backups",
    receipts: "receipts",
    schedule: "schedule",
    "small-equipment": "small-equipment",
  };
  return employeeSections[section]
    ? `/employee-portal/${employeeSections[section]}`
    : `/employee-portal/operator/${section === "milestones" ? "qualification" : section}`;
}

function LegacyOperatorRoute() {
  return <Navigate to={legacyOperatorTarget(useParams().section)} replace />;
}

function AuthenticatedApp() {
  const { user, portalRole, isLoading } = useAuth();
  const location = useLocation();
  if (/^\/employee-onboarding\/[^/]+$/.test(location.pathname)) {
    return (
      <Routes>
        <Route path="/employee-onboarding/:token" element={<EmployeeOnboardingPortalPage />} />
      </Routes>
    );
  }
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
    const isForeman = portalRole === "foreman";
    const root = isForeman ? "/foreman-portal" : "/employee-portal";
    const sections = isForeman ? ["time", "backups", "receipts", "schedule", "production", "loads", "forms", "safety", "milestones", "small-equipment", "records"] : ["time", "backups", "receipts", "journal", "schedule", "safety", "milestones", "small-equipment", "profile", "records"];
    const Page = isForeman ? ForemanPortalPage : EmployeePortalPage;
    return <AppLayout><Routes><Route path={root} element={<Page />} /><Route path="/request-po" element={<PurchaseOrderRequestPage />} /><Route path={`${root}/request-po`} element={<PurchaseOrderRequestPage />} /><Route path="/backups" element={<BackupsPage />} /><Route path="/equipment/field/:equipmentId" element={<EquipmentFieldPage />} />{sections.map((section) => <Route key={section} path={`${root}/${section}`} element={<Page section={section} />} />)}{!isForeman ? <><Route path="/employee-portal/operator" element={<EmployeePortalPage section="operator" />} /><Route path="/employee-portal/operator/:operatorSection" element={<EmployeeOperatorRoute />} /><Route path="/operator" element={<LegacyOperatorRoute />} /><Route path="/operator/:section" element={<LegacyOperatorRoute />} /><Route path="/operator-portal" element={<LegacyOperatorRoute />} /><Route path="/operator-portal/:section" element={<LegacyOperatorRoute />} /></> : null}<Route path="*" element={<Navigate to={root} replace />} /></Routes></AppLayout>;
  }

  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/request-po" element={<PurchaseOrderRequestPage />} />
        <Route path="/backups" element={<BackupsPage />} />
        <Route path="/employee-portal" element={<EmployeePortalPage />} />
        <Route path="/employee-portal/:section" element={<EmployeePortalRoute />} />
        <Route path="/employee-portal/operator/:operatorSection" element={<EmployeeOperatorRoute />} />
        <Route path="/foreman-portal" element={<ForemanPortalPage />} />
        <Route path="/foreman-portal/:section" element={<ForemanPortalRoute />} />
        <Route path="/operator" element={<LegacyOperatorRoute />} />
        <Route path="/operator/:section" element={<LegacyOperatorRoute />} />
        <Route path="/operator-portal" element={<LegacyOperatorRoute />} />
        <Route path="/operator-portal/:section" element={<LegacyOperatorRoute />} />
        <Route path="/vehicle-tracking" element={<VehicleTrackingPage />} />
        <Route path="/safety-program" element={<SafetyProgramPage />} />
        <Route path="/safety-operations" element={<SafetyOperationsPage />} />
        <Route path="/worker-orientations" element={<WorkerOrientationsPage />} />
        <Route path="/employee-onboarding" element={<EmployeeOnboardingPage />} />
        <Route path="/iron-house-chat" element={<IronHouseChatPage />} />
        <Route path="/meeting-minutes" element={<MeetingMinutesPage />} />
        <Route path="/google-calendar" element={<GoogleCalendarPage />} />
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
        <Route path="/customer-quotes" element={<CustomerQuotesPage />} />
        <Route path="/quotes" element={<QuoteComparisonPage />} />
        <Route path="/drawing-intelligence" element={<DrawingIntelligencePage />} />
        <Route path="/quantity-takeoff" element={<QuantityTakeoffPage />} />
        <Route path="/municipality-intelligence" element={<MunicipalityIntelligencePage />} />
        <Route path="/equipment" element={<EquipmentPage />} />
        <Route path="/equipment/field/:equipmentId" element={<EquipmentFieldPage />} />
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
      {isPerformanceObservabilityEnabled() ? (
        <Profiler id="core-modules" onRender={observeCoreRender}>
          <AuthenticatedApp />
        </Profiler>
      ) : (
        <AuthenticatedApp />
      )}
    </AuthProvider>
  );
}
