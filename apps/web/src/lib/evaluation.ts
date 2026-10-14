/**
 * Resultado da avaliação do RAG (apps/api/demo: `python -m demo.evaluate --chat`) contra o
 * ambiente no ar, com 22 perguntas sobre 7 documentos fictícios. Atualize junto com
 * apps/api/demo/last-report.json.
 */
export const EVALUATION = {
  questions: 22,
  answerable: 18,
  unanswerable: 4,
  documents: 7,
  search: {
    top1: 0.78,
    top5: 1.0,
    mrr: 0.875,
  },
  answers: {
    // 18 das 18 perguntas com resposta: respondeu, citou o documento e a página certos e trouxe o fato.
    correct: 1,
    // Das 4 perguntas sem resposta nos documentos, quantas ele recusou em vez de inventar.
    refused: 1,
  },
  embeddings: "locais, por hash de palavras (o Voyage AI ainda não está ligado)",
};

export const percent = (value: number) => `${Math.round(value * 100)}%`;
