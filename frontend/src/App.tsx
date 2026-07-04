import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { modules } from "./modules";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { RFQBuilderPage } from "./pages/RFQBuilderPage";

export function App() {
  const placeholderModules = modules.filter((module) => module.path !== "/rfq-builder");

  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/rfq-builder" element={<RFQBuilderPage />} />
        <Route path="/rfq-builder/:rfqPackageId" element={<RFQBuilderPage />} />
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
