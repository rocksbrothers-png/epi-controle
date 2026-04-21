# Deploy Docker no Render com OCR (Tesseract)

## O que foi configurado

- `Dockerfile` com:
  - Python 3.11 slim
  - `tesseract-ocr` e `tesseract-ocr-por`
  - `tesseract-ocr-eng` (fallback de idioma)
  - `libgl1` e `libglib2.0-0` (OpenCV runtime)
  - validação de OCR no build via `python scripts/check_ocr_runtime.py`.
- `render.yaml` ajustado para `env: docker` e uso de `./Dockerfile`.
- `TESSERACT_CMD=/usr/bin/tesseract` via variável de ambiente.

## Como publicar no Render

1. No serviço, selecione **Blueprint** (ou conecte o `render.yaml`).
2. Garanta que a branch de deploy contém:
   - `Dockerfile`
   - `render.yaml`
3. Faça **manual deploy** com **Clear build cache**.
4. Após subir, valide:
   - endpoint `GET /api/ocr/runtime-status`
   - leitura da ferramenta “Capturar data por câmera”.

## Verificações recomendadas após deploy

- `GET /api/ocr/runtime-status` deve retornar:
  - `ready: true`
  - `tesseract_cmd: /usr/bin/tesseract`
  - `tesseract_has_por: true`
  - versão CLI e versão via pytesseract preenchidas.

Se `ready: false`, verifique logs do deploy e confirme se o serviço está usando o Dockerfile atualizado.
Se estiver usando Render sem Docker, o backend agora tenta localizar Tesseract também em caminhos comuns do Render (`/opt/render/project/.apt/usr/bin/tesseract`).
