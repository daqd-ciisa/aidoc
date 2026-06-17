/**
 * Integración con SharePoint / Microsoft Graph (importación puntual).
 * MSAL (popup, scope Sites.Read.All) → access_token → exploramos
 * sitio → biblioteca de documentos (drive) → carpetas con Graph, y el backend
 * descarga los archivos elegidos.
 *
 * Comparte el Client ID con OneDrive (misma App registration de Azure); lo que
 * cambia es el permiso de Graph: SharePoint necesita Sites.Read.All (delegado),
 * que normalmente requiere consentimiento del admin del tenant.
 */
import { PublicClientApplication } from "@azure/msal-browser";
import {
  getOneDriveClientId,
  setOneDriveClientId,
  type DriveItem,
} from "./oneDrive";

const GRAPH = "https://graph.microsoft.com/v1.0";
const SCOPES = ["Sites.Read.All"];

export type { DriveItem };

/** Un sitio de SharePoint. */
export interface SiteItem {
  id: string;
  name: string;
  webUrl?: string;
}

/** Una biblioteca de documentos (drive) dentro de un sitio. */
export interface DriveLib {
  id: string;
  name: string;
}

// El Client ID es el mismo que OneDrive (misma App registration de Azure).
export function getSharePointClientId(): string | undefined {
  return getOneDriveClientId();
}

export function setSharePointClientId(clientId: string): void {
  setOneDriveClientId(clientId);
}

export function isSharePointConfigured(): boolean {
  return Boolean(getOneDriveClientId());
}

let _pca: PublicClientApplication | null = null;
let _initClientId: string | null = null;

async function getPca(): Promise<PublicClientApplication> {
  const clientId = getSharePointClientId();
  if (!clientId) throw new Error("SharePoint no está configurado.");
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
export async function getSharePointTokenSilent(): Promise<string | null> {
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
export async function getSharePointToken(): Promise<string> {
  const silent = await getSharePointTokenSilent();
  if (silent) return silent;
  const pca = await getPca();
  const res = await pca.acquireTokenPopup({ scopes: SCOPES });
  return res.accessToken;
}

/** Busca sitios de SharePoint por texto (vacío = sitios más usados). */
export async function searchSites(
  token: string,
  query: string
): Promise<SiteItem[]> {
  const q = query.trim() || "*";
  const url = `${GRAPH}/sites?search=${encodeURIComponent(q)}&$top=50`;
  const resp = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error(`Graph ${resp.status}`);
  const data = await resp.json();
  return (data.value || []).map(
    (s: { id: string; displayName?: string; name?: string; webUrl?: string }) => ({
      id: s.id,
      name: s.displayName || s.name || s.webUrl || s.id,
      webUrl: s.webUrl,
    })
  );
}

/** Lista las bibliotecas de documentos (drives) de un sitio. */
export async function listDrives(
  token: string,
  siteId: string
): Promise<DriveLib[]> {
  const url = `${GRAPH}/sites/${siteId}/drives?$select=id,name&$top=100`;
  const resp = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error(`Graph ${resp.status}`);
  const data = await resp.json();
  return (data.value || []).map((d: { id: string; name: string }) => ({
    id: d.id,
    name: d.name,
  }));
}

/** Lista el contenido de una carpeta de una biblioteca (root si no hay folderId). */
export async function listChildren(
  token: string,
  siteId: string,
  driveId: string,
  folderId?: string
): Promise<DriveItem[]> {
  const base = `${GRAPH}/sites/${siteId}/drives/${driveId}`;
  const path = folderId
    ? `${base}/items/${folderId}/children`
    : `${base}/root/children`;
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
