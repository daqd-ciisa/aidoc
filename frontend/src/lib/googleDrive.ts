/**
 * Integración con Google Drive (importación puntual, amigable):
 * Google Identity Services (token client) → access_token con scope drive.file
 * → Google Picker para elegir archivos. No se almacenan refresh tokens.
 *
 * La configuración (Client ID + API key, ambos públicos) se puede setear desde
 * la UI (se guarda en localStorage) o por env (VITE_GOOGLE_CLIENT_ID/API_KEY).
 */
import type { DriveFile } from "../api/connectors";

const env = (import.meta as unknown as { env: Record<string, string | undefined> })
  .env;
const SCOPE = "https://www.googleapis.com/auth/drive.file";
const LS_CLIENT = "aidoc-google-client-id";
const LS_KEY = "aidoc-google-api-key";

// Acceso laxo a los SDK globales de Google (cargados dinámicamente).
const w = window as unknown as { google?: any; gapi?: any }; // eslint-disable-line @typescript-eslint/no-explicit-any

function ls(key: string): string | undefined {
  try {
    return localStorage.getItem(key) || undefined;
  } catch {
    return undefined;
  }
}

/** Config efectiva: localStorage (UI) tiene prioridad sobre el env. */
export function getGoogleConfig(): { clientId?: string; apiKey?: string } {
  return {
    clientId: ls(LS_CLIENT) || env.VITE_GOOGLE_CLIENT_ID || undefined,
    apiKey: ls(LS_KEY) || env.VITE_GOOGLE_API_KEY || undefined,
  };
}

export function setGoogleConfig(clientId: string, apiKey: string): void {
  try {
    localStorage.setItem(LS_CLIENT, clientId.trim());
    localStorage.setItem(LS_KEY, apiKey.trim());
  } catch {
    /* ignore */
  }
}

export function clearGoogleConfig(): void {
  try {
    localStorage.removeItem(LS_CLIENT);
    localStorage.removeItem(LS_KEY);
  } catch {
    /* ignore */
  }
}

export function isGoogleDriveConfigured(): boolean {
  const c = getGoogleConfig();
  return Boolean(c.clientId && c.apiKey);
}

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) return resolve();
    const s = document.createElement("script");
    s.src = src;
    s.async = true;
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`No se pudo cargar ${src}`));
    document.head.appendChild(s);
  });
}

function getAccessToken(clientId: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const tokenClient = w.google.accounts.oauth2.initTokenClient({
      client_id: clientId,
      scope: SCOPE,
      callback: (resp: { access_token?: string; error?: string }) => {
        if (resp.error || !resp.access_token) {
          reject(new Error(resp.error || "No se obtuvo token de Google."));
        } else {
          resolve(resp.access_token);
        }
      },
    });
    tokenClient.requestAccessToken({ prompt: "" });
  });
}

function openPicker(accessToken: string, apiKey: string): Promise<DriveFile[]> {
  return new Promise((resolve, reject) => {
    w.gapi.load("picker", () => {
      try {
        const g = w.google;
        const view = new g.picker.DocsView(g.picker.ViewId.DOCS)
          .setIncludeFolders(true)
          .setSelectFolderEnabled(false);
        const picker = new g.picker.PickerBuilder()
          .enableFeature(g.picker.Feature.MULTISELECT_ENABLED)
          .setOAuthToken(accessToken)
          .setDeveloperKey(apiKey)
          .addView(view)
          .setCallback((data: any) => {
            // eslint-disable-line @typescript-eslint/no-explicit-any
            if (data.action === g.picker.Action.PICKED) {
              const files: DriveFile[] = (data.docs || []).map((d: any) => ({
                id: d.id,
                name: d.name,
                mimeType: d.mimeType,
              }));
              resolve(files);
            } else if (data.action === g.picker.Action.CANCEL) {
              resolve([]);
            }
          })
          .build();
        picker.setVisible(true);
      } catch (e) {
        reject(e);
      }
    });
  });
}

/** Abre el flujo completo: consentimiento → Picker. Devuelve token + archivos. */
export async function pickFromDrive(): Promise<{
  accessToken: string;
  files: DriveFile[];
}> {
  const { clientId, apiKey } = getGoogleConfig();
  if (!clientId || !apiKey) {
    throw new Error("Google Drive no está configurado.");
  }
  await Promise.all([
    loadScript("https://accounts.google.com/gsi/client"),
    loadScript("https://apis.google.com/js/api.js"),
  ]);
  const accessToken = await getAccessToken(clientId);
  const files = await openPicker(accessToken, apiKey);
  return { accessToken, files };
}
