// Chamadas feitas no servidor do Next vão direto à API; no navegador, usam o
// caminho relativo /api, repassado pelo rewrite de next.config.ts.
const serverApiUrl = process.env.API_URL ?? "http://localhost:8000";

export type ApiHealth = { status: "ok"; version: string };

export async function fetchApiHealth(): Promise<ApiHealth | null> {
  try {
    const response = await fetch(`${serverApiUrl}/api/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    if (!response.ok) return null;
    return (await response.json()) as ApiHealth;
  } catch {
    return null;
  }
}
