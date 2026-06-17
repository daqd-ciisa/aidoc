import { useCallback, useEffect, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  FileText,
  Folder,
  Library,
  Loader2,
  Search,
  Share2,
  X,
} from "lucide-react";
import type { ImportResult, SharePointFile } from "../api/connectors";
import { importFromSharePoint } from "../api/connectors";
import {
  getSharePointToken,
  isSharePointConfigured,
  listChildren,
  listDrives,
  searchSites,
  setSharePointClientId,
  type DriveItem,
  type DriveLib,
  type SiteItem,
} from "../lib/sharePoint";

type Step = "config" | "loading" | "sites" | "drives" | "files" | "importing";
interface Crumb {
  id?: string;
  name: string;
}

export default function SharePointPickerModal({
  onClose,
  onImported,
}: {
  onClose: () => void;
  onImported: (res: ImportResult) => void;
}) {
  const [step, setStep] = useState<Step>(
    isSharePointConfigured() ? "loading" : "config"
  );
  const [clientId, setClientId] = useState("");
  const [token, setToken] = useState<string | null>(null);

  const [siteQuery, setSiteQuery] = useState("");
  const [sites, setSites] = useState<SiteItem[]>([]);
  const [site, setSite] = useState<SiteItem | null>(null);
  const [drives, setDrives] = useState<DriveLib[]>([]);
  const [drive, setDrive] = useState<DriveLib | null>(null);

  const [crumbs, setCrumbs] = useState<Crumb[]>([]);
  const [items, setItems] = useState<DriveItem[]>([]);
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const findSites = useCallback(async (tok: string, query: string) => {
    setErr(null);
    setBusy(true);
    try {
      setSites(await searchSites(tok, query));
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(false);
    }
  }, []);

  const connect = useCallback(async () => {
    setStep("loading");
    setErr(null);
    try {
      const tok = await getSharePointToken();
      setToken(tok);
      setStep("sites");
      await findSites(tok, "");
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
      setStep(isSharePointConfigured() ? "sites" : "config");
    }
  }, [findSites]);

  useEffect(() => {
    if (isSharePointConfigured()) connect();
  }, [connect]);

  function saveConfig() {
    if (!clientId.trim()) return;
    setSharePointClientId(clientId);
    connect();
  }

  async function openSite(s: SiteItem) {
    if (!token) return;
    setSite(s);
    setStep("drives");
    setErr(null);
    setBusy(true);
    try {
      setDrives(await listDrives(token, s.id));
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(false);
    }
  }

  async function loadFolder(driveId: string, folderId?: string) {
    if (!token || !site) return;
    setErr(null);
    setBusy(true);
    try {
      setItems(await listChildren(token, site.id, driveId, folderId));
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(false);
    }
  }

  async function openDrive(d: DriveLib) {
    setDrive(d);
    setCrumbs([{ name: d.name }]);
    setSelected({});
    setStep("files");
    await loadFolder(d.id);
  }

  async function openFolder(item: DriveItem) {
    if (!drive) return;
    setCrumbs((c) => [...c, { id: item.id, name: item.name }]);
    await loadFolder(drive.id, item.id);
  }

  async function goTo(idx: number) {
    if (!drive) return;
    const next = crumbs.slice(0, idx + 1);
    setCrumbs(next);
    await loadFolder(drive.id, next[next.length - 1].id);
  }

  function toggle(item: DriveItem) {
    setSelected((s) => {
      const copy = { ...s };
      if (copy[item.id]) delete copy[item.id];
      else copy[item.id] = item.name;
      return copy;
    });
  }

  async function doImport() {
    if (!token || !site || !drive) return;
    const files: SharePointFile[] = Object.entries(selected).map(
      ([id, name]) => ({ id, name, site_id: site.id, drive_id: drive.id })
    );
    if (files.length === 0) return;
    setStep("importing");
    try {
      const res = await importFromSharePoint(token, files);
      onImported(res);
      onClose();
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
      setStep("files");
    }
  }

  const selectedCount = Object.keys(selected).length;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-surface-900/40 p-4 backdrop-blur-sm animate-fade-in dark:bg-black/60"
      onClick={onClose}
    >
      <div
        className="flex max-h-[85vh] w-full max-w-lg flex-col overflow-hidden rounded-2xl bg-white shadow-pop animate-scale-in dark:bg-surface-800"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-surface-200 px-6 py-4 dark:border-surface-700">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-400">
              <Share2 className="h-5 w-5" />
            </div>
            <h2 className="text-base font-bold text-surface-900 dark:text-surface-50">
              Importar de SharePoint
            </h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-surface-400 transition hover:bg-surface-100 hover:text-surface-700 dark:text-surface-500 dark:hover:bg-surface-700 dark:hover:text-surface-200"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {err && (
          <div className="mx-6 mt-4 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600 ring-1 ring-red-100 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/20">
            {err}
          </div>
        )}

        {/* Config */}
        {step === "config" && (
          <div className="px-6 py-5">
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-surface-500 dark:text-surface-400">
              Client ID (App registration de Azure, SPA)
            </label>
            <input
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              placeholder="00000000-0000-0000-0000-000000000000"
              className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-800 placeholder:text-surface-400 focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-100 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-100 dark:placeholder:text-surface-500 dark:focus:border-brand-600 dark:focus:ring-brand-500/20"
            />
            <div className="mt-3 rounded-lg bg-surface-50 px-3 py-2.5 text-xs text-surface-500 ring-1 ring-surface-200 dark:bg-surface-900/50 dark:text-surface-400 dark:ring-surface-700">
              Misma App registration que OneDrive (tipo <b>SPA</b>, URI{" "}
              <code className="rounded bg-surface-200 px-1 dark:bg-surface-700">
                {window.location.origin}
              </code>
              ), pero requiere el permiso de Graph <b>Sites.Read.All</b>{" "}
              (delegado) con <b>consentimiento del administrador</b> del tenant.
              <a
                href="https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade"
                target="_blank"
                rel="noreferrer"
                className="mt-1.5 flex items-center gap-1 font-medium text-brand-600 hover:underline dark:text-brand-400"
              >
                Abrir Registros de aplicaciones <ExternalLink className="h-3 w-3" />
              </a>
            </div>
            <button
              onClick={saveConfig}
              disabled={!clientId.trim()}
              className="btn-primary mt-4 w-full"
            >
              Guardar y conectar
            </button>
          </div>
        )}

        {/* Loading */}
        {step === "loading" && (
          <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
            <Loader2 className="h-6 w-6 animate-spin text-brand-500" />
            <p className="mt-3 text-sm text-surface-500 dark:text-surface-400">
              Conectando con Microsoft…
            </p>
          </div>
        )}

        {/* Sites */}
        {step === "sites" && (
          <>
            <div className="border-b border-surface-200 px-6 py-3 dark:border-surface-700">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (token) findSites(token, siteQuery);
                }}
                className="flex items-center gap-2 rounded-lg border border-surface-300 bg-white px-3 py-1.5 dark:border-surface-700 dark:bg-surface-900"
              >
                <Search className="h-4 w-4 shrink-0 text-surface-400" />
                <input
                  value={siteQuery}
                  onChange={(e) => setSiteQuery(e.target.value)}
                  placeholder="Buscar sitio de SharePoint…"
                  className="w-full bg-transparent text-sm text-surface-800 placeholder:text-surface-400 focus:outline-none dark:text-surface-100 dark:placeholder:text-surface-500"
                />
              </form>
            </div>
            <div className="flex-1 overflow-y-auto px-3 py-2">
              {busy ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin text-brand-500" />
                </div>
              ) : sites.length === 0 ? (
                <p className="px-3 py-6 text-center text-xs text-surface-400 dark:text-surface-500">
                  No se encontraron sitios.
                </p>
              ) : (
                sites.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => openSite(s)}
                    className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition hover:bg-surface-50 dark:hover:bg-surface-700"
                  >
                    <Share2 className="h-4 w-4 shrink-0 text-brand-500 dark:text-brand-400" />
                    <span className="flex-1 truncate text-surface-700 dark:text-surface-200">
                      {s.name}
                    </span>
                    <ChevronRight className="h-4 w-4 text-surface-300" />
                  </button>
                ))
              )}
            </div>
          </>
        )}

        {/* Drives (bibliotecas) */}
        {step === "drives" && (
          <>
            <div className="flex items-center gap-2 border-b border-surface-200 px-6 py-2.5 text-xs text-surface-500 dark:border-surface-700 dark:text-surface-400">
              <button
                onClick={() => setStep("sites")}
                className="flex items-center gap-1 rounded px-1 py-0.5 hover:text-surface-800 hover:underline dark:hover:text-surface-100"
              >
                <ChevronLeft className="h-3 w-3" /> Sitios
              </button>
              <ChevronRight className="h-3 w-3 text-surface-300" />
              <span className="truncate font-medium text-surface-700 dark:text-surface-200">
                {site?.name}
              </span>
            </div>
            <div className="flex-1 overflow-y-auto px-3 py-2">
              {busy ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin text-brand-500" />
                </div>
              ) : drives.length === 0 ? (
                <p className="px-3 py-6 text-center text-xs text-surface-400 dark:text-surface-500">
                  Este sitio no tiene bibliotecas de documentos.
                </p>
              ) : (
                drives.map((d) => (
                  <button
                    key={d.id}
                    onClick={() => openDrive(d)}
                    className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition hover:bg-surface-50 dark:hover:bg-surface-700"
                  >
                    <Library className="h-4 w-4 shrink-0 text-brand-500 dark:text-brand-400" />
                    <span className="flex-1 truncate text-surface-700 dark:text-surface-200">
                      {d.name}
                    </span>
                    <ChevronRight className="h-4 w-4 text-surface-300" />
                  </button>
                ))
              )}
            </div>
          </>
        )}

        {/* Files (carpetas + archivos) */}
        {step === "files" && (
          <>
            <div className="flex flex-wrap items-center gap-1 border-b border-surface-200 px-6 py-2.5 text-xs text-surface-500 dark:border-surface-700 dark:text-surface-400">
              <button
                onClick={() => setStep("drives")}
                className="flex items-center gap-1 rounded px-1 py-0.5 hover:text-surface-800 hover:underline dark:hover:text-surface-100"
              >
                <ChevronLeft className="h-3 w-3" /> Bibliotecas
              </button>
              {crumbs.map((c, i) => (
                <span key={i} className="flex items-center gap-1">
                  <ChevronRight className="h-3 w-3 text-surface-300" />
                  <button
                    onClick={() => goTo(i)}
                    className="rounded px-1 py-0.5 hover:text-surface-800 hover:underline dark:hover:text-surface-100"
                  >
                    {c.name}
                  </button>
                </span>
              ))}
            </div>
            <div className="flex-1 overflow-y-auto px-3 py-2">
              {busy ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin text-brand-500" />
                </div>
              ) : items.length === 0 ? (
                <p className="px-3 py-6 text-center text-xs text-surface-400 dark:text-surface-500">
                  Carpeta vacía.
                </p>
              ) : (
                items.map((it) =>
                  it.isFolder ? (
                    <button
                      key={it.id}
                      onClick={() => openFolder(it)}
                      className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition hover:bg-surface-50 dark:hover:bg-surface-700"
                    >
                      <Folder className="h-4 w-4 shrink-0 text-brand-500 dark:text-brand-400" />
                      <span className="flex-1 truncate text-surface-700 dark:text-surface-200">
                        {it.name}
                      </span>
                      <ChevronRight className="h-4 w-4 text-surface-300" />
                    </button>
                  ) : (
                    <label
                      key={it.id}
                      className="flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition hover:bg-surface-50 dark:hover:bg-surface-700"
                    >
                      <input
                        type="checkbox"
                        checked={Boolean(selected[it.id])}
                        onChange={() => toggle(it)}
                        className="h-4 w-4 rounded border-surface-300 text-brand focus:ring-brand-300 dark:border-surface-600 dark:bg-surface-700"
                      />
                      <FileText className="h-4 w-4 shrink-0 text-surface-400 dark:text-surface-500" />
                      <span className="flex-1 truncate text-surface-700 dark:text-surface-200">
                        {it.name}
                      </span>
                    </label>
                  )
                )
              )}
            </div>
            <div className="flex items-center justify-between gap-3 border-t border-surface-200 bg-surface-50 px-6 py-3 dark:border-surface-700 dark:bg-surface-900/50">
              <span className="text-xs text-surface-500 dark:text-surface-400">
                {selectedCount} seleccionado(s)
              </span>
              <button
                onClick={doImport}
                disabled={selectedCount === 0}
                className="btn-primary"
              >
                Importar
              </button>
            </div>
          </>
        )}

        {/* Importing */}
        {step === "importing" && (
          <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
            <Loader2 className="h-6 w-6 animate-spin text-brand-500" />
            <p className="mt-3 text-sm text-surface-500 dark:text-surface-400">
              Importando documentos…
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
