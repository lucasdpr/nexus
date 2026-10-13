import { cn } from "@/lib/utils";

type Status = "UPLOADED" | "PROCESSING" | "READY" | "FAILED";

const STATUS: Record<Status, { label: string; pill: string; dot: string; pulse?: boolean }> = {
  UPLOADED: {
    label: "Na fila",
    pill: "bg-white/5 text-zinc-300 ring-white/15",
    dot: "bg-zinc-400",
  },
  PROCESSING: {
    label: "Processando",
    pill: "bg-amber-400/10 text-amber-300 ring-amber-400/30",
    dot: "bg-amber-300 shadow-[0_0_8px_#fcd34d]",
    pulse: true,
  },
  READY: {
    label: "Pronto",
    pill: "bg-emerald-400/10 text-emerald-300 ring-emerald-400/30",
    dot: "bg-emerald-300 shadow-[0_0_8px_#6ee7b7]",
  },
  FAILED: {
    label: "Falhou",
    pill: "bg-rose-500/10 text-rose-300 ring-rose-500/40",
    dot: "bg-rose-400 shadow-[0_0_8px_#fb7185]",
  },
};

/** Estado do documento numa pílula fluorescente. A cor nunca aparece sozinha: sempre com o nome. */
export function StatusBadge({ status, className }: { status: Status; className?: string }) {
  const { label, pill, dot, pulse } = STATUS[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[12px] font-medium whitespace-nowrap ring-1",
        pill,
        className,
      )}
    >
      <span aria-hidden className={cn("size-1.5 rounded-full", dot, pulse && "animate-pulse")} />
      {label}
    </span>
  );
}

export function isPending(status: Status): boolean {
  return status === "UPLOADED" || status === "PROCESSING";
}
