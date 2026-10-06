import { Fragment } from "react";

import { cn } from "@/lib/utils";

const MARKER = /\[S(\d+)\]/g;
const BOLD = /\*\*(.+?)\*\*/g;

type Props = {
  text: string;
  /** Marcadores que existem (citações válidas ou fontes recuperadas). */
  markers: Set<number>;
  activeMarker?: number | null;
  onCite?: (marker: number) => void;
};

/**
 * Texto da resposta com as citações [S1] transformadas em selos clicáveis.
 * Renderiza só parágrafos, listas e negrito: nenhum HTML vindo do modelo vai para a página.
 */
export function AnswerText({ text, markers, activeMarker, onCite }: Props) {
  const blocks = text.trim().split(/\n{2,}/);
  return (
    <div className="space-y-3 text-[15px] leading-relaxed">
      {blocks.map((block, index) => {
        const lines = block.split("\n");
        if (lines.every((line) => /^\s*([-*•]|\d+\.)\s+/.test(line))) {
          return (
            <ul key={index} className="list-disc space-y-1 pl-5 marker:text-muted-foreground">
              {lines.map((line, item) => (
                <li key={item}>
                  <Inline text={line.replace(/^\s*([-*•]|\d+\.)\s+/, "")} {...{ markers, activeMarker, onCite }} />
                </li>
              ))}
            </ul>
          );
        }
        return (
          <p key={index} className="max-w-[68ch]">
            <Inline text={lines.join(" ")} {...{ markers, activeMarker, onCite }} />
          </p>
        );
      })}
    </div>
  );
}

function Inline({ text, markers, activeMarker, onCite }: Props) {
  const parts: React.ReactNode[] = [];
  let last = 0;
  for (const match of text.matchAll(MARKER)) {
    const marker = Number(match[1]);
    parts.push(<Bold key={`t${last}`} text={text.slice(last, match.index)} />);
    parts.push(
      markers.has(marker) ? (
        <button
          key={`m${match.index}`}
          type="button"
          onClick={() => onCite?.(marker)}
          aria-label={`Ver fonte ${marker}`}
          className={cn(
            "mx-0.5 inline-grid h-[18px] min-w-[18px] place-items-center rounded-sm bg-evidence px-1 align-[2px] text-[11px] font-semibold text-evidence-foreground transition-shadow",
            activeMarker === marker && "ring-2 ring-primary ring-offset-1 ring-offset-background",
          )}
        >
          {marker}
        </button>
      ) : null,
    );
    last = (match.index ?? 0) + match[0].length;
  }
  parts.push(<Bold key="fim" text={text.slice(last)} />);
  return <>{parts}</>;
}

function Bold({ text }: { text: string }) {
  const pieces = text.split(BOLD);
  return (
    <>
      {pieces.map((piece, index) =>
        index % 2 === 1 ? <strong key={index} className="font-semibold">{piece}</strong> : <Fragment key={index}>{piece}</Fragment>,
      )}
    </>
  );
}
