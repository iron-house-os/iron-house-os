import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { modules } from "./modules";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { RFQBuilderPage } from "./pages/RFQBuilderPage";
import { SupplierDatabasePage } from "./pages/SupplierDatabasePage";

export function App() {
  const placeholderModules = modules.filter(
    (module) => !["/rfq-builder", "/suppliers"].includes(module.path),
  );

  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/rfq-builder" element={<RFQBuilderPage />} />
        <Route path="/rfq-builder/:rfqPackageId" element={<RFQBuilderPage />} />
        <Route path="/suppliers" element={<SupplierDatabasePage />} />
        <Route path="/suppliers/:supplierId" element={<SupplierDatabasePage />} />
        {placeholderModules.map((module) => (
          <Route
            key={module.path}
            path={module.path}
            element={<PlaceholderPage module={module} />}
          />
        ))}
      </Routes>
    </AppLayout>
  );
}
