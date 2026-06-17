/**
 * Integración con OneDrive / Microsoft Graph (importación puntual).
 * MSAL (popup, scope Files.Read) → access_token → exploramos el drive con Graph
 * y el backend descarga los archivos elegidos.
 *
 * Config: Client ID de una App registration de Azure (SPA, redirect =
 * window.location.origin). Se setea desde la UI (localStorage) o por env
 * (VITE_MS_CLIENT_ID). No necesita "API key" (Graph usa solo el token).
 */
import { PublicClientApplication } from "@azure/msal-browser";

const env = (import.meta as unknown as { env: Record<string, string | undefined> })
  .env;
const LS_CLIENT = "aidoc-ms-client-id";
const GRAPH = "https://graph.microsoft.com/v1.0";
const SCOPES = ["Files.Read"];

export interface DriveItem {
  id: string;
  name: string;
  isFolder: boolean;
  size?: number;
}

function ls(key: string): string | undefined {
  try {
    return localStorage.getItem(key) || undefined;
  } catch {
    return undefined;
  }
}

export function getOneDriveClientId(): string | undefined {
  return ls(LS_CLIENT) || env.VITE_MS_CLIENT_ID || undefined;
}

export function setOneDriveClientId(clientId: string): void {
  try {
    localStorage.setItem(LS_CLIENT, clientId.trim());
  } catch {
    /* ignore */
  }
}

export function isOneDriveConfigured(): boolean {
  return Boolean(getOneDriveClientId());
}

let _pca: PublicClientApplication | null = null;
let _initClientId: string | null = null;

async function getPca(): Promise<PublicClientApplication> {
  const clientId = getOneDriveClientId();
  if (!clientId) throw new Error("OneDrive no está configurado.");
  if (!_pca || _initClientId !== clientId) {
    _pca = new PublicClientApplication({
      auth: {
        clientId,
        authority: "https://login.microsoftonline.com/common",
        redirectUri: window.location.origin,
      },
      cache: { cacheLocation: "localStorage" },
    });
    await _pca.initialize();
    _initClientId = clientId;
  }
  return _pca;
}

/** Intenta un access_token SIN popup (devuelve null si requiere interacción). */
export async function getOneDriveTokenSilent(): Promise<string | null> {
  const pca = await getPca();
  const accounts = pca.getAllAccounts();
  if (accounts.length === 0) return null;
  try {
    const res = await pca.acquireTokenSilent({
      scopes: SCOPES,
      account: accounts[0],
    });
    return res.accessToken;
  } catch {
    return null;
  }
}

/** Obtiene un access_token con popup. DEBE llamarse desde un gesto del usuario
 * (clic): los navegadores bloquean popups que no nacen de una interacción. */
export async function getOneDriveToken(): Promise<string> {
  const silent = await getOneDriveTokenSilent();
  if (silent) return silent;
  const pca = await getPca();
  const res = await pca.acquireTokenPopup({ scopes: SCOPES });
  return res.accessToken;
}

/** Lista el contenido de una carpeta (root si no se pasa id). */
export async function listChildren(
  token: string,
  folderId?: string
): Promise<DriveItem[]> {
  const path = folderId
    ? `${GRAPH}/me/drive/items/${folderId}/children`
    : `${GRAPH}/me/drive/root/children`;
  const url = `${path}?$select=id,name,folder,file,size&$top=200`;
  const resp = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error(`Graph ${resp.status}`);
  const data = await resp.json();
  return (data.value || []).map(
    (it: { id: string; name: string; folder?: unknown; size?: number }) => ({
      id: it.id,
      name: it.name,
      isFolder: Boolean(it.folder),
      size: it.size,
    })
  );
}
