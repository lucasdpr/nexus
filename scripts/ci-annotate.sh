#!/usr/bin/env bash
# Transforma o fim de um arquivo de log em uma anotação de erro do GitHub Actions.
# Anotações aparecem na API pública (check-runs/<id>/annotations), sem abrir a página de logs.
# Uso: ci-annotate.sh <arquivo> <titulo>
set -euo pipefail

file="$1"
title="$2"
# As anotações têm limite de tamanho: fica só o final do log, onde costuma estar o erro.
message="$(tail -c 3000 "$file")"
# Caracteres especiais do formato de comando do GitHub.
message="${message//'%'/'%25'}"
message="${message//$'\r'/'%0D'}"
message="${message//$'\n'/'%0A'}"
echo "::error title=${title}::${message}"
