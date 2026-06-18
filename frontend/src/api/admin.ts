import { apiGet, apiPost } from "./client";
import type { Organization, User, UserRole } from "./types";

// ── Organizaciones (super-admin) ────────────────────────────────────────────────

export interface OrgCreate {
  name: string;
  slug: string;
  admin_email: string;
  admin_password: string;
}

export const listOrganizations = () =>
  apiGet<Organization[]>("/auth/organizations");

export const createOrganization = (body: OrgCreate) =>
  apiPost<Organization>("/auth/organizations", body);

// ── Usuarios de la organización (admin) ─────────────────────────────────────────

export interface UserCreate {
  email: string;
  password: string;
  role: Exclude<UserRole, "superadmin">;
}

export const listUsers = () => apiGet<User[]>("/auth/users");

export const createUser = (body: UserCreate) =>
  apiPost<User>("/auth/users", body);

// ── Cuenta propia ────────────────────────────────────────────────────────────────

export const changePassword = (current_password: string, new_password: string) =>
  apiPost<User>("/auth/change-password", { current_password, new_password });
