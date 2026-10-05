#!/usr/bin/env bash
# Teste de fumaça contra o ambiente do docker compose, passando por toda a cadeia:
# navegador → web (proxy /api) → API → banco → fila → worker.
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3000}"
ADMIN_EMAIL="admin@novaforja.example.com"
ADMIN_PASSWORD="${SEED_ADMIN_PASSWORD:-nexus-admin-local}"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

api() { curl -fsS -H "Origin: $BASE_URL" -b "$WORKDIR/cookies" -c "$WORKDIR/cookies" "$@"; }

echo "1. API respondendo pelo proxy do web"
curl -fsS --retry 20 --retry-connrefused --retry-delay 2 "$BASE_URL/api/health" > /dev/null

echo "2. Entrada como visitante"
curl -fsS -X POST -H "Origin: $BASE_URL" "$BASE_URL/api/v1/auth/demo" > /dev/null

echo "3. Login do administrador da demonstração"
api -X POST -H "Content-Type: application/json" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" \
  "$BASE_URL/api/v1/auth/login" > /dev/null

echo "4. Envio de documento"
collection_id="$(api "$BASE_URL/api/v1/collections" | jq -r '.[0].id')"
printf 'Procedimento de bloqueio %s\n\nDesligue a chave geral antes da manutenção.\n' "$(date +%s%N)" \
  > "$WORKDIR/procedimento.md"
document_id="$(
  api -F "collection_id=$collection_id" -F "file=@$WORKDIR/procedimento.md" \
    "$BASE_URL/api/v1/documents" | jq -r '.id'
)"

echo "5. Processamento pelo worker"
for _ in $(seq 1 45); do
  status="$(api "$BASE_URL/api/v1/documents/$document_id" | jq -r '.status')"
  case "$status" in
    READY) echo "Documento processado."; exit 0 ;;
    FAILED) echo "O processamento falhou." >&2; exit 1 ;;
  esac
  sleep 2
done
echo "Tempo esgotado: o documento ficou em $status." >&2
exit 1
