'use strict';

// UI compartilhada: leitura de arquivo como data URL (Refatoração UBX-V3,
// Etapa 5 — extraído de static/app.js).
//
// fileToDataUrl (arquivo bruto) e fileToJpegDataUrl (imagem redimensionada e
// convertida em JPEG num canvas de fundo branco), usados pela foto do EPI e
// pelos logotipos da plataforma/empresa. Camada UI: FileReader, Image, canvas.
//
// Eram `async function` de bloco no app.js (sem Annex B): só o app.js as via.
// Agora são publicadas em globalThis e o app.js e o cadastro de EPI chegam a
// elas pelo nome. Corpos e mensagens idênticos (inclusive o caractere invisível
// U+00AD em "possí­vel" de fileToJpegDataUrl, preservado de propósito).
(function () {
  if (globalThis.__EPI_MODULE_SHARED_FILE_DATA_URL_LOADED__) { return; }
  globalThis.__EPI_MODULE_SHARED_FILE_DATA_URL_LOADED__ = true;

  async function fileToDataUrl(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error('Não foi possível ler o arquivo do logotipo.'));
      reader.onload = () => resolve(typeof reader.result === 'string' ? reader.result : '');
      reader.readAsDataURL(file);
    });
  }

  async function fileToJpegDataUrl(file, maxWidth = 720) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error('Não foi possí­vel ler o arquivo do logotipo.'));
      reader.onload = () => {
        const image = new Image();
        image.onerror = () => reject(new Error('Não foi possí­vel processar o logotipo enviado.'));
        image.onload = () => {
          const scale = Math.min(1, maxWidth / (image.width || maxWidth));
          const canvas = document.createElement('canvas');
          canvas.width = Math.max(1, Math.round(image.width * scale));
          canvas.height = Math.max(1, Math.round(image.height * scale));
          const context = canvas.getContext('2d');
          context.fillStyle = '#ffffff';
          context.fillRect(0, 0, canvas.width, canvas.height);
          context.drawImage(image, 0, 0, canvas.width, canvas.height);
          resolve(canvas.toDataURL('image/jpeg', 0.92));
        };
        image.src = typeof reader.result === 'string' ? reader.result : '';
      };
      reader.readAsDataURL(file);
    });
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const fileDataUrlExports = {
    fileToDataUrl,
    fileToJpegDataUrl
  };

  for (const [name, fn] of Object.entries(fileDataUrlExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_SHARED_FILE_DATA_URL__ = Object.freeze({ ...fileDataUrlExports });
})();
