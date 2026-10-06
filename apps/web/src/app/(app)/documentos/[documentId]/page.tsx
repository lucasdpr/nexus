import type { Metadata } from "next";

import { DocumentView } from "./document-view";

export const metadata: Metadata = { title: "Documento" };

export default async function DocumentPage({ params, searchParams }: PageProps<"/documentos/[documentId]">) {
  const { documentId } = await params;
  const query = await searchParams;
  const page = Number(query.pagina);
  return (
    <DocumentView
      documentId={documentId}
      initialPage={Number.isInteger(page) && page > 0 ? page : 1}
      chunkId={typeof query.trecho === "string" ? query.trecho : undefined}
    />
  );
}
