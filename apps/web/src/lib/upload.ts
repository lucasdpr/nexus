import { ApiError, errorMessage, type DocumentDetail } from "@/lib/api/client";

/**
 * A Vercel recusa corpos de requisição acima de ~4,5 MB. Acima deste tamanho o navegador
 * envia o arquivo direto à API (que aceita até 25 MB), com um token curto pedido antes.
 */
const DIRECT_THRESHOLD_BYTES = 4 * 1024 * 1024;

type UploadToken = { token: string; upload_url: string | null; expires_in: number };

/**
 * Envio de documento com progresso. Usa XMLHttpRequest porque `fetch` não informa o
 * progresso do upload, e arquivos de até 25 MB pedem esse retorno visual.
 */
export async function uploadDocument(
  file: File,
  collectionId: string,
  onProgress: (fraction: number) => void,
): Promise<DocumentDetail> {
  const form = new FormData();
  form.append("collection_id", collectionId);

  let url = "/api/v1/documents";
  if (file.size > DIRECT_THRESHOLD_BYTES) {
    const direct = await requestDirectUpload();
    if (direct?.upload_url) {
      url = direct.upload_url;
      form.append("token", direct.token);
    }
  }
  form.append("file", file);

  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", url);
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

/** Pede o token pela rota normal (com o cookie). Sem endereço público da API, devolve sem URL. */
async function requestDirectUpload(): Promise<UploadToken | null> {
  const response = await fetch("/api/v1/documents/upload-token", { method: "POST", credentials: "same-origin" });
  if (!response.ok) {
    throw new ApiError(errorMessage(await response.json().catch(() => null), "Não foi possível iniciar o envio."), response.status);
  }
  return (await response.json()) as UploadToken;
}
