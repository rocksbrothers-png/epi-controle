"""Public supplier portal shell; presentation JS uses the central i18n engine.

The existing token routes remain the sole authority for supplier data/actions."""

PORTAL_PAGE_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title data-i18n="supplierPortal.pageTitle">Portal do Fornecedor — EPI Controle</title>
<style>
  :root { --azul: #1c4e80; --cinza: #f4f6f8; --borda: #d7dde3; --ok: #1e7d46; --erro: #b3261e; }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; }
  body { background: var(--cinza); color: #1e2833; padding: 16px; }
  .card { max-width: 760px; margin: 0 auto 16px; background: #fff; border: 1px solid var(--borda); border-radius: 10px; padding: 20px; }
  h1 { font-size: 1.25rem; color: var(--azul); margin-bottom: 4px; }
  h2 { font-size: 1rem; margin: 16px 0 8px; }
  .muted { color: #5b6875; font-size: .85rem; }
  table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: .9rem; }
  th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--borda); vertical-align: middle; }
  th { color: #40505f; font-weight: 600; font-size: .8rem; text-transform: uppercase; }
  input, select, textarea { width: 100%; padding: 8px; border: 1px solid var(--borda); border-radius: 6px; font-size: .9rem; }
  input[type="checkbox"] { width: auto; }
  .row { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 8px; }
  .row > div { flex: 1 1 160px; }
  label { display: block; font-size: .8rem; color: #40505f; margin-bottom: 4px; }
  button { background: var(--azul); color: #fff; border: 0; border-radius: 8px; padding: 12px 20px; font-size: 1rem; cursor: pointer; margin-top: 16px; }
  button:disabled { opacity: .5; cursor: default; }
  .msg { margin-top: 12px; padding: 10px 12px; border-radius: 8px; display: none; font-size: .9rem; }
  .msg.ok { display: block; background: #e6f4ec; color: var(--ok); }
  .msg.erro { display: block; background: #fdeceb; color: var(--erro); }
  .file-picker { margin: 0; padding: 8px 12px; font-size: .85rem; }
  #proposal-name { font-size: .85rem; overflow-wrap: anywhere; }
  td input[type="number"] { min-width: 110px; }
  .table-scroll { overflow-x: auto; }
  #portal-language { width: auto; margin: 8px 0; max-width: 100%; }
  .tag { display: inline-block; background: #e8eef5; color: var(--azul); border-radius: 999px; padding: 2px 10px; font-size: .75rem; margin-left: 6px; }
  @media (max-width: 560px) { .esconde-mobile { display: none; } td, th { padding: 6px 4px; } }
</style>
</head>
<body>
<div class="card" id="cabecalho">
  <h1 data-i18n="supplierPortal.title">Portal do Fornecedor</h1>
  <label for="portal-language" data-i18n="login.selectLanguage">Idioma</label>
  <select id="portal-language"><option value="pt-BR">Português</option><option value="en-GB">English</option><option value="es-ES">Español</option><option value="fr-FR">Français</option><option value="nb-NO">Norsk</option></select>
  <p class="muted" id="locale-error" role="status" hidden></p>
  <p class="muted" data-i18n="loading" id="subtitulo">Carregando…</p>
</div>
<div class="card" id="conteudo" style="display:none"></div>
<div class="card" id="painel-erro" style="display:none">
  <p class="msg erro" style="display:block" id="texto-erro"></p>
</div>
<script src="/i18n.js"></script>
<script src="/js/modules/purchases/integrations/supplier-portal-api.js"></script>
<script src="/js/views/supplier-portal.js"></script>

</body>
</html>
"""
