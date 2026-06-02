import { useState } from "react";
import { ExternalLink, HardDriveDownload, X } from "lucide-react";
import { getGoogleConfig, setGoogleConfig } from "../lib/googleDrive";

export default function GoogleSettingsModal({
  onClose,
  onSaved,
}: {
  onClose: () => void;
  onSaved: () => void;
}) {
  const current = getGoogleConfig();
  const [clientId, setClientId] = useState(current.clientId ?? "");
  const [apiKey, setApiKey] = useState(current.apiKey ?? "");

  const canSave = clientId.trim().length > 0 && apiKey.trim().length > 0;

  function save() {
    if (!canSave) return;
    setGoogleConfig(clientId, apiKey);
    onSaved();
    onClose();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-surface-900/40 p-4 backdrop-blur-sm animate-fade-in dark:bg-black/60"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-pop animate-scale-in dark:bg-surface-800"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-surface-200 px-6 py-4 dark:border-surface-700">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-400">
              <HardDriveDownload className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-surface-900 dark:text-surface-50">
                Conectar Google Drive
              </h2>
              <p className="text-xs text-surface-400 dark:text-surface-500">
                Pegá las credenciales de tu app de Google Cloud
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-surface-400 transition hover:bg-surface-100 hover:text-surface-700 dark:text-surface-500 dark:hover:bg-surface-700 dark:hover:text-surface-200"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="px-6 py-5">
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-surface-500 dark:text-surface-400">
            Client ID (OAuth, app web)
          </label>
          <input
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            placeholder="123456.apps.googleusercontent.com"
            className="mb-4 w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-800 placeholder:text-surface-400 focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-100 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-100 dark:placeholder:text-surface-500 dark:focus:border-brand-600 dark:focus:ring-brand-500/20"
          />

          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-surface-500 dark:text-surface-400">
            API Key (para el Picker)
          </label>
          <input
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="AIza…"
            className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-800 placeholder:text-surface-400 focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-100 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-100 dark:placeholder:text-surface-500 dark:focus:border-brand-600 dark:focus:ring-brand-500/20"
          />

          <div className="mt-4 rounded-lg bg-surface-50 px-3 py-2.5 text-xs text-surface-500 ring-1 ring-surface-200 dark:bg-surface-900/50 dark:text-surface-400 dark:ring-surface-700">
            <p className="mb-1 font-medium text-surface-600 dark:text-surface-300">
              ¿Dónde las obtengo?
            </p>
            <p>
              En Google Cloud Console: habilitá Google Picker API + Drive API,
              creá un <b>ID de cliente OAuth</b> (app web, origen{" "}
              <code className="rounded bg-surface-200 px-1 dark:bg-surface-700">
                http://localhost:5173
              </code>
              ) y una <b>Clave de API</b>. Se guardan en este navegador.
            </p>
            <a
              href="https://console.cloud.google.com/apis/credentials"
              target="_blank"
              rel="noreferrer"
              className="mt-1.5 inline-flex items-center gap-1 font-medium text-brand-600 hover:underline dark:text-brand-400"
            >
              Abrir Credenciales de Google Cloud
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-surface-200 bg-surface-50 px-6 py-3.5 dark:border-surface-700 dark:bg-surface-900/50">
          <button
            onClick={onClose}
            className="rounded-lg px-3 py-2 text-sm font-medium text-surface-600 transition hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-700"
          >
            Cancelar
          </button>
          <button onClick={save} disabled={!canSave} className="btn-primary">
            Guardar
          </button>
        </div>
      </div>
    </div>
  );
}
