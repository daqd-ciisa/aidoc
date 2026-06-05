import { apiDelete, apiGet, apiPost } from "./client";
import { authHeaders, clearToken, notifyUnauthorized } from "../lib/auth";
import type { DocumentRead, UploadResult } from "./types";

export const listDocuments = () => apiGet<DocumentRead[]>("/documents");

export async function uploadDocuments(
  files: FileList | File[]
): Promise<UploadResult> {
  const form = new FormData();
  Array.from(files).forEach((f) => form.append("files", f));
  // Sin Content-Type: el browser lo setea con el boundary del multipart.
  const res = await fetch("/api/documents", {
    method: "POST",
    headers: { ...authHeaders() },
    body: form,
  });
  if (!res.ok) {
    if (res.status === 401) {
      clearToken();
      notifyUnauthorized();
    }
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || res.statusText);
  }
  return res.json();
}

export const deleteDocument = (id: string) => apiDelete(`/documents/${id}`);

export const reindexDocument = (id: string) =>
  apiPost<DocumentRead>(`/documents/${id}/reindex`);
