# SECURITY-PILLOW-13 — Pillow 13 e endurecimento da decodificação de imagens

## Motivo

O `pip-audit` de 17/11/2026 apontou 42 avisos (19 PYSEC, 22 CVE, 1 GHSA) no
Pillow 12.3.0, versão instalada em produção. Todos têm correção no 13.0.0. A
restrição `Pillow>=12.3.0,<13` impedia a atualização.

Os avisos cobrem estouro e leitura fora de memória em decodificadores (TIFF,
JPEG, BMP, MSP, FlashPix), laços infinitos e consumo de CPU ou memória
(GIF, MIC, EXIF, APNG), além de falhas nos caminhos de PDF e EPS.

## Alterações

1. `requirements.txt`: `Pillow>=13.0.0,<14`.
2. `epi_backend/image_signatures.py`: só PNG e JPEG chegam ao Pillow. O
   conteúdo precisa começar pela assinatura real do tipo declarado, e o
   `Image.open` recebe `formats=[<tipo declarado>]`, de modo que nenhum outro
   decodificador é tentado. Erros de identificação e bomba de descompressão
   viram `ValueError` com a mensagem já existente do ponto de chamada.
3. Os três pontos que decodificam imagem no servidor passam a usar essa regra:
   - foto do EPI no portal (`modules/safety_library/service.py`,
     `render_epi_photo`), que roda no processo principal;
   - OCR da etiqueta de lote (`epi_backend/lot_label_ocr.py`);
   - worker isolado de pré-visualização (`modules/safety_library/render_worker.py`),
     com a conferência feita no próprio worker, que roda com `sys.path` próprio.

Os limites existentes não mudam: 8 MiB e 8 MP na foto do EPI, 32 MP no OCR e
no worker (`Image.MAX_IMAGE_PIXELS`), timeout de 100 s e subprocesso isolado na
pré-visualização. A orientação EXIF continua aplicada e os metadados continuam
removidos.

O cadastro da foto do EPI continua aceitando os mesmos tipos de data URL
(regra de XSS em `modules/commercial/service.py`), porque o servidor não
decodifica esses valores no cadastro. Quem decodifica é `render_epi_photo`,
que agora recusa qualquer conteúdo que não seja PNG ou JPEG real.

## Testes

`tests/test_pillow_image_hardening.py`, com 95 casos:

- TIFF, GIF, BMP, WEBP, ICO e PDF disfarçados de PNG ou JPEG são recusados nos
  três pontos;
- assinatura PNG ou JPEG seguida de corpo de outro formato é recusada;
- PNG e JPEG reais continuam funcionando, inclusive com rotação EXIF;
- os limites de pixels e de tamanho continuam valendo;
- não resta `Image.open` sem `formats=` em `modules/`, `epi_backend/` e `core/`;
- a restrição de dependência e a versão instalada são Pillow 13 ou superior.

## Rollback

Reverter o PR. Nenhuma migração, nenhum dado e nenhuma configuração mudam.
Os dados atuais de foto de EPI (todos JPEG com assinatura válida, conferido em
17/11/2026) continuam sendo exibidos.
