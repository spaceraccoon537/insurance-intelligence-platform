export interface HealthResponse {
  status: "ok";
  api_version: string;
}

export interface DocumentResponse {
  document_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  status: "queued" | "processing" | "ready" | "failed";
  created_at: string;
  page_count: number | null;
}

export interface DocumentListResponse {
  documents: DocumentResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface SourceCitation {
  document_id: string;
  filename: string;
  page_number: number | null;
  section_title: string | null;
  chunk_id: string;
  excerpt: string;
}

export interface QuestionResponse {
  request_id: string;
  answer: string;
  citations: SourceCitation[];
  retrieval_strategy: "semantic" | "bm25" | "hybrid";
}

export interface ComparisonValue {
  document_id: string;
  value: string;
  citations: SourceCitation[];
}

export interface ComparisonDimension {
  name: string;
  values: ComparisonValue[];
}

export interface ComparisonResponse {
  request_id: string;
  dimensions: ComparisonDimension[];
  summary: string;
}

export interface Finding {
  severity: "note" | "potential_issue" | "missing_information";
  title: string;
  explanation: string;
  citations: SourceCitation[];
}

export interface ClaimAnalysisResponse {
  request_id: string;
  findings: Finding[];
  potentially_missing_document_types: string[];
  disclaimer: string;
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

interface ApiErrorBody {
  error?: {
    message?: string;
  };
  detail?: unknown;
}

async function parseError(response: Response): Promise<Error> {
  let message = `Request failed (${response.status}).`;
  try {
    const body = (await response.json()) as ApiErrorBody;
    if (typeof body.error?.message === "string") {
      message = body.error.message;
    } else if (typeof body.detail === "string") {
      message = body.detail;
    }
  } catch {
    // Keep the stable status fallback when a non-JSON response is returned.
  }
  return new Error(message);
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${apiBaseUrl}/health`, { signal });
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as HealthResponse;
}

export async function listDocuments(signal?: AbortSignal): Promise<DocumentListResponse> {
  const response = await fetch(`${apiBaseUrl}/documents?limit=100`, { signal });
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as DocumentListResponse;
}

export async function uploadDocument(file: File, signal?: AbortSignal): Promise<DocumentResponse> {
  if (file.size > 25 * 1024 * 1024) {
    throw new Error("The selected file exceeds the 25 MiB upload limit.");
  }
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${apiBaseUrl}/documents`, {
    method: "POST",
    body: form,
    signal,
  });
  if (!response.ok) throw await parseError(response);
  const body = (await response.json()) as { document: DocumentResponse };
  return body.document;
}

export async function deleteDocument(documentId: string, signal?: AbortSignal): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/documents/${documentId}`, {
    method: "DELETE",
    signal,
  });
  if (!response.ok) throw await parseError(response);
}

export async function askQuestion(
  question: string,
  documentIds: string[],
  strategy: "semantic" | "bm25" | "hybrid" = "hybrid",
  signal?: AbortSignal,
): Promise<QuestionResponse> {
  const response = await fetch(`${apiBaseUrl}/questions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      document_ids: documentIds,
      retrieval_strategy: strategy,
    }),
    signal,
  });
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as QuestionResponse;
}

export async function comparePolicies(
  documentIds: string[],
  focusAreas: string[],
  signal?: AbortSignal,
): Promise<ComparisonResponse> {
  const response = await fetch(`${apiBaseUrl}/comparisons`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_ids: documentIds, focus_areas: focusAreas }),
    signal,
  });
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as ComparisonResponse;
}

export async function analyzeClaim(
  policyDocumentId: string,
  claimDocumentIds: string[],
  signal?: AbortSignal,
): Promise<ClaimAnalysisResponse> {
  const response = await fetch(`${apiBaseUrl}/claims/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      policy_document_id: policyDocumentId,
      claim_document_ids: claimDocumentIds,
    }),
    signal,
  });
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as ClaimAnalysisResponse;
}
