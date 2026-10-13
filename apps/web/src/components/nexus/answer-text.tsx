"use client";

import { AnimatePresence, motion } from "motion/react";
import { Fragment, useState } from "react";

import { SPRING } from "@/components/fx/motion";
import { cn } from "@/lib/utils";

const MARKER = /\[S(\d+)\]/g;
const BOLD = /\*\*(.+?)\*\*/g;

export type CitationPreview = { title: string | null; page: number | null; quote: string | null };

type Props = {
  text: string;
  /** Marcadores que existem (citações válidas ou fontes recuperadas). */
  markers: Set<number>;
  /** Dados de cada fonte, para a prévia em gota ao passar o mouse. */
  previews?: Map<number, CitationPreview>;
  activeMarker?: number | null;
  onCite?: (marker: number) => void;
  /** Mostra o cursor luminoso no fim do texto enquanto a resposta chega. */
  streaming?: boolean;
};

/**
 * Texto da resposta com as citações [S1] transformadas em pílulas neon.
 * Renderiza só parágrafos, listas e negrito: nenhum HTML vindo do modelo vai para a página.
 */
export function AnswerText({ text, streaming, ...rest }: Props) {
  const blocks = text.trim().split(/\n{2,}/);
  return (
    <div className="space-y-3 text-[15px] leading-relaxed">
      {blocks.map((block, index) => {
        const last = index === blocks.length - 1;
        const caret = streaming && last ? <Caret /> : null;
        const lines = block.split("\n");
        if (lines.every((line) => /^\s*([-*•]|\d+\.)\s+/.test(line))) {
          return (
            <ul key={index} className="list-disc space-y-1 pl-5 marker:text-neon-violet">
              {lines.map((line, item) => (
                <li key={item}>
                  <Inline text={line.replace(/^\s*([-*•]|\d+\.)\s+/, "")} {...rest} />
                  {item === lines.length - 1 && caret}
                </li>
              ))}
            </ul>
          );
        }
        return (
          <p key={index} className="max-w-[68ch]">
            <Inline text={lines.join(" ")} {...rest} />
            {caret}
          </p>
        );
      })}
    </div>
  );
}

/** Cursor de brilho contínuo no fim da resposta em streaming. */
function Caret() {
  return (
    <span
      aria-hidden
      className="animate-caret ml-0.5 inline-block h-[1.05em] w-[3px] translate-y-[3px] rounded-full bg-neon-cyan shadow-[0_0_10px_var(--neon-cyan)]"
    />
  );
}

function Inline({ text, markers, previews, activeMarker, onCite }: Omit<Props, "streaming">) {
  const parts: React.ReactNode[] = [];
  let last = 0;
  for (const match of text.matchAll(MARKER)) {
    const marker = Number(match[1]);
    parts.push(<Bold key={`t${last}`} text={text.slice(last, match.index)} />);
    parts.push(
      markers.has(marker) ? (
        <CitationPill
          key={`m${match.index}`}
          marker={marker}
          preview={previews?.get(marker)}
          active={activeMarker === marker}
          onClick={() => onCite?.(marker)}
        />
      ) : null,
    );
    last = (match.index ?? 0) + match[0].length;
  }
  parts.push(<Bold key="fim" text={text.slice(last)} />);
  return <>{parts}</>;
}

/**
 * Pílula da citação. Ao passar o mouse (ou focar), a prévia nasce da própria pílula: começa
 * como uma gota pequena e redonda e se abre num cartão, numa mola.
 */
function CitationPill({
  marker,
  preview,
  active,
  onClick,
}: {
  marker: number;
  preview?: CitationPreview;
  active: boolean;
  onClick: () => void;
}) {
  const [open, setOpen] = useState(false);
  const show = () => setOpen(true);
  const hide = () => setOpen(false);

  return (
    <span className="relative inline-block" onMouseEnter={show} onMouseLeave={hide}>
      <motion.button
        type="button"
        onClick={onClick}
        onFocus={show}
        onBlur={hide}
        whileHover={{ scale: 1.15 }}
        whileTap={{ scale: 0.9 }}
        transition={SPRING}
        aria-label={preview?.title ? `Fonte ${marker}: ${preview.title}` : `Ver fonte ${marker}`}
        className={cn(
          "mx-0.5 inline-grid h-[19px] min-w-[22px] place-items-center rounded-full bg-gradient-to-r from-[#a21fe6] to-[#4f52d9] px-1.5 align-[2px] text-[11px] font-semibold text-white shadow-[0_0_12px_-2px_var(--neon-violet)]",
          active && "ring-2 ring-neon-cyan ring-offset-2 ring-offset-background",
        )}
      >
        S{marker}
      </motion.button>

      <AnimatePresence>
        {open && preview?.title && (
          <motion.span
            role="tooltip"
            initial={{ opacity: 0, scale: 0.2, borderRadius: 999, x: "-50%", y: 6 }}
            animate={{ opacity: 1, scale: 1, borderRadius: 16, x: "-50%", y: 0 }}
            exit={{ opacity: 0, scale: 0.4, borderRadius: 999, x: "-50%", y: 4 }}
            transition={SPRING}
            style={{ transformOrigin: "50% 100%" }}
            className="glass absolute bottom-full left-1/2 z-30 mb-2 block w-[min(20rem,80vw)] p-4 text-left shadow-[0_20px_50px_-12px_rgb(0_0_0/0.8),0_0_30px_-10px_var(--neon-violet)]"
          >
            <span className="block text-[13px] font-semibold text-foreground">{preview.title}</span>
            <span className="block text-[12px] text-muted-foreground">
              {preview.page ? `Página ${preview.page}` : "Documento sem páginas"}
            </span>
            {preview.quote && (
              <span className="document-voice mt-2 line-clamp-4 block text-[14px] text-foreground/90">
                <mark className="evidence-mark text-inherit">{preview.quote}</mark>
              </span>
            )}
          </motion.span>
        )}
      </AnimatePresence>
    </span>
  );
}

function Bold({ text }: { text: string }) {
  const pieces = text.split(BOLD);
  return (
    <>
      {pieces.map((piece, index) =>
        index % 2 === 1 ? (
          <strong key={index} className="font-semibold">
            {piece}
          </strong>
        ) : (
          <Fragment key={index}>{piece}</Fragment>
        ),
      )}
    </>
  );
}
