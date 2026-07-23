# ── Stage 1: Flutter Web builder ─────────────────────────────────────────────
# Builds the Flutter Web app; only the output is copied into the final image.
FROM debian:bookworm-slim AS flutter-builder

# Melos 8.x + pub workspaces exige Dart SDK >= 3.9.0 (ver flutter/pubspec.yaml).
# O pin anterior (3.24.5 -> Dart 3.5.x) ficou incompatível; segue `stable` como
# os demais builds Flutter do projeto (Dockerfile.web, render.yaml).
ARG FLUTTER_VERSION=stable
ENV FLUTTER_HOME=/opt/flutter \
    PUB_CACHE=/root/.pub-cache
ENV PATH="$FLUTTER_HOME/bin:$FLUTTER_HOME/bin/cache/dart-sdk/bin:$PUB_CACHE/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git unzip xz-utils ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Clone Flutter SDK — layer cached until FLUTTER_VERSION changes
RUN git clone --depth 1 --branch $FLUTTER_VERSION \
    https://github.com/flutter/flutter.git $FLUTTER_HOME \
    && flutter config --no-analytics \
       --no-enable-android --no-enable-ios --no-enable-linux-desktop \
       --no-enable-macos-desktop --no-enable-windows-desktop \
    && flutter precache --web

# Install Melos — separate layer for cache efficiency
RUN dart pub global activate melos

WORKDIR /src
COPY flutter/ .

RUN melos bootstrap \
    && melos run gen:l10n \
    && melos run gen \
    && melos run build:web

# ── Stage 2: Python runtime ───────────────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TESSERACT_CMD=/usr/bin/tesseract \
    OCR_REQUIRED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-por \
    tesseract-ocr-spa \
    tesseract-ocr-nor \
    tesseract-ocr-fra \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt

COPY . .

# Embed Flutter Web output — served by Python at /app/
COPY --from=flutter-builder /src/apps/epi_admin/build/web/ ./static/app/

# Marcador explícito no log de build para confirmar uso do Dockerfile no Render.
RUN echo "[render][docker] Build usando Dockerfile do repositório (multi-stage: Flutter Web + Python)."

# Gera static/index.html a partir dos fragmentos modulares (static/views/).
# Garante que o HTML servido em produção sempre reflita os fragmentos atuais.
RUN python scripts/build_index.py build

# Validação de runtime OCR no build (evita deploy quebrado em produção).
RUN python -m py_compile epi_backend/manufacture_date_ocr.py server_postgres.py app.py
RUN python -c "from epi_backend.manufacture_date_ocr import detect_manufacture_date, get_ocr_runtime_status; print('ocr_import_ok', callable(detect_manufacture_date), callable(get_ocr_runtime_status))"
RUN tesseract --version
RUN python -m pip show pytesseract
RUN python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
RUN python scripts/check_ocr_runtime.py --require
RUN python scripts/check_ocr_runtime.py

EXPOSE 8000

CMD ["sh", "-c", "python scripts/check_ocr_runtime.py --require && exec python app.py"]
