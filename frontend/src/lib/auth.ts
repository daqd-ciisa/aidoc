// Almacenamiento del token JWT + helpers de auth para el cliente API.

const TOKEN_KEY = "aidoc-token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* ignore */
  }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

/** Header Authorization si hay token; objeto vacío si no. */
export function authHeaders(): Record<string, string> {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

/** Avisa a la app (AuthProvider) que la sesión dejó de ser válida (401). */
export function notifyUnauthorized(): void {
  window.dispatchEvent(new Event("aidoc:unauthorized"));
}
