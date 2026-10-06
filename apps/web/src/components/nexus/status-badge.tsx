import { cn } from "@/lib/utils";

type Status = "UPLOADED" | "PROCESSING" | "READY" | "FAILED";

const STATUS: Record<Status, { label: string; dot: string; pulse?: boolean }> = {
  UPLOADED: { label: "Na fila", dot: "bg-muted-foreground" },
  PROCESSING: { label: "Processando", dot: "bg-status-processing", pulse: true },
  READY: { label: "Pronto", dot: "bg-status-ready" },
  FAILED: { label: "Falhou", dot: "bg-status-failed" },
};

/** Estado do documento no pipeline. A cor nunca aparece sozinha: sempre com o nome. */
export function StatusBadge({ status, className }: { status: Status; className?: string }) {
  const { label, dot, pulse } = STATUS[status];
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-[13px] whitespace-nowrap", className)}>
      <span aria-hidden className={cn("size-2 rounded-full", dot, pulse && "animate-pulse")} />
      {label}
    </span>
  );
}

export function isPending(status: Status): boolean {
  return status === "UPLOADED" || status === "PROCESSING";
}
