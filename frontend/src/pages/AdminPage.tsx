import { useCallback, useEffect, useState, type ReactNode } from "react";
import {
  Building2,
  KeyRound,
  Loader2,
  ShieldCheck,
  UserPlus,
  Users,
  X,
} from "lucide-react";
import {
  changePassword,
  createOrganization,
  createUser,
  listOrganizations,
  listUsers,
} from "../api/admin";
import type { Organization, User, UserRole } from "../api/types";
import { useAuth } from "../context/AuthContext";

const errStr = (e: unknown) => String(e instanceof Error ? e.message : e);

/** Deriva un slug válido (^[a-z0-9-]{2,64}$) a partir del nombre. */
function slugify(name: string): string {
  return name
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);
}

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("es-MX", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function AdminPage() {
  const { user } = useAuth();
  const isSuper = user?.role === "superadmin";
  const isAdmin = user?.role === "admin";

  const [err, setErr] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl px-8 py-8">
        {/* Encabezado */}
        <div className="mb-6 flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-400">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-surface-900 dark:text-surface-50">
              Administración
            </h1>
            <p className="mt-0.5 text-sm text-surface-500 dark:text-surface-400">
              {isSuper
                ? "Creá organizaciones (cada una con su administrador inicial) y gestioná tu cuenta."
                : isAdmin
                  ? "Creá y gestioná los usuarios de tu organización."
                  : "Gestioná tu cuenta."}
            </p>
          </div>
        </div>

        {err && (
          <div className="mb-4 flex items-start justify-between gap-3 rounded-lg bg-red-50 px-4 py-2.5 text-sm text-red-600 ring-1 ring-red-100 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/20">
            <span>{err}</span>
            <button onClick={() => setErr(null)}>
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
        {notice && (
          <div className="mb-4 flex items-center justify-between gap-3 rounded-lg bg-brand-50 px-4 py-2.5 text-sm text-brand-700 ring-1 ring-brand-100 dark:bg-brand-500/10 dark:text-brand-300 dark:ring-brand-500/20">
            <span>{notice}</span>
            <button onClick={() => setNotice(null)}>
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {isSuper && <OrganizationsSection setErr={setErr} setNotice={setNotice} />}
        {isAdmin && <UsersSection setErr={setErr} setNotice={setNotice} />}
        <AccountSection setErr={setErr} setNotice={setNotice} />
      </div>
    </div>
  );
}

interface SectionProps {
  setErr: (s: string | null) => void;
  setNotice: (s: string | null) => void;
}

// ── Organizaciones (super-admin) ────────────────────────────────────────────────

function OrganizationsSection({ setErr, setNotice }: SectionProps) {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setOrgs(await listOrganizations());
  }, []);

  useEffect(() => {
    refresh().catch((e) => setErr(errStr(e)));
  }, [refresh, setErr]);

  const effectiveSlug = slugTouched ? slug : slugify(name);

  async function onCreate() {
    setErr(null);
    setBusy(true);
    try {
      await createOrganization({
        name: name.trim(),
        slug: effectiveSlug,
        admin_email: email.trim(),
        admin_password: password,
      });
      setNotice(`Organización "${name.trim()}" creada con su admin ${email.trim()}.`);
      setName("");
      setSlug("");
      setSlugTouched(false);
      setEmail("");
      setPassword("");
      await refresh();
    } catch (e) {
      setErr(errStr(e));
    } finally {
      setBusy(false);
    }
  }

  const valid =
    name.trim() &&
    /^[a-z0-9-]{2,64}$/.test(effectiveSlug) &&
    email.trim() &&
    password.length >= 8;

  return (
    <section className="mb-8">
      <div className="mb-2 flex items-center gap-2">
        <Building2 className="h-4 w-4 text-brand-600 dark:text-brand-400" />
        <h2 className="text-sm font-bold text-surface-800 dark:text-surface-100">
          Organizaciones
        </h2>
      </div>
      <p className="mb-3 text-xs text-surface-500 dark:text-surface-400">
        Al crear una organización se crea también su usuario <b>administrador</b>{" "}
        inicial. El admin podrá luego dar de alta a los demás usuarios.
      </p>

      <div className="mb-3 grid grid-cols-1 gap-2 rounded-xl border border-surface-200 bg-white p-4 shadow-soft dark:border-surface-800 dark:bg-surface-800/40 sm:grid-cols-2">
        <Field label="Nombre">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="CiiSA"
            className="adm-input"
          />
        </Field>
        <Field label="Slug" hint="minúsculas, números y guiones">
          <input
            value={effectiveSlug}
            onChange={(e) => {
              setSlugTouched(true);
              setSlug(e.target.value);
            }}
            placeholder="ciisa"
            className="adm-input"
          />
        </Field>
        <Field label="Email del admin">
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            placeholder="admin@ciisa.com"
            className="adm-input"
          />
        </Field>
        <Field label="Contraseña del admin" hint="mínimo 8 caracteres">
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            placeholder="••••••••"
            className="adm-input"
          />
        </Field>
        <div className="sm:col-span-2">
          <button
            onClick={onCreate}
            disabled={busy || !valid}
            className="btn-primary"
          >
            {busy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <Building2 className="h-4 w-4" /> Crear organización
              </>
            )}
          </button>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-surface-200 bg-white shadow-soft dark:border-surface-800 dark:bg-surface-800/40">
        {orgs.length === 0 ? (
          <p className="px-5 py-8 text-center text-xs text-surface-400 dark:text-surface-500">
            Todavía no hay organizaciones.
          </p>
        ) : (
          <table className="w-full table-fixed text-sm">
            <thead>
              <tr className="border-b border-surface-200 bg-surface-50 text-left text-[11px] font-semibold uppercase tracking-wider text-surface-500 dark:border-surface-800 dark:bg-surface-800/60 dark:text-surface-400">
                <th className="px-5 py-3">Nombre</th>
                <th className="px-5 py-3">Slug</th>
                <th className="w-32 px-5 py-3 text-right">Creada</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100 dark:divide-surface-800">
              {orgs.map((o) => (
                <tr key={o.id} className="hover:bg-surface-50/50 dark:hover:bg-surface-800/30">
                  <td className="px-5 py-3 font-medium text-surface-800 dark:text-surface-100">
                    {o.name}
                  </td>
                  <td className="px-5 py-3">
                    <code className="rounded bg-surface-100 px-1.5 py-0.5 text-xs text-surface-600 dark:bg-surface-800 dark:text-surface-300">
                      {o.slug}
                    </code>
                  </td>
                  <td className="px-5 py-3 text-right text-xs text-surface-500 dark:text-surface-400">
                    {fmtDate(o.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

// ── Usuarios de la organización (admin) ─────────────────────────────────────────

function UsersSection({ setErr, setNotice }: SectionProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Exclude<UserRole, "superadmin">>("member");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setUsers(await listUsers());
  }, []);

  useEffect(() => {
    refresh().catch((e) => setErr(errStr(e)));
  }, [refresh, setErr]);

  async function onCreate() {
    setErr(null);
    setBusy(true);
    try {
      await createUser({ email: email.trim(), password, role });
      setNotice(`Usuario ${email.trim()} creado.`);
      setEmail("");
      setPassword("");
      setRole("member");
      await refresh();
    } catch (e) {
      setErr(errStr(e));
    } finally {
      setBusy(false);
    }
  }

  const valid = email.trim() && password.length >= 8;

  return (
    <section className="mb-8">
      <div className="mb-2 flex items-center gap-2">
        <Users className="h-4 w-4 text-brand-600 dark:text-brand-400" />
        <h2 className="text-sm font-bold text-surface-800 dark:text-surface-100">
          Usuarios de la organización
        </h2>
      </div>

      <div className="mb-3 flex flex-wrap items-end gap-2 rounded-xl border border-surface-200 bg-white p-4 shadow-soft dark:border-surface-800 dark:bg-surface-800/40">
        <div className="min-w-[220px] flex-1">
          <Field label="Email">
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              placeholder="usuario@ciisa.com"
              className="adm-input"
            />
          </Field>
        </div>
        <div className="w-44">
          <Field label="Contraseña" hint="mínimo 8">
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              placeholder="••••••••"
              className="adm-input"
            />
          </Field>
        </div>
        <div className="w-36">
          <Field label="Rol">
            <select
              value={role}
              onChange={(e) =>
                setRole(e.target.value as Exclude<UserRole, "superadmin">)
              }
              className="adm-input"
            >
              <option value="member">Miembro</option>
              <option value="admin">Administrador</option>
            </select>
          </Field>
        </div>
        <button onClick={onCreate} disabled={busy || !valid} className="btn-primary">
          {busy ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <>
              <UserPlus className="h-4 w-4" /> Crear usuario
            </>
          )}
        </button>
      </div>

      <div className="overflow-hidden rounded-xl border border-surface-200 bg-white shadow-soft dark:border-surface-800 dark:bg-surface-800/40">
        {users.length === 0 ? (
          <p className="px-5 py-8 text-center text-xs text-surface-400 dark:text-surface-500">
            Todavía no hay usuarios.
          </p>
        ) : (
          <table className="w-full table-fixed text-sm">
            <thead>
              <tr className="border-b border-surface-200 bg-surface-50 text-left text-[11px] font-semibold uppercase tracking-wider text-surface-500 dark:border-surface-800 dark:bg-surface-800/60 dark:text-surface-400">
                <th className="px-5 py-3">Email</th>
                <th className="w-32 px-5 py-3">Rol</th>
                <th className="w-24 px-5 py-3">Estado</th>
                <th className="w-32 px-5 py-3 text-right">Creado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100 dark:divide-surface-800">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-surface-50/50 dark:hover:bg-surface-800/30">
                  <td className="px-5 py-3 font-medium text-surface-800 dark:text-surface-100">
                    {u.email}
                  </td>
                  <td className="px-5 py-3 capitalize text-surface-600 dark:text-surface-300">
                    {u.role}
                  </td>
                  <td className="px-5 py-3">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${
                        u.is_active
                          ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400"
                          : "bg-surface-100 text-surface-500 dark:bg-surface-800 dark:text-surface-400"
                      }`}
                    >
                      {u.is_active ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right text-xs text-surface-500 dark:text-surface-400">
                    {fmtDate(u.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

// ── Cuenta propia: cambio de contraseña ──────────────────────────────────────────

function AccountSection({ setErr, setNotice }: SectionProps) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);

  async function onChange() {
    if (next !== confirm) {
      setErr("La nueva contraseña y su confirmación no coinciden.");
      return;
    }
    setErr(null);
    setBusy(true);
    try {
      await changePassword(current, next);
      setNotice("Contraseña actualizada.");
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (e) {
      setErr(errStr(e));
    } finally {
      setBusy(false);
    }
  }

  const valid = current && next.length >= 8 && confirm;

  return (
    <section>
      <div className="mb-2 flex items-center gap-2">
        <KeyRound className="h-4 w-4 text-brand-600 dark:text-brand-400" />
        <h2 className="text-sm font-bold text-surface-800 dark:text-surface-100">
          Mi contraseña
        </h2>
      </div>

      <div className="flex flex-wrap items-end gap-2 rounded-xl border border-surface-200 bg-white p-4 shadow-soft dark:border-surface-800 dark:bg-surface-800/40">
        <div className="w-48">
          <Field label="Contraseña actual">
            <input
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              type="password"
              placeholder="••••••••"
              className="adm-input"
            />
          </Field>
        </div>
        <div className="w-48">
          <Field label="Nueva contraseña" hint="mínimo 8">
            <input
              value={next}
              onChange={(e) => setNext(e.target.value)}
              type="password"
              placeholder="••••••••"
              className="adm-input"
            />
          </Field>
        </div>
        <div className="w-48">
          <Field label="Confirmar">
            <input
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              type="password"
              placeholder="••••••••"
              className="adm-input"
            />
          </Field>
        </div>
        <button onClick={onChange} disabled={busy || !valid} className="btn-primary">
          {busy ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <>
              <KeyRound className="h-4 w-4" /> Cambiar
            </>
          )}
        </button>
      </div>
    </section>
  );
}

// ── Helper de campo etiquetado ───────────────────────────────────────────────────

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
        {label}
        {hint && (
          <span className="ml-1 font-normal normal-case text-surface-400 dark:text-surface-500">
            ({hint})
          </span>
        )}
      </span>
      {children}
    </label>
  );
}
