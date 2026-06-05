import { apiGet } from "./client";
import { clearToken, setToken } from "../lib/auth";
import type { User } from "./types";

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

/** Autentica y guarda el token; devuelve el usuario. */
export async function login(email: string, password: string): Promise<User> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Credenciales inválidas.");
  }
  const data: LoginResponse = await res.json();
  setToken(data.access_token);
  return data.user;
}

/** Usuario autenticado actual (valida el token contra el backend). */
export const me = () => apiGet<User>("/auth/me");

export function logout(): void {
  clearToken();
}
