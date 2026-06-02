import { useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import {
  Library,
  MessagesSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Sparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import ChatPage from "./pages/ChatPage";
import LibraryPage from "./pages/LibraryPage";
import ThemeToggle from "./components/ThemeToggle";

const COLLAPSE_KEY = "aidoc-sidebar-collapsed";

function NavItem({
  to,
  label,
  icon: Icon,
  collapsed,
}: {
  to: string;
  label: string;
  icon: LucideIcon;
  collapsed: boolean;
}) {
  return (
    <NavLink
      to={to}
      title={collapsed ? label : undefined}
      className={({ isActive }) =>
        `group flex items-center rounded-lg text-sm font-medium transition ${
          collapsed ? "justify-center px-0 py-2.5" : "gap-3 px-3 py-2"
        } ${
          isActive
            ? "bg-brand text-white shadow-soft dark:bg-brand-500"
            : "text-surface-600 hover:bg-surface-100 hover:text-surface-900 dark:text-surface-400 dark:hover:bg-surface-800 dark:hover:text-surface-100"
        }`
      }
    >
      <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={2} />
      {!collapsed && label}
    </NavLink>
  );
}

export default function App() {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(COLLAPSE_KEY) === "1";
    } catch {
      return false;
    }
  });

  function toggle() {
    setCollapsed((c) => {
      const next = !c;
      try {
        localStorage.setItem(COLLAPSE_KEY, next ? "1" : "0");
      } catch {
        /* ignore */
      }
      return next;
    });
  }

  return (
    <div className="flex h-full bg-surface-50 dark:bg-surface-900">
      <aside
        className={`flex shrink-0 flex-col border-r border-surface-200 bg-white transition-all duration-200 dark:border-surface-800 dark:bg-surface-900 ${
          collapsed ? "w-[72px]" : "w-60"
        }`}
      >
        {/* Logo + toggle */}
        <div
          className={`flex items-center py-5 ${
            collapsed ? "flex-col gap-3 px-3" : "gap-2.5 px-5"
          }`}
        >
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand text-white shadow-soft dark:bg-brand-500">
            <Sparkles className="h-5 w-5" strokeWidth={2.2} />
          </div>
          {!collapsed && (
            <div className="flex-1 leading-tight">
              <div className="text-[15px] font-bold tracking-tight text-surface-900 dark:text-surface-50">
                AIDOC
              </div>
              <div className="text-[11px] font-medium text-surface-400 dark:text-surface-500">
                Documentos con IA
              </div>
            </div>
          )}
          <button
            onClick={toggle}
            title={collapsed ? "Expandir menú" : "Contraer menú"}
            aria-label={collapsed ? "Expandir menú" : "Contraer menú"}
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-surface-400 transition hover:bg-surface-100 hover:text-surface-700 dark:text-surface-500 dark:hover:bg-surface-800 dark:hover:text-surface-200"
          >
            {collapsed ? (
              <PanelLeftOpen className="h-[18px] w-[18px]" />
            ) : (
              <PanelLeftClose className="h-[18px] w-[18px]" />
            )}
          </button>
        </div>

        {/* Navegación */}
        <nav className={`flex flex-col gap-1 py-2 ${collapsed ? "px-2" : "px-3"}`}>
          {!collapsed && (
            <p className="px-3 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-surface-400 dark:text-surface-500">
              Espacio de trabajo
            </p>
          )}
          <NavItem to="/library" label="Biblioteca" icon={Library} collapsed={collapsed} />
          <NavItem to="/chat" label="Chat" icon={MessagesSquare} collapsed={collapsed} />
        </nav>

        {/* Footer */}
        <div
          className={`mt-auto flex items-center py-4 ${
            collapsed ? "flex-col gap-3 px-2" : "justify-between gap-2 px-3"
          }`}
        >
          {collapsed ? (
            <span
              className="relative flex h-2.5 w-2.5"
              title="Conectado"
            >
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent-400 opacity-75" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-accent-500" />
            </span>
          ) : (
            <div className="flex flex-1 items-center gap-2 rounded-lg bg-surface-50 px-3 py-2.5 ring-1 ring-surface-200 dark:bg-surface-800 dark:ring-surface-700">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-accent-500" />
              </span>
              <span className="text-xs font-medium text-surface-500 dark:text-surface-400">
                Conectado
              </span>
            </div>
          )}
          <ThemeToggle />
        </div>
      </aside>

      <main className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={<Navigate to="/library" replace />} />
          <Route path="/library" element={<LibraryPage />} />
          <Route path="/chat" element={<ChatPage />} />
        </Routes>
      </main>
    </div>
  );
}
