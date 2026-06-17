import { apiPost } from "./client";
import type { DocumentRead } from "./types";

export interface DriveFile {
  id: string;
  name: string;
  mimeType?: string;
}

export interface ImportResult {
  documents: DocumentRead[];
  duplicates: string[];
  rejected: string[];
  failed: string[];
}

export const importFromGoogleDrive = (accessToken: string, files: DriveFile[]) =>
  apiPost<ImportResult>("/connectors/google/import", {
    access_token: accessToken,
    files,
  });

export const importFromOneDrive = (accessToken: string, files: DriveFile[]) =>
  apiPost<ImportResult>("/connectors/onedrive/import", {
    access_token: accessToken,
    files,
  });

export interface SharePointFile {
  id: string;
  name: string;
  site_id: string;
  drive_id: string;
  mimeType?: string;
}

export const importFromSharePoint = (
  accessToken: string,
  files: SharePointFile[]
) =>
  apiPost<ImportResult>("/connectors/sharepoint/import", {
    access_token: accessToken,
    files,
  });

export const importFromUrl = (
  url: string,
  docType: "reference" | "document" | "catalog" = "reference"
) =>
  apiPost<ImportResult>("/connectors/url/import", {
    url,
    doc_type: docType,
  });
