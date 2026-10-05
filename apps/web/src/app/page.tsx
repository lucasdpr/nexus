import { connection } from "next/server";

import { fetchApiHealth } from "@/lib/api";

// Página provisória da Fase 0: confirma que web e API conversam.
// Substituída pela landing na Fase 8.
export default async function Home() {
  await connection();
  const health = await fetchApiHealth();

  return (
    <main className="mx-auto flex min-h-dvh max-w-xl flex-col justify-center gap-3 px-6">
      <h1 className="text-2xl font-semibold tracking-tight">NEXUS</h1>
      <p role="status" className="text-sm">
        {health
          ? `API conectada · versão ${health.version}`
          : "API indisponível. Inicie o servidor em apps/api."}
      </p>
    </main>
  );
}
