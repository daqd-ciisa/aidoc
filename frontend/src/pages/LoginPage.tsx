import { useState } from "react";
import { Loader2, LogIn, Sparkles } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await login(email.trim(), password);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full items-center justify-center bg-surface-50 px-4 dark:bg-surface-900">
      <div className="w-full max-w-sm animate-fade-in">
        {/* Marca */}
        <div className="mb-7 flex flex-col items-center text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand text-white shadow-card dark:bg-brand-500">
            <Sparkles className="h-6 w-6" strokeWidth={2.2} />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-surface-900 dark:text-surface-50">
            AIDOC
          </h1>
          <p className="mt-1 text-sm text-surface-500 dark:text-surface-400">
            Ingresá a tu espacio de documentos
          </p>
        </div>

        <form
          onSubmit={onSubmit}
          className="rounded-2xl border border-surface-200 bg-white p-6 shadow-card dark:border-surface-800 dark:bg-surface-800"
        >
          <label className="mb-1 block text-sm font-medium text-surface-700 dark:text-surface-200">
            Email
          </label>
          <input
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="vos@empresa.com"
            className="mb-4 w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-800 outline-none transition focus:border-brand-400 focus:ring-2 focus:ring-brand-100 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-100 dark:focus:border-brand-500 dark:focus:ring-brand-500/20"
          />

          <label className="mb-1 block text-sm font-medium text-surface-700 dark:text-surface-200">
            Contraseña
          </label>
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="mb-4 w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-800 outline-none transition focus:border-brand-400 focus:ring-2 focus:ring-brand-100 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-100 dark:focus:border-brand-500 dark:focus:ring-brand-500/20"
          />

          {err && (
            <div className="mb-4 rounded-lg bg-red-50 px-3 py-2.5 text-xs text-red-600 ring-1 ring-red-200 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/30">
              {err}
            </div>
          )}

          <button
            type="submit"
            disabled={busy}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-white shadow-soft transition hover:bg-brand-600 disabled:opacity-60 dark:bg-brand-500 dark:hover:bg-brand-400"
          >
            {busy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <LogIn className="h-4 w-4" />
            )}
            {busy ? "Ingresando…" : "Ingresar"}
          </button>
        </form>

        <p className="mt-4 text-center text-[11px] text-surface-400 dark:text-surface-500">
          ¿No tenés acceso? Pedí a tu administrador que te cree una cuenta.
        </p>
      </div>
    </div>
  );
}
