import { useCallback, useEffect, useRef, useState } from "react";
import {
  BadgeCheck,
  ExternalLink,
  FileText,
  Link2,
  Loader2,
  RotateCw,
  ShieldCheck,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import {
  deleteDocument,
  listDocuments,
  reindexDocument,
  uploadDocuments,
} from "../api/documents";
import { importFromUrl } from "../api/connectors";
import type { DocumentRead } from "../api/types";
import StatusBadge from "../components/StatusBadge";

// Presets de fabricante/tipo de las fuentes aprobadas (campo `vendor`).
const VENDORS = [
  "HPE QuickSpecs",
  "HPE Seismic",
  "HPE Aruba",
  "Microsoft 365",
  "Otro",
];

export default function SourcesPage() {
  const [docs, setDocs] = useState<DocumentRead[]>([]);
  const [vendor, setVendor] = useState(VENDORS[0]);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    setDocs(await listDocuments("reference"));
  }, []);

  useEffect(() => {
    refresh().catch((e) => setErr(String(e instanceof Error ? e.message : e)));
  }, [refresh]);

  // Polling mientras haya fuentes indexándose.
  useEffect(() => {
    const pending = docs.some(
      (d) => d.status === "pending" || d.status === "processing"
    );
    if (!pending) return;
    const t = setInterval(() => {
      refresh().catch(() => {});
    }, 2500);
    return () => clearInterval(t);
  }, [docs, refresh]);

  function summarize(res: {
    documents: unknown[];
    duplicates: string[];
    rejected: string[];
    failed?: string[];
  }) {
    const parts = [`${res.documents.length} agregada(s)`];
    if (res.duplicates.length) parts.push(`${res.duplicates.length} duplicada(s)`);
    if (res.rejected.length) parts.push(`${res.rejected.length} no soportada(s)`);
    if (res.failed?.length) parts.push(`${res.failed.length} con error`);
    setNotice(parts.join(" · "));
  }

  async function onUpload(files: FileList | null) {
    if (!files || files.length === 0) return;
    setErr(null);
    setBusy(true);
    try {
      const res = await uploadDocuments(files, "reference", vendor);
      summarize(res);
      await refresh();
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function onImportUrl() {
    const u = url.trim();
    if (!u) return;
    setErr(null);
    setBusy(true);
    try {
      const res = await importFromUrl(u, vendor, "reference");
      summarize(res);
      setUrl("");
      await refresh();
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(false);
    }
  }

  async function onReindex(id: string) {
    await reindexDocument(id);
    await refresh();
  }

  async function onDelete(id: string) {
    await deleteDocument(id);
    await refresh();
  }

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
              Fuentes externas
            </h1>
            <p className="mt-0.5 text-sm text-surface-500 dark:text-surface-400">
              Documentación aprobada del fabricante (HPE QuickSpecs, guías
              validadas de Aruba, Microsoft 365…) para validar las afirmaciones
              técnicas de las propuestas.
            </p>
          </div>
        </div>

        {/* Alta de fuente */}
        <div className="mb-5 rounded-xl border border-surface-200 bg-white p-4 shadow-soft dark:border-surface-800 dark:bg-surface-800/40">
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-surface-500 dark:text-surface-400">
                Fabricante / tipo
              </label>
              <select
                value={vendor}
                onChange={(e) => setVendor(e.target.value)}
                className="rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-800 focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-100 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-100"
              >
                {VENDORS.map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </select>
            </div>
            <div className="min-w-[260px] flex-1">
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-surface-500 dark:text-surface-400">
                Por URL (web pública)
              </label>
              <div className="flex gap-2">
                <div className="flex flex-1 items-center gap-2 rounded-lg border border-surface-300 bg-white px-3 dark:border-surface-700 dark:bg-surface-900">
                  <Link2 className="h-4 w-4 shrink-0 text-surface-400" />
                  <input
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && onImportUrl()}
                    placeholder="https://www.hpe.com/…/quickspecs.pdf"
                    className="w-full bg-transparent py-2 text-sm text-surface-800 placeholder:text-surface-400 focus:outline-none dark:text-surface-100 dark:placeholder:text-surface-500"
                  />
                </div>
                <button
                  onClick={onImportUrl}
                  disabled={busy || !url.trim()}
                  className="btn-primary shrink-0"
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Importar"}
                </button>
              </div>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-surface-500 dark:text-surface-400">
                O subir archivo
              </label>
              <button
                onClick={() => fileRef.current?.click()}
                disabled={busy}
                className="inline-flex items-center gap-2 rounded-lg border border-surface-300 bg-white px-3.5 py-2 text-sm font-medium text-surface-700 shadow-soft transition hover:border-brand-300 hover:bg-surface-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:border-brand-600 dark:hover:bg-surface-700"
              >
                <Upload className="h-4 w-4 text-brand-600 dark:text-brand-400" />
                PDF / archivo
              </button>
              <input
                ref={fileRef}
                type="file"
                multiple
                hidden
                onChange={(e) => onUpload(e.target.files)}
              />
            </div>
          </div>
          <p className="mt-3 text-xs text-surface-400 dark:text-surface-500">
            Portales con login o muy dependientes de JavaScript (Aruba doc portal,
            HPE Seismic) suelen no extraer texto por URL: para esos, subí el PDF.
          </p>
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

        {/* Tabla de fuentes */}
        <div className="overflow-hidden rounded-xl border border-surface-200 bg-white shadow-soft dark:border-surface-800 dark:bg-surface-800/40">
          <table className="w-full table-fixed text-sm">
            <thead>
              <tr className="border-b border-surface-200 bg-surface-50 text-left text-[11px] font-semibold uppercase tracking-wider text-surface-500 dark:border-surface-800 dark:bg-surface-800/60 dark:text-surface-400">
                <th className="px-5 py-3">Fuente</th>
                <th className="w-44 px-5 py-3">Fabricante / tipo</th>
                <th className="w-32 px-5 py-3">Estado</th>
                <th className="w-24 px-5 py-3">Fragmentos</th>
                <th className="w-28 px-5 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100 dark:divide-surface-800">
              {docs.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-5 py-16 text-center">
                    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-surface-100 text-surface-400 dark:bg-surface-800 dark:text-surface-500">
                      <BadgeCheck className="h-6 w-6" />
                    </div>
                    <p className="mt-3 text-sm font-medium text-surface-600 dark:text-surface-300">
                      Todavía no hay fuentes aprobadas
                    </p>
                    <p className="mt-1 text-xs text-surface-400 dark:text-surface-500">
                      Agregá QuickSpecs, guías validadas o docs de Microsoft 365.
                    </p>
                  </td>
                </tr>
              )}
              {docs.map((d) => (
                <tr key={d.id} className="hover:bg-surface-50/50 dark:hover:bg-surface-800/30">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2.5">
                      <FileText className="h-4 w-4 shrink-0 text-surface-400 dark:text-surface-500" />
                      <div className="min-w-0">
                        <div className="truncate font-medium text-surface-800 dark:text-surface-100" title={d.filename}>
                          {d.filename}
                        </div>
                        {d.origin_url && (
                          <a
                            href={d.origin_url}
                            target="_blank"
                            rel="noreferrer"
                            className="mt-0.5 flex items-center gap-1 truncate text-xs text-brand-600 hover:underline dark:text-brand-400"
                            title={d.origin_url}
                          >
                            <ExternalLink className="h-3 w-3 shrink-0" />
                            <span className="truncate">{d.origin_url}</span>
                          </a>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-5 py-3">
                    {d.vendor ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700 ring-1 ring-brand-100 dark:bg-brand-500/10 dark:text-brand-300 dark:ring-brand-500/20">
                        <ShieldCheck className="h-3 w-3" />
                        {d.vendor}
                      </span>
                    ) : (
                      <span className="text-xs text-surface-400">—</span>
                    )}
                  </td>
                  <td className="px-5 py-3">
                    <StatusBadge status={d.status} />
                  </td>
                  <td className="px-5 py-3 tabular-nums text-surface-600 dark:text-surface-300">
                    {d.chunk_count || "—"}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => onReindex(d.id)}
                        title="Reindexar"
                        className="rounded-lg p-1.5 text-surface-400 transition hover:bg-surface-100 hover:text-surface-700 dark:hover:bg-surface-700 dark:hover:text-surface-200"
                      >
                        <RotateCw className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => onDelete(d.id)}
                        title="Borrar"
                        className="rounded-lg p-1.5 text-surface-400 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/10 dark:hover:text-red-400"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
