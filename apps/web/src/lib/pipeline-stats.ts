"use client";

import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";

export type PipelineStats = { queued: number; processing: number; ready: number; failed: number; total: number };

const STATUSES = ["UPLOADED", "PROCESSING", "READY", "FAILED"] as const;

/**
 * Quantos documentos visíveis ao usuário estão em cada etapa. Usa o `total` da listagem
 * filtrada (limit=1), sem endpoint próprio. Atualiza a cada 4 s enquanto há fila.
 */
export function usePipelineStats() {
  return useQuery({
    queryKey: ["pipeline-stats"],
    queryFn: async (): Promise<PipelineStats> => {
      const [queued, processing, ready, failed] = await Promise.all(
        STATUSES.map((status) =>
          unwrap(api.GET("/api/v1/documents", { params: { query: { status, limit: 1 } } })).then((page) => page.total),
        ),
      );
      return { queued, processing, ready, failed, total: queued + processing + ready + failed };
    },
    refetchInterval: (query) => {
      const data = query.state.data;
      return data && data.queued + data.processing > 0 ? 4000 : 30_000;
    },
  });
}
