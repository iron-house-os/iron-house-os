import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { modules } from "./modules";
import { PlaceholderPage } from "./pages/PlaceholderPage";

export function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        {modules.map((module) => (
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
