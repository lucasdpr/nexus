"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CloudUpload, FileText } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import Link from "next/link";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { AnimatedNumber } from "@/components/fx/animated-number";
import { GlassCard } from "@/components/fx/glass-card";
import { SPRING } from "@/components/fx/motion";
import { StatusBadge } from "@/components/nexus/status-badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, errorMessage, unwrap } from "@/lib/api/client";
import { EVALUATION, percent } from "@/lib/evaluation";
import { formatRelative } from "@/lib/format";
import { canManageDocuments, useMe } from "@/lib/me-context";
import { usePipelineStats } from "@/lib/pipeline-stats";
import { uploadDocument } from "@/lib/upload";
import { cn } from "@/lib/utils";

const MAX_BYTES = 25 * 1024 * 1024;

export function Dashboard() {
  const me = useMe();
  const firstName = me.user.name.split(/\s+/)[0];

  return (
    <div className="mx-auto w-full max-w-6xl px-4 pb-10 sm:px-6">
      <h1 className="w-fit bg-gradient-to-r from-white via-fuchsia-200 to-primary bg-clip-text pt-2 text-[30px] leading-tight font-semibold tracking-tight text-transparent">
        Olá, {firstName}
      </h1>
      <p className="mt-1 text-muted-foreground">O que está acontecendo com os documentos da {me.organization.name}.</p>

      {/* Bento assimétrico: fila larga no topo, motor de busca alto à direita. */}
      <div className="mt-6 grid gap-4 lg:grid-cols-3 lg:grid-rows-[auto_auto]">
        <QueueCard className="lg:col-span-2" />
        <SearchEngineCard className="lg:row-span-2" />
        {canManageDocuments(me) ? <UploadCard /> : <AskCard />}
        <RecentDocumentsCard />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ Fila de ingestão */

function QueueCard({ className }: { className?: string }) {
  const stats = usePipelineStats();
  const data = stats.data;
  const working = (data?.queued ?? 0) + (data?.processing ?? 0);
  const readyShare = data && data.total > 0 ? data.ready / data.total : 0;

  const cells = [
    { label: "Na fila", value: data?.queued ?? 0, tone: "text-zinc-200" },
    { label: "Processando", value: data?.processing ?? 0, tone: "text-amber-300" },
    { label: "Prontos", value: data?.ready ?? 0, tone: "text-emerald-300" },
    { label: "Com falha", value: data?.failed ?? 0, tone: "text-rose-300" },
  ];

  return (
    <GlassCard
      className={cn("min-h-64 p-6 pb-24", className)}
      // Onda fluida: a altura do líquido é a fração de documentos já pesquisáveis.
      decoration={<LiquidWave level={readyShare} active={working > 0} />}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-[15px] font-semibold">Fila de ingestão</h2>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            {working > 0 ? "Documentos sendo lidos, divididos e indexados agora." : "Nada esperando processamento."}
          </p>
        </div>
        <p className="text-right">
          <span className="block text-[32px] leading-none font-semibold tabular-nums">
            <AnimatedNumber value={Math.round(readyShare * 100)} />%
          </span>
          <span className="text-[12px] text-muted-foreground">pesquisáveis</span>
        </p>
      </div>

      <dl className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {cells.map((cell) => (
          <div key={cell.label}>
            <dt className="text-[12px] text-muted-foreground">{cell.label}</dt>
            <dd className={cn("mt-1 text-[28px] leading-none font-semibold tabular-nums", cell.tone)}>
              <AnimatedNumber value={cell.value} />
            </dd>
          </div>
        ))}
      </dl>
    </GlassCard>
  );
}

function LiquidWave({ level, active }: { level: number; active: boolean }) {
  const height = 18 + level * 46;
  return (
    <div aria-hidden className="pointer-events-none absolute inset-x-0 bottom-0 h-20 overflow-hidden rounded-b-xl">
      <motion.div className="absolute inset-x-0 bottom-0" animate={{ height }} transition={SPRING}>
        {[0, 1].map((layer) => (
          <svg
            key={layer}
            viewBox="0 0 1200 60"
            preserveAspectRatio="none"
            className={cn(
              "absolute -top-4 left-0 h-6 w-[200%]",
              layer === 0 ? "text-neon-violet/40" : "text-neon-cyan/25",
            )}
            style={{
              animation: `wave ${active ? (layer ? 5 : 7) : layer ? 12 : 16}s linear infinite`,
              animationDelay: layer ? "-3s" : "0s",
            }}
          >
            <path
              fill="currentColor"
              d="M0 30 Q 150 0 300 30 T 600 30 T 900 30 T 1200 30 V60 H0 Z"
            />
          </svg>
        ))}
        <div className="h-full bg-gradient-to-b from-neon-violet/40 to-neon-indigo/10" />
      </motion.div>
    </div>
  );
}

/* ------------------------------------------------------------- Motor de busca (RRF) */

function SearchEngineCard({ className }: { className?: string }) {
  return (
    <GlassCard className={cn("flex min-h-80 flex-col p-6", className)}>
      <h2 className="text-[15px] font-semibold">Motor de busca</h2>
      <p className="mt-0.5 text-[13px] text-muted-foreground">
        Cada pergunta corre por dois caminhos, por significado e por palavras, e os rankings se fundem.
      </p>
      <FusionAnimation />
      <dl className="mt-auto grid grid-cols-2 gap-3 border-t border-white/10 pt-4 text-[13px]">
        <div>
          <dt className="text-muted-foreground">Trecho certo em 1º</dt>
          <dd className="text-[22px] font-semibold tabular-nums">{percent(EVALUATION.search.top1)}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Entre os 5 primeiros</dt>
          <dd className="text-[22px] font-semibold tabular-nums">{percent(EVALUATION.search.top5)}</dd>
        </div>
      </dl>
      <p className="mt-2 text-[12px] text-muted-foreground">
        Medido em {EVALUATION.answerable} perguntas com resposta conhecida.
      </p>
    </GlassCard>
  );
}

/**
 * Ilustração do RRF: partículas ciano (busca vetorial) e violeta (busca textual) descem por
 * dois trilhos e se fundem num núcleo que pulsa. Puramente decorativa (aria-hidden).
 */
function FusionAnimation() {
  // Animação SVG (SMIL) não obedece ao CSS de "reduzir movimento": desliga as partículas aqui.
  const reduce = useReducedMotion();
  const particles = reduce ? [] : Array.from({ length: 6 }, (_, index) => index);
  return (
    <div aria-hidden className="relative my-6 h-44">
      <svg viewBox="0 0 200 160" className="absolute inset-0 size-full">
        <path id="trilho-a" d="M30 0 C 30 80, 100 70, 100 130" fill="none" stroke="rgb(6 182 212 / 0.25)" strokeWidth="1.5" />
        <path id="trilho-b" d="M170 0 C 170 80, 100 70, 100 130" fill="none" stroke="rgb(176 38 255 / 0.3)" strokeWidth="1.5" />
        {particles.map((index) => (
          <g key={index}>
            <circle r="3" fill="#22d3ee" style={{ filter: "drop-shadow(0 0 4px #22d3ee)" }}>
              <animateMotion dur="2.4s" begin={`${index * 0.4}s`} repeatCount="indefinite" keyPoints="0;1" keyTimes="0;1" calcMode="spline" keySplines="0.4 0 0.6 1">
                <mpath href="#trilho-a" />
              </animateMotion>
            </circle>
            <circle r="3" fill="#d08bff" style={{ filter: "drop-shadow(0 0 4px #d08bff)" }}>
              <animateMotion dur="2.4s" begin={`${index * 0.4 + 0.2}s`} repeatCount="indefinite" keyPoints="0;1" keyTimes="0;1" calcMode="spline" keySplines="0.4 0 0.6 1">
                <mpath href="#trilho-b" />
              </animateMotion>
            </circle>
          </g>
        ))}
      </svg>
      <motion.div
        className="absolute bottom-0 left-1/2 size-14 -translate-x-1/2 rounded-full bg-gradient-to-br from-neon-cyan via-neon-violet to-neon-indigo blur-[2px]"
        animate={{ scale: [1, 1.15, 1], opacity: [0.85, 1, 0.85] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
      />
      <div className="absolute bottom-0 left-1/2 size-14 -translate-x-1/2 rounded-full bg-neon-violet/40 blur-2xl" />
      <span className="absolute top-0 left-0 text-[11px] text-cyan-300">significado</span>
      <span className="absolute top-0 right-0 text-[11px] text-fuchsia-300">palavras</span>
    </div>
  );
}

/* --------------------------------------------------------------------------- Upload */

function UploadCard() {
  const queryClient = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const collections = useQuery({ queryKey: ["collections"], queryFn: () => unwrap(api.GET("/api/v1/collections")) });
  const [collectionId, setCollectionId] = useState<string>();
  const target = collectionId ?? collections.data?.[0]?.id;

  async function send(files: FileList | null) {
    const file = files?.[0];
    if (!file || !target) return;
    if (file.size > MAX_BYTES) {
      toast.error("O arquivo passa do limite de 25 MB.");
      return;
    }
    try {
      setProgress(0);
      await uploadDocument(file, target, setProgress);
      toast.success(`${file.name} enviado. O processamento começou.`);
      await queryClient.invalidateQueries({ queryKey: ["pipeline-stats"] });
      await queryClient.invalidateQueries({ queryKey: ["recent-documents"] });
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setProgress(null);
    }
  }

  return (
    <GlassCard tilt={false} className="p-6">
      <h2 className="text-[15px] font-semibold">Enviar documento</h2>
      <Select value={target} onValueChange={setCollectionId}>
        <SelectTrigger className="mt-3 w-full" aria-label="Coleção de destino">
          <SelectValue placeholder="Coleção" />
        </SelectTrigger>
        <SelectContent>
          {collections.data?.map((collection) => (
            <SelectItem key={collection.id} value={collection.id}>
              {collection.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Zona de soltar: borda tracejada que acende em ciano quando um arquivo passa por cima. */}
      <button
        type="button"
        onClick={() => input.current?.click()}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          void send(event.dataTransfer.files);
        }}
        disabled={progress !== null}
        className={cn(
          "mt-3 flex h-36 w-full flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-white/15 text-center transition-all duration-300",
          dragging &&
            "scale-[1.02] border-neon-cyan bg-neon-cyan/10 shadow-[0_0_32px_-6px_var(--neon-cyan),inset_0_0_24px_-8px_var(--neon-cyan)]",
        )}
      >
        <motion.span animate={dragging ? { y: -6, scale: 1.15 } : { y: 0, scale: 1 }} transition={SPRING}>
          <CloudUpload className={cn("size-7 text-muted-foreground", dragging && "text-neon-cyan")} aria-hidden />
        </motion.span>
        {progress === null ? (
          <span className="text-[13px] text-muted-foreground">
            <span className="text-foreground">Solte um arquivo</span> ou clique para escolher
            <br />
            PDF, DOCX, TXT ou MD, até 25 MB
          </span>
        ) : (
          <span className="w-3/4">
            <span className="block text-[13px]">Enviando {Math.round(progress * 100)}%</span>
            <span className="mt-2 block h-1.5 overflow-hidden rounded-full bg-white/10">
              <motion.span
                className="block h-full rounded-full bg-gradient-to-r from-neon-cyan to-neon-violet"
                animate={{ width: `${progress * 100}%` }}
                transition={SPRING}
              />
            </span>
          </span>
        )}
      </button>
      <input
        ref={input}
        type="file"
        accept=".pdf,.docx,.txt,.md"
        className="sr-only"
        tabIndex={-1}
        onChange={(event) => {
          void send(event.target.files);
          event.target.value = "";
        }}
      />
    </GlassCard>
  );
}

function AskCard() {
  return (
    <GlassCard className="flex flex-col justify-between p-6">
      <div>
        <h2 className="text-[15px] font-semibold">Pergunte aos documentos</h2>
        <p className="mt-1 text-[13px] text-muted-foreground">
          As respostas citam o documento e a página de onde vieram.
        </p>
      </div>
      <Link
        href="/perguntar"
        className="neon-ring mt-6 block rounded-xl bg-card px-4 py-3 text-[14px] text-muted-foreground transition-colors hover:text-foreground"
      >
        Qual é o prazo de garantia do compressor CX-200?
      </Link>
    </GlassCard>
  );
}

/* ------------------------------------------------------------- Documentos recentes */

function RecentDocumentsCard() {
  const recent = useQuery({
    queryKey: ["recent-documents"],
    queryFn: () => unwrap(api.GET("/api/v1/documents", { params: { query: { limit: 5 } } })),
  });

  return (
    <GlassCard tilt={false} className="p-6">
      <div className="flex items-baseline justify-between">
        <h2 className="text-[15px] font-semibold">Documentos recentes</h2>
        <Link href="/biblioteca" className="text-[13px] text-primary hover:underline">
          Ver todos
        </Link>
      </div>
      {recent.data?.items.length === 0 && (
        <p className="mt-6 text-[13px] text-muted-foreground">Nenhum documento ainda. Envie o primeiro ao lado.</p>
      )}
      <ul className="mt-3 space-y-1">
        <AnimatePresence initial={false}>
          {recent.data?.items.map((document, index) => (
            <motion.li
              key={document.id}
              layout
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ ...SPRING, delay: index * 0.04 }}
            >
              <Link
                href={`/documentos/${document.id}`}
                className="flex items-center gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-white/5"
              >
                <FileText className="size-4 shrink-0 text-muted-foreground" aria-hidden />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[14px]">{document.title}</span>
                  <span className="block text-[12px] text-muted-foreground">{formatRelative(document.created_at)}</span>
                </span>
                <StatusBadge status={document.status} />
              </Link>
            </motion.li>
          ))}
        </AnimatePresence>
      </ul>
    </GlassCard>
  );
}
