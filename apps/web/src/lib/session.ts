import { cookies } from "next/headers";

import type { Me } from "@/lib/api/client";

const API_URL = process.env.API_URL ?? "http://localhost:8000";
const SESSION_COOKIE = "nexus_session";

/**
 * Sessão atual, validada pela API no servidor. Esconder telas no front é conveniência;
 * a autorização de verdade acontece em cada chamada à API.
 */
export async function getSession(): Promise<Me | null> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return null;

  const response = await fetch(`${API_URL}/api/v1/auth/me`, {
    headers: { cookie: `${SESSION_COOKIE}=${token}` },
    cache: "no-store",
  });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error(`A API respondeu ${response.status} ao validar a sessão.`);
  return (await response.json()) as Me;
}
