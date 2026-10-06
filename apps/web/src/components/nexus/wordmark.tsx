import { cn } from "@/lib/utils";

/** Marca do produto: o nome com a barra do marca-texto sob as letras, como um trecho destacado. */
export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn("relative inline-flex items-baseline font-semibold tracking-[0.08em]", className)}>
      <span
        aria-hidden
        className="absolute inset-x-[-0.15em] bottom-[0.08em] h-[0.42em] rounded-[2px] bg-evidence/80"
      />
      <span className="relative">NEXUS</span>
    </span>
  );
}
