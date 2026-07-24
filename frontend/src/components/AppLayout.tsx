import { LogOut, Menu } from "lucide-react";
import { PropsWithChildren, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";

import { modules } from "../modules";
import { useAuth } from "../contexts/AuthContext";
import { modulePathWithProjectContext, readEffectiveProjectContext } from "../utils/projectContext";

export function AppLayout({ children }: PropsWithChildren) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const { user, portalRole, logout } = useAuth();
  const location = useLocation();
  const activeProject = readEffectiveProjectContext(location.search);
  const accessLabel =
    user?.role === "viewer"
      ? "Read-only access"
      : user?.role === "estimator"
        ? "Estimating access"
        : user?.role === "operations_manager"
          ? "Operations access"
          : "Administrator access";

  return (
    <div className="min-h-screen bg-iron-50 text-iron-950">
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex w-72 flex-col border-r border-brand-gold/30 bg-brand-black text-white shadow-brand transition-transform lg:translate-x-0 ${
          isSidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="ihos-brand-surface flex h-20 items-center gap-3 border-b border-white/10 px-4">
          <img src="/os-logo-256.png" alt="" className="h-12 w-12 rounded-xl border border-brand-gold/30 object-cover" />
          <div>
            <div className="text-lg font-semibold tracking-wide text-brand-silver">Iron House OS</div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-brand-gold">Contracting</div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label="Primary navigation">
          {modules.filter((module) => {
            if (user?.role !== "viewer") return true;
            return module.path === `/${portalRole ?? "employee"}-portal`;
          }).map((module) => {
            const Icon = module.icon;
            return (
              <NavLink
                key={module.path}
                to={modulePathWithProjectContext(module.path, activeProject)}
                className={({ isActive }) =>
                  [
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition",
                    isActive
                      ? "bg-brand-gold text-brand-black shadow-md"
                      : "text-iron-100 hover:bg-white/10 hover:text-white",
                  ].join(" ")
                }
                onClick={() => setIsSidebarOpen(false)}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {module.label}
              </NavLink>
            );
          })}
        </nav>
        <div className="border-t border-white/10 px-5 py-4 text-[10px] font-semibold uppercase tracking-[0.2em] text-iron-300">
          Civil • Earthworks • Utilities
        </div>
      </aside>

      {isSidebarOpen ? (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 z-20 bg-iron-950/60 backdrop-blur-sm lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      ) : null}

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-brand-gold/20 bg-white/95 px-4 shadow-sm backdrop-blur lg:px-8">
          <button
            type="button"
            className="rounded-md border border-brand-gold/40 p-2 text-iron-800 lg:hidden"
            onClick={() => setIsSidebarOpen((value) => !value)}
            aria-label="Open navigation"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="hidden text-sm font-medium text-iron-700 lg:block">
            {user ? `Signed in as ${user.display_name}` : "Signed out"}
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden text-xs font-medium text-iron-500 sm:block">{accessLabel}</div>
            <div className="rounded-md bg-brand-gold px-3 py-1 text-xs font-semibold capitalize text-brand-black">
              {user?.role.replace("_", " ")}
            </div>
            <button
              type="button"
              onClick={() => void logout()}
              className="rounded-md border border-iron-100 p-2 text-iron-700 transition hover:border-brand-gold hover:bg-brand-gold/10"
              aria-label="Sign out"
              title="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </header>
        <main className="mx-auto min-w-0 max-w-7xl overflow-x-clip px-4 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
