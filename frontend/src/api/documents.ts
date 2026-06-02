import { apiDelete, apiGet, apiPost } from "./client";
import type { DocumentRead, UploadResult } from "./types";

export const listDocuments = () => apiGet<DocumentRead[]>("/documents");

export async function uploadDocuments(
  files: FileList | File[]
): Promise<UploadResult> {
  const form = new FormData();
  Array.from(files).forEach((f) => form.append("files", f));
  const res = await fetch("/api/documents", { method: "POST", body: form });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || res.statusText);
  }
  return res.json();
}

export const deleteDocument = (id: string) => apiDelete(`/documents/${id}`);

export const reindexDocument = (id: string) =>
  apiPost<DocumentRead>(`/documents/${id}/reindex`);
