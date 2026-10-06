import Link from "next/link";

import { cn } from "@/lib/utils";

type Cell = { label: string; value: React.ReactNode };

export type SourceCardProps = {
  /** Número da fonte na resposta, como em [1]. */
  marker: number;
  documentTitle: string;
  page: number | null;
  quote: string;
  /** Trecho do `quote` que sustenta a resposta; recebe o marca-texto. */
  highlight?: string;
  collection?: string;
  version?: number;
  href?: string;
  className?: string;
};

/**
 * Fonte de uma resposta, desenhada como o carimbo de um desenho técnico: o trecho do
 * documento em cima e, embaixo, uma grade com as informações que identificam a origem.
 */
export function SourceCard({
  marker,
  documentTitle,
  page,
  quote,
  highlight,
  collection,
  version,
  href,
  className,
}: SourceCardProps) {
  const cells: Cell[] = [
    { label: "Documento", value: documentTitle },
    { label: "Página", value: page ?? "Sem páginas" },
    ...(collection ? [{ label: "Coleção", value: collection }] : []),
    ...(version ? [{ label: "Versão", value: version }] : []),
  ];

  const body = (
    <>
      <div className="flex gap-3 p-4">
        <span
          aria-label={`Fonte ${marker}`}
          className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-sm bg-evidence text-[11px] font-semibold text-evidence-foreground"
        >
          {marker}
        </span>
        <blockquote className="document-voice line-clamp-6 text-[15px] text-card-foreground">
          <Quote text={quote} highlight={highlight} />
        </blockquote>
      </div>
      <dl
        className="grid border-t border-border"
        style={{ gridTemplateColumns: `minmax(0, 2fr) repeat(${cells.length - 1}, minmax(0, 1fr))` }}
      >
        {cells.map((cell, index) => (
          <div key={cell.label} className={cn("min-w-0 px-3 py-2", index > 0 && "border-l border-border")}>
            <dt className="text-[11px] text-muted-foreground">{cell.label}</dt>
            <dd className="line-clamp-2 text-[13px] leading-snug font-medium">{cell.value}</dd>
          </div>
        ))}
      </dl>
    </>
  );

  const frame = cn(
    "block overflow-hidden rounded-md border border-border bg-card text-left",
    href && "transition-colors hover:border-primary/60 focus-visible:border-primary",
    className,
  );

  return href ? (
    <Link href={href} className={frame}>
      {body}
    </Link>
  ) : (
    <article className={frame}>{body}</article>
  );
}

function Quote({ text, highlight }: { text: string; highlight?: string }) {
  const start = highlight ? text.indexOf(highlight) : -1;
  if (!highlight || start < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, start)}
      <mark className="evidence-mark text-inherit">{highlight}</mark>
      {text.slice(start + highlight.length)}
    </>
  );
}
