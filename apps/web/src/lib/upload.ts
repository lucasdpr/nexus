import { ApiError, errorMessage, type DocumentDetail } from "@/lib/api/client";

/**
 * Envio de documento com progresso. Usa XMLHttpRequest porque `fetch` não informa o
 * progresso do upload, e arquivos de até 25 MB pedem esse retorno visual.
 */
export function uploadDocument(
  file: File,
  collectionId: string,
  onProgress: (fraction: number) => void,
): Promise<DocumentDetail> {
  const form = new FormData();
  form.append("collection_id", collectionId);
  form.append("file", file);

  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", "/api/v1/documents");
    request.responseType = "json";
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total);
    };
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) {
        resolve(request.response as DocumentDetail);
      } else {
        reject(new ApiError(errorMessage(request.response, "Não foi possível enviar o arquivo."), request.status));
      }
    };
    request.onerror = () => reject(new ApiError("Sem conexão com o servidor.", 0));
    request.send(form);
  });
}
