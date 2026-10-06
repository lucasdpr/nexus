"use client";

import "react-pdf/dist/Page/TextLayer.css";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";

import { Button } from "@/components/ui/button";

// Precisa ficar no mesmo módulo que usa <Document> (ver README do react-pdf).
pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();

const normalize = (text: string) => text.normalize("NFKC").replace(/\s+/g, " ").trim().toLowerCase();
const escapeHtml = (text: string) => text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

type Props = {
  url: string;
  initialPage: number;
  /** Texto do trecho citado: as linhas da página que fazem parte dele recebem o marca-texto. */
  evidence?: string;
  evidencePage?: number | null;
};

export default function PdfViewer({ url, initialPage, evidence, evidencePage }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(800);
  const [pages, setPages] = useState<number>();
  const [page, setPage] = useState(initialPage);

  useEffect(() => {
    const element = container.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.min(entry.contentRect.width, 900)));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const target = evidence ? normalize(evidence) : "";
  const renderText = useCallback(
    ({ str }: { str: string }) => {
      const line = normalize(str);
      const isEvidence = target && page === evidencePage && line.length >= 4 && target.includes(line);
      return isEvidence ? `<mark class="pdf-evidence">${escapeHtml(str)}</mark>` : escapeHtml(str);
    },
    [target, page, evidencePage],
  );

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-center gap-2 border-b border-border px-4 py-2">
        <Button variant="ghost" size="icon" disabled={page <= 1} onClick={() => setPage(page - 1)} aria-label="Página anterior">
          <ChevronLeft aria-hidden />
        </Button>
        <span className="min-w-28 text-center text-[13px]" aria-live="polite">
          Página {page}
          {pages ? ` de ${pages}` : ""}
        </span>
        <Button
          variant="ghost"
          size="icon"
          disabled={!pages || page >= pages}
          onClick={() => setPage(page + 1)}
          aria-label="Próxima página"
        >
          <ChevronRight aria-hidden />
        </Button>
        {evidencePage && page !== evidencePage && (
          <Button variant="outline" size="sm" onClick={() => setPage(evidencePage)}>
            Voltar ao trecho citado
          </Button>
        )}
      </div>
      <div ref={container} className="min-h-0 flex-1 overflow-auto bg-muted/50 px-4 py-6">
        <Document
          file={url}
          suspense={false}
          onLoadSuccess={({ numPages }) => {
            setPages(numPages);
            setPage((current) => Math.min(Math.max(current, 1), numPages));
          }}
          loading={<p className="py-20 text-center text-muted-foreground">Abrindo o PDF…</p>}
          error={<p className="py-20 text-center text-destructive">Não foi possível abrir o PDF.</p>}
          className="flex justify-center"
        >
          <Page
            pageNumber={page}
            width={width}
            renderAnnotationLayer={false}
            customTextRenderer={renderText}
            className="overflow-hidden rounded-sm shadow-sm ring-1 ring-border"
            loading={<div style={{ width, height: width * 1.414 }} className="bg-card" />}
          />
        </Document>
      </div>
    </div>
  );
}
