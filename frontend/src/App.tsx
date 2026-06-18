import { useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import {
  Library,
  Loader2,
  LogOut,
  MessagesSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Receipt,
  ShieldCheck,
  Shield,
  Sparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import ChatPage from "./pages/ChatPage";
import LibraryPage from "./pages/LibraryPage";
import QuotesPage from "./pages/QuotesPage";
import SourcesPage from "./pages/SourcesPage";
import AdminPage from "./pages/AdminPage";
import LoginPage from "./pages/LoginPage";
import ThemeToggle from "./components/ThemeToggle";
import { useAuth } from "./context/AuthContext";

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

  const { user, loading, logout } = useAuth();
  // El super-admin no pertenece a una organización: las páginas de datos
  // (Biblioteca/Chat/…) le fallan, así que solo ve Administración.
  const isSuper = user?.role === "superadmin";
  const canAdmin = isSuper || user?.role === "admin";
  const home = isSuper ? "/admin" : "/library";

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

  // Gate de autenticación: sin sesión válida no se renderiza la app.
  if (loading) {
    return (
      <div className="flex h-full items-center justify-center bg-surface-50 dark:bg-surface-900">
        <Loader2 className="h-6 w-6 animate-spin text-brand-500" />
      </div>
    );
  }
  if (!user) return <LoginPage />;

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
          {!isSuper && (
            <>
              <NavItem to="/library" label="Biblioteca" icon={Library} collapsed={collapsed} />
              <NavItem to="/sources" label="Fuentes externas" icon={ShieldCheck} collapsed={collapsed} />
              <NavItem to="/chat" label="Chat" icon={MessagesSquare} collapsed={collapsed} />
              <NavItem to="/quotes" label="Cotizaciones" icon={Receipt} collapsed={collapsed} />
            </>
          )}
          {canAdmin && (
            <NavItem to="/admin" label="Administración" icon={Shield} collapsed={collapsed} />
          )}
        </nav>

        {/* Footer: usuario + sesión */}
        <div className={`mt-auto flex flex-col gap-2 py-4 ${collapsed ? "px-2" : "px-3"}`}>
          {!collapsed && (
            <div className="rounded-lg bg-surface-50 px-3 py-2.5 ring-1 ring-surface-200 dark:bg-surface-800 dark:ring-surface-700">
              <div
                className="truncate text-xs font-semibold text-surface-700 dark:text-surface-200"
                title={user.email}
              >
                {user.email}
              </div>
              <div className="mt-0.5 text-[11px] capitalize text-surface-400 dark:text-surface-500">
                {user.role}
              </div>
            </div>
          )}
          <div
            className={`flex items-center ${
              collapsed ? "flex-col gap-3" : "justify-between gap-2"
            }`}
          >
            <button
              onClick={logout}
              title="Cerrar sesión"
              className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium text-surface-500 transition hover:bg-red-50 hover:text-red-600 dark:text-surface-400 dark:hover:bg-red-500/10 dark:hover:text-red-400"
            >
              <LogOut className="h-4 w-4" />
              {!collapsed && "Salir"}
            </button>
            <ThemeToggle />
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={<Navigate to={home} replace />} />
          <Route path="/library" element={<LibraryPage />} />
          <Route path="/sources" element={<SourcesPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/quotes" element={<QuotesPage />} />
          {canAdmin && <Route path="/admin" element={<AdminPage />} />}
          <Route path="*" element={<Navigate to={home} replace />} />
        </Routes>
      </main>
    </div>
  );
}
