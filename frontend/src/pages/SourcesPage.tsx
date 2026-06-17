import { useCallback, useEffect, useRef, useState } from "react";
import {
  BadgeCheck,
  ExternalLink,
  FileText,
  Globe,
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
import {
  addApprovedUrl,
  deleteApprovedUrl,
  listApprovedUrls,
} from "../api/sources";
import type { ApprovedUrl, DocumentRead } from "../api/types";
import StatusBadge from "../components/StatusBadge";

export default function SourcesPage() {
  const [urls, setUrls] = useState<ApprovedUrl[]>([]);
  const [docs, setDocs] = useState<DocumentRead[]>([]);
  const [url, setUrl] = useState("");
  const [label, setLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const refreshUrls = useCallback(async () => {
    setUrls(await listApprovedUrls());
  }, []);
  const refreshDocs = useCallback(async () => {
    setDocs(await listDocuments("reference"));
  }, []);

  useEffect(() => {
    refreshUrls().catch((e) => setErr(String(e instanceof Error ? e.message : e)));
    refreshDocs().catch((e) => setErr(String(e instanceof Error ? e.message : e)));
  }, [refreshUrls, refreshDocs]);

  // Polling mientras haya documentos indexándose.
  useEffect(() => {
    const pending = docs.some(
      (d) => d.status === "pending" || d.status === "processing"
    );
    if (!pending) return;
    const t = setInterval(() => {
      refreshDocs().catch(() => {});
    }, 2500);
    return () => clearInterval(t);
  }, [docs, refreshDocs]);

  async function onAddUrl() {
    const u = url.trim();
    if (!u) return;
    setErr(null);
    setBusy(true);
    try {
      await addApprovedUrl(u, label.trim() || undefined);
      setUrl("");
      setLabel("");
      setNotice("URL aprobada agregada.");
      await refreshUrls();
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(false);
    }
  }

  async function onDeleteUrl(id: string) {
    await deleteApprovedUrl(id);
    await refreshUrls();
  }

  async function onUpload(files: FileList | null) {
    if (!files || files.length === 0) return;
    setErr(null);
    setBusy(true);
    try {
      const res = await uploadDocuments(files, "reference");
      const parts = [`${res.documents.length} subido(s)`];
      if (res.duplicates.length) parts.push(`${res.duplicates.length} duplicado(s)`);
      if (res.rejected.length) parts.push(`${res.rejected.length} no soportado(s)`);
      setNotice(parts.join(" · "));
      await refreshDocs();
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
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
              Fuentes aprobadas
            </h1>
            <p className="mt-0.5 text-sm text-surface-500 dark:text-surface-400">
              Documentación autoritativa del fabricante (HPE QuickSpecs, guías de
              Aruba, Microsoft 365…) contra la que se validan las afirmaciones
              técnicas de las propuestas.
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

        {/* ── URLs aprobadas (búsqueda en vivo) ── */}
        <section className="mb-8">
          <div className="mb-2 flex items-center gap-2">
            <Globe className="h-4 w-4 text-brand-600 dark:text-brand-400" />
            <h2 className="text-sm font-bold text-surface-800 dark:text-surface-100">
              URLs aprobadas — búsqueda en vivo
            </h2>
          </div>
          <p className="mb-3 text-xs text-surface-500 dark:text-surface-400">
            El modelo descarga estas URLs <b>al momento de validar</b>. Usá enlaces
            directos a PDF o artículos (ej. un QuickSpec o una página de Microsoft
            365 Learn). Portales con login o JavaScript (Aruba, Seismic) no se
            pueden leer en vivo: para esos, subí el PDF abajo.
          </p>

          <div className="mb-3 flex flex-wrap items-end gap-2">
            <div className="min-w-[280px] flex-1">
              <div className="flex items-center gap-2 rounded-lg border border-surface-300 bg-white px-3 dark:border-surface-700 dark:bg-surface-900">
                <Link2 className="h-4 w-4 shrink-0 text-surface-400" />
                <input
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && onAddUrl()}
                  placeholder="https://www.hpe.com/…/quickspec.pdf"
                  className="w-full bg-transparent py-2 text-sm text-surface-800 placeholder:text-surface-400 focus:outline-none dark:text-surface-100 dark:placeholder:text-surface-500"
                />
              </div>
            </div>
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onAddUrl()}
              placeholder="Etiqueta (opcional)"
              className="w-44 rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-800 placeholder:text-surface-400 focus:outline-none dark:border-surface-700 dark:bg-surface-900 dark:text-surface-100 dark:placeholder:text-surface-500"
            />
            <button
              onClick={onAddUrl}
              disabled={busy || !url.trim()}
              className="btn-primary shrink-0"
            >
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Agregar URL"}
            </button>
          </div>

          <div className="overflow-hidden rounded-xl border border-surface-200 bg-white shadow-soft dark:border-surface-800 dark:bg-surface-800/40">
            {urls.length === 0 ? (
              <p className="px-5 py-8 text-center text-xs text-surface-400 dark:text-surface-500">
                Todavía no hay URLs aprobadas.
              </p>
            ) : (
              <ul className="divide-y divide-surface-100 dark:divide-surface-800">
                {urls.map((u) => (
                  <li key={u.id} className="flex items-center gap-3 px-5 py-3">
                    <Globe className="h-4 w-4 shrink-0 text-brand-500 dark:text-brand-400" />
                    <div className="min-w-0 flex-1">
                      {u.label && (
                        <div className="truncate text-sm font-medium text-surface-800 dark:text-surface-100">
                          {u.label}
                        </div>
                      )}
                      <a
                        href={u.url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1 truncate text-xs text-brand-600 hover:underline dark:text-brand-400"
                        title={u.url}
                      >
                        <ExternalLink className="h-3 w-3 shrink-0" />
                        <span className="truncate">{u.url}</span>
                      </a>
                    </div>
                    <button
                      onClick={() => onDeleteUrl(u.id)}
                      title="Quitar"
                      className="rounded-lg p-1.5 text-surface-400 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/10 dark:hover:text-red-400"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        {/* ── Documentos subidos (indexados) ── */}
        <section>
          <div className="mb-2 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-brand-600 dark:text-brand-400" />
              <h2 className="text-sm font-bold text-surface-800 dark:text-surface-100">
                Documentos subidos — indexados
              </h2>
            </div>
            <button
              onClick={() => fileRef.current?.click()}
              disabled={busy}
              className="inline-flex items-center gap-2 rounded-lg border border-surface-300 bg-white px-3.5 py-2 text-sm font-medium text-surface-700 shadow-soft transition hover:border-brand-300 hover:bg-surface-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:border-brand-600 dark:hover:bg-surface-700"
            >
              <Upload className="h-4 w-4 text-brand-600 dark:text-brand-400" />
              Subir PDF / archivo
            </button>
            <input
              ref={fileRef}
              type="file"
              multiple
              hidden
              onChange={(e) => onUpload(e.target.files)}
            />
          </div>
          <p className="mb-3 text-xs text-surface-500 dark:text-surface-400">
            Para fuentes con login o anti-bot (Aruba doc portal, HPE Seismic):
            descargá el PDF y subilo acá. Se indexa una vez y se consulta junto con
            las URLs en vivo.
          </p>

          <div className="overflow-hidden rounded-xl border border-surface-200 bg-white shadow-soft dark:border-surface-800 dark:bg-surface-800/40">
            <table className="w-full table-fixed text-sm">
              <thead>
                <tr className="border-b border-surface-200 bg-surface-50 text-left text-[11px] font-semibold uppercase tracking-wider text-surface-500 dark:border-surface-800 dark:bg-surface-800/60 dark:text-surface-400">
                  <th className="px-5 py-3">Documento</th>
                  <th className="w-32 px-5 py-3">Estado</th>
                  <th className="w-24 px-5 py-3">Fragmentos</th>
                  <th className="w-28 px-5 py-3 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100 dark:divide-surface-800">
                {docs.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-5 py-12 text-center">
                      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-surface-100 text-surface-400 dark:bg-surface-800 dark:text-surface-500">
                        <BadgeCheck className="h-6 w-6" />
                      </div>
                      <p className="mt-3 text-sm font-medium text-surface-600 dark:text-surface-300">
                        Sin documentos subidos
                      </p>
                    </td>
                  </tr>
                )}
                {docs.map((d) => (
                  <tr key={d.id} className="hover:bg-surface-50/50 dark:hover:bg-surface-800/30">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2.5">
                        <FileText className="h-4 w-4 shrink-0 text-surface-400 dark:text-surface-500" />
                        <span className="truncate font-medium text-surface-800 dark:text-surface-100" title={d.filename}>
                          {d.filename}
                        </span>
                      </div>
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
                          onClick={() => reindexDocument(d.id).then(refreshDocs)}
                          title="Reindexar"
                          className="rounded-lg p-1.5 text-surface-400 transition hover:bg-surface-100 hover:text-surface-700 dark:hover:bg-surface-700 dark:hover:text-surface-200"
                        >
                          <RotateCw className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => deleteDocument(d.id).then(refreshDocs)}
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
        </section>
      </div>
    </div>
  );
}
