#!/bin/bash
# =============================================================
# clear_cache.sh — Limpa bytecode Python compilado
# Uso no CentOS (VM): bash clear_cache.sh
# Deve ser executado antes de subir o servidor para evitar que
# Python execute bytecode .pyc antigo (cache de versão anterior).
# =============================================================

echo "Apagando __pycache__ e arquivos .pyc..."

# Remove todos os diretórios __pycache__
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Remove arquivos .pyc soltos (caso existam fora de __pycache__)
find . -name "*.pyc" -delete 2>/dev/null

echo "Cache limpo com sucesso."
