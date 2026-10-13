"use client";

import { Check, CircleAlert } from "lucide-react";
import { motion } from "motion/react";

import { SPRING } from "@/components/fx/motion";
import type { DocumentDetail } from "@/lib/api/client";
import { cn } from "@/lib/utils";

type Step = DocumentDetail["steps"][number];

const STEP_NAMES: Record<Step["step"], string> = {
  UPLOAD: "Upload e validação",
  EXTRACT: "Extração do texto",
  CHUNK: "Divisão em trechos",
  EMBED: "Embeddings",
  INDEX: "Indexação",
};

/**
 * Linha do tempo do processamento como um conduto: o líquido luminoso enche o tubo até a
 * etapa em andamento, numa mola. Etapa com falha treme uma vez e acende em vermelho.
 */
export function IngestionPipeline({ steps, error }: { steps: Step[]; error?: string | null }) {
  const done = steps.filter((step) => step.status === "DONE").length;
  const running = steps.some((step) => step.status === "RUNNING");
  const failed = steps.some((step) => step.status === "FAILED");
  // Cada etapa ocupa um trecho do tubo; a que está rodando conta como meio trecho cheio.
  const fill = steps.length > 1 ? Math.min(1, (done - 1 + (running ? 0.5 : 0)) / (steps.length - 1)) : 1;

  return (
    <div className="relative">
      {/* Tubo vazio (vidro) e o líquido que o preenche. */}
      <div aria-hidden className="absolute top-3 bottom-3 left-[11px] w-1.5 overflow-hidden rounded-full bg-white/[0.06] ring-1 ring-white/10">
        <motion.div
          className={cn(
            "w-full rounded-full bg-gradient-to-b",
            failed ? "from-neon-violet via-neon-indigo to-neon-red" : "from-neon-cyan via-neon-violet to-neon-emerald",
          )}
          initial={{ height: 0 }}
          animate={{ height: `${Math.max(0, fill) * 100}%` }}
          transition={SPRING}
          style={{ boxShadow: "0 0 12px var(--neon-violet)" }}
        />
      </div>

      <ol className="relative space-y-4">
        {steps.map((step) => (
          <motion.li
            key={step.step}
            className="flex items-start gap-3"
            animate={step.status === "FAILED" ? { x: [0, -4, 4, -3, 3, 0] } : { x: 0 }}
            transition={{ duration: 0.45 }}
          >
            <StepNode status={step.status} />
            <div className="min-w-0 pt-0.5">
              <p className={cn("text-[14px]", step.status === "PENDING" && "text-muted-foreground")}>
                {STEP_NAMES[step.step]}
              </p>
              {step.status === "FAILED" && (
                <span className="mt-1 inline-flex rounded-full bg-rose-500/15 px-2 py-0.5 text-[12px] font-medium text-rose-300 ring-1 ring-rose-500/50 shadow-[0_0_14px_-2px_var(--neon-red)]">
                  Falhou
                </span>
              )}
              {step.error && <p className="mt-1 text-[13px] text-rose-300">{step.error}</p>}
            </div>
          </motion.li>
        ))}
      </ol>
      {error && <p className="mt-4 text-[13px] text-rose-300">{error}</p>}
    </div>
  );
}

function StepNode({ status }: { status: Step["status"] }) {
  const base = "relative grid size-6 shrink-0 place-items-center rounded-full ring-1";
  if (status === "DONE") {
    return (
      <motion.span
        initial={{ scale: 0.6 }}
        animate={{ scale: 1 }}
        transition={SPRING}
        className={cn(base, "bg-emerald-400/20 text-emerald-300 ring-emerald-400/50 shadow-[0_0_10px_-2px_var(--neon-emerald)]")}
        aria-label="Concluída"
      >
        <Check className="size-3.5" aria-hidden />
      </motion.span>
    );
  }
  if (status === "RUNNING") {
    return (
      <span className={cn(base, "bg-neon-violet/20 ring-neon-violet/60")} aria-label="Em andamento">
        <span className="absolute inset-0 animate-ping rounded-full bg-neon-violet/40" aria-hidden />
        <span className="size-2 rounded-full bg-fuchsia-300 shadow-[0_0_8px_var(--neon-violet)]" aria-hidden />
      </span>
    );
  }
  if (status === "FAILED") {
    return (
      <span className={cn(base, "bg-rose-500/20 text-rose-300 ring-rose-500/60 shadow-[0_0_12px_var(--neon-red)]")} aria-label="Falhou">
        <CircleAlert className="size-3.5" aria-hidden />
      </span>
    );
  }
  return (
    <span className={cn(base, "bg-background ring-white/15")} aria-label="Pendente">
      <span className="size-1.5 rounded-full bg-muted-foreground/60" aria-hidden />
    </span>
  );
}
