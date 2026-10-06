"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Check, CircleAlert, Download, LoaderCircle } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect } from "react";

import { StatusBadge, isPending } from "@/components/nexus/status-badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api, errorMessage, unwrap, type DocumentDetail } from "@/lib/api/client";
import { formatBytes, formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

// PDF.js só roda no navegador.
const PdfViewer = dynamic(() => import("./pdf-viewer"), {
  ssr: false,
  loading: () => <p className="py-20 text-center text-muted-foreground">Abrindo o PDF…</p>,
});

const STEP_NAMES: Record<DocumentDetail["steps"][number]["step"], string> = {
  UPLOAD: "Upload concluído",
  EXTRACT: "Texto extraído",
  CHUNK: "Conteúdo dividido em trechos",
  EMBED: "Embeddings gerados",
  INDEX: "Indexação concluída",
};

type Props = { documentId: string; initialPage: number; chunkId?: string };

export function DocumentView({ documentId, initialPage, chunkId }: Props) {
  const path = { document_id: documentId };
  const document = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => unwrap(api.GET("/api/v1/documents/{document_id}", { params: { path } })),
    refetchInterval: (query) => (query.state.data && isPending(query.state.data.status) ? 2000 : false),
  });
  const citedChunk = useQuery({
    queryKey: ["chunk", documentId, chunkId],
    queryFn: () =>
      unwrap(api.GET("/api/v1/documents/{document_id}/chunks/{chunk_id}", { params: { path: { ...path, chunk_id: chunkId! } } })),
    enabled: Boolean(chunkId),
  });
  const isPdf = document.data?.kind === "PDF";
  const allChunks = useQuery({
    queryKey: ["chunks", documentId],
    queryFn: () => unwrap(api.GET("/api/v1/documents/{document_id}/chunks", { params: { path } })),
    enabled: Boolean(document.data) && !isPdf && document.data?.status === "READY",
  });

  useEffect(() => {
    if (chunkId && allChunks.data) {
      window.document.getElementById(`trecho-${chunkId}`)?.scrollIntoView({ block: "center" });
    }
  }, [chunkId, allChunks.data]);

  if (document.isLoading) {
    return (
      <div className="grid flex-1 gap-6 p-6 lg:grid-cols-[1fr_360px]">
        <Skeleton className="h-[70dvh]" />
        <Skeleton className="h-80" />
      </div>
    );
  }
  if (!document.data) {
    return (
      <div className="mx-auto max-w-md px-6 py-20 text-center">
        <p className="font-medium">Não foi possível abrir este documento.</p>
        <p className="mt-1 text-muted-foreground">{errorMessage(document.error)}</p>
        <Button asChild variant="outline" className="mt-4">
          <Link href="/biblioteca">Voltar à biblioteca</Link>
        </Button>
      </div>
    );
  }

  const data = document.data;
  const fileUrl = `/api/v1/documents/${data.id}/file`;

  return (
    <div className="flex min-h-0 flex-1 flex-col lg:h-dvh lg:flex-row">
      <section aria-label="Documento" className="flex min-h-[60dvh] min-w-0 flex-1 flex-col lg:min-h-0">
        <header className="flex items-center gap-3 border-b border-border px-4 py-3 sm:px-6">
          <Button asChild variant="ghost" size="icon" className="shrink-0">
            <Link href="/biblioteca" aria-label="Voltar à biblioteca">
              <ArrowLeft aria-hidden />
            </Link>
          </Button>
          <h1 className="min-w-0 truncate text-[17px] font-semibold">{data.title}</h1>
        </header>
        {data.status !== "READY" ? (
          <p className="m-auto max-w-sm px-6 py-20 text-center text-muted-foreground">
            {data.status === "FAILED"
              ? "O processamento falhou. Veja o motivo ao lado."
              : "O documento ainda está sendo processado. A página se atualiza sozinha."}
          </p>
        ) : isPdf ? (
          <PdfViewer
            url={fileUrl}
            initialPage={citedChunk.data?.page ?? initialPage}
            evidence={citedChunk.data?.content}
            evidencePage={citedChunk.data?.page}
            key={citedChunk.data?.id ?? "sem-trecho"}
          />
        ) : (
          <div className="min-h-0 flex-1 overflow-y-auto bg-muted/50 px-4 py-6 sm:px-8">
            <article className="document-voice mx-auto max-w-[70ch] space-y-4 rounded-sm bg-card px-6 py-8 text-[16px] shadow-sm ring-1 ring-border sm:px-10">
              {allChunks.isLoading && <Skeleton className="h-40" />}
              {allChunks.data?.map((chunk) => (
                <p key={chunk.id} id={`trecho-${chunk.id}`} className="scroll-mt-24 whitespace-pre-line">
                  {chunk.id === chunkId ? <mark className="evidence-mark text-inherit">{chunk.content}</mark> : chunk.content}
                </p>
              ))}
            </article>
          </div>
        )}
      </section>

      <aside aria-label="Informações do documento" className="shrink-0 space-y-6 overflow-y-auto border-t border-border bg-secondary/40 p-5 lg:w-[360px] lg:border-t-0 lg:border-l">
        {citedChunk.data && (
          <section>
            <h2 className="text-[13px] text-muted-foreground">Trecho citado na resposta</h2>
            <blockquote className="document-voice mt-2 rounded-md border border-border bg-card p-4 text-[15px]">
              <mark className="evidence-mark text-inherit">{citedChunk.data.content}</mark>
            </blockquote>
            {citedChunk.data.page && (
              <p className="mt-2 text-[13px] text-muted-foreground">Página {citedChunk.data.page}</p>
            )}
          </section>
        )}

        <section>
          <h2 className="sr-only">Ficha do documento</h2>
          <TitleBlock
            cells={[
              { label: "Documento", value: data.title, wide: true },
              { label: "Coleção", value: data.collection.name, wide: true },
              { label: "Tipo", value: data.kind },
              { label: "Tamanho", value: formatBytes(data.size_bytes) },
              { label: "Páginas", value: data.page_count ?? "Sem páginas" },
              { label: "Versão", value: data.version },
              { label: "Enviado por", value: data.uploaded_by.name, wide: true },
              { label: "Enviado em", value: formatDateTime(data.created_at) },
              { label: "Status", value: <StatusBadge status={data.status} /> },
            ]}
          />
          <Button asChild variant="outline" className="mt-3 w-full">
            <a href={fileUrl} download>
              <Download aria-hidden />
              Baixar arquivo original
            </a>
          </Button>
        </section>

        <section>
          <h2 className="text-[13px] text-muted-foreground">Processamento</h2>
          <ol className="mt-2 space-y-2">
            {data.steps.map((step) => (
              <li key={step.step} className="flex items-start gap-2.5 text-[14px]">
                <StepIcon status={step.status} />
                <div className="min-w-0">
                  <p className={cn(step.status === "PENDING" && "text-muted-foreground")}>{STEP_NAMES[step.step]}</p>
                  {step.error && <p className="text-[13px] text-destructive">{step.error}</p>}
                </div>
              </li>
            ))}
          </ol>
          {data.error && <p className="mt-3 text-[13px] text-destructive">{data.error}</p>}
        </section>
      </aside>
    </div>
  );
}

function StepIcon({ status }: { status: DocumentDetail["steps"][number]["status"] }) {
  const base = "mt-0.5 size-4 shrink-0";
  if (status === "DONE") return <Check className={cn(base, "text-status-ready")} aria-label="Concluída" />;
  if (status === "RUNNING") return <LoaderCircle className={cn(base, "animate-spin text-status-processing")} aria-label="Em andamento" />;
  if (status === "FAILED") return <CircleAlert className={cn(base, "text-status-failed")} aria-label="Falhou" />;
  return <span className={cn(base, "grid place-items-center")} aria-label="Pendente"><span className="size-1.5 rounded-full bg-muted-foreground/60" /></span>;
}

/** Ficha do documento no formato do carimbo de desenho técnico. */
function TitleBlock({ cells }: { cells: { label: string; value: React.ReactNode; wide?: boolean }[] }) {
  return (
    <dl className="grid grid-cols-2 overflow-hidden rounded-md border border-border bg-card">
      {cells.map((cell) => (
        <div key={cell.label} className={cn("min-w-0 border-b border-border px-3 py-2 odd:border-r last:border-b-0", cell.wide && "col-span-2 border-r-0")}>
          <dt className="text-[11px] text-muted-foreground">{cell.label}</dt>
          <dd className="text-[13px] leading-snug font-medium break-words">{cell.value}</dd>
        </div>
      ))}
    </dl>
  );
}
