import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

/**
 * Cliente tipado da API, gerado do OpenAPI do FastAPI (`npm run api:types`).
 * No navegador, as chamadas vão para /api no mesmo domínio e o Next repassa à API;
 * o cookie de sessão viaja sozinho.
 */
export const api = createClient<paths>({ baseUrl: "", credentials: "same-origin" });

type Schemas = components["schemas"];
export type Me = Schemas["MeResponse"];
export type Collection = Schemas["CollectionOut"];
export type DocumentSummary = Schemas["DocumentOut"];
export type DocumentDetail = Schemas["DocumentDetail"];
export type DocumentPage = Schemas["DocumentPage"];
export type Conversation = Schemas["ConversationOut"];
export type ConversationDetail = Schemas["ConversationDetail"];
export type Message = Schemas["MessageOut"];
export type Citation = Schemas["CitationOut"];
export type Chunk = Schemas["ChunkOut"];

/** Fonte enviada no evento `sources` do streaming (fora do OpenAPI, que não descreve SSE). */
export type Source = {
  marker: number;
  document_id: string;
  chunk_id: string;
  document_title: string;
  page: number | null;
  snippet: string;
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

/** Mensagem legível a partir do corpo de erro da API (`detail` texto ou lista de validação). */
export function errorMessage(error: unknown, fallback = "Algo deu errado. Tente novamente."): string {
  if (error instanceof ApiError) return error.message;
  const detail = (error as { detail?: unknown } | undefined)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) return "Confira os campos preenchidos.";
  return fallback;
}

/** Converte o resultado do openapi-fetch em dado ou exceção, para usar com TanStack Query. */
export async function unwrap<T>(
  request: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await request;
  if (error !== undefined || !response.ok) {
    throw new ApiError(errorMessage(error), response.status);
  }
  return data as T;
}
