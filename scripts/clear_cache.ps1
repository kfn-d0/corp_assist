# =============================================================
# clear_cache.ps1 — Limpa bytecode Python compilado (Windows)
# Uso: powershell -ExecutionPolicy Bypass -File clear_cache.ps1
# Deve ser executado antes de subir o servidor para evitar que
# Python execute bytecode .pyc antigo (cache de versao anterior).
# =============================================================

Write-Host "Apagando __pycache__ e arquivos .pyc..."

# Remove todos os diretorios __pycache__
Get-ChildItem -Path . -Filter "__pycache__" -Recurse -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Remove arquivos .pyc soltos
Get-ChildItem -Path . -Filter "*.pyc" -Recurse -File | Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "Cache limpo com sucesso."
