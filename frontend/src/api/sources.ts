import { apiDelete, apiGet, apiPost } from "./client";
import type { ApprovedUrl } from "./types";

/** URLs aprobadas que el modelo consulta EN VIVO al validar propuestas. */
export const listApprovedUrls = () =>
  apiGet<ApprovedUrl[]>("/sources/urls");

export const addApprovedUrl = (url: string, label?: string) =>
  apiPost<ApprovedUrl>("/sources/urls", { url, label: label || null });

export const deleteApprovedUrl = (id: string) =>
  apiDelete(`/sources/urls/${id}`);
