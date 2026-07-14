import { LogOut, Menu } from "lucide-react";
import { PropsWithChildren, useState } from "react";
import { NavLink } from "react-router-dom";

import { modules } from "../modules";
import { useAuth } from "../contexts/AuthContext";

export function AppLayout({ children }: PropsWithChildren) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-iron-50 text-iron-950">
      <aside
        className={`fixed inset-y-0 left-0 z-30 w-72 border-r border-iron-100 bg-white transition-transform lg:translate-x-0 ${
          isSidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-16 items-center border-b border-iron-100 px-5">
          <div>
            <div className="text-lg font-semibold">Iron House OS</div>
            <div className="text-xs uppercase tracking-wide text-iron-500">Civil construction</div>
          </div>
        </div>
        <nav className="space-y-1 p-3">
          {modules.map((module) => {
            const Icon = module.icon;
            return (
              <NavLink
                key={module.path}
                to={module.path}
                className={({ isActive }) =>
                  [
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition",
                    isActive
                      ? "bg-iron-950 text-white"
                      : "text-iron-800 hover:bg-iron-100 hover:text-iron-950",
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
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-iron-100 bg-white px-4 lg:px-8">
          <button
            type="button"
            className="rounded-md border border-iron-100 p-2 text-iron-800 lg:hidden"
            onClick={() => setIsSidebarOpen((value) => !value)}
            aria-label="Open navigation"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="hidden text-sm text-iron-500 lg:block">
            Signed in as {user?.display_name}
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-md bg-signal-green px-3 py-1 text-xs font-semibold capitalize text-white">
              {user?.role.replace("_", " ")}
            </div>
            <button
              type="button"
              onClick={() => void logout()}
              className="rounded-md border border-iron-100 p-2 text-iron-700 transition hover:bg-iron-100"
              aria-label="Sign out"
              title="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
