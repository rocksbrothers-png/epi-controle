# Plano de integração I18N-FULL-V1 → UBX (Comercial)

Status: **plano; nada foi integrado.** Os PRs UBX não foram alterados.

| | Corporate | SaaS |
|---|---|---|
| I18N | rocksbrothers-png/epi-controle#1080 `2bc847cce3559009b5b1e5b655ff08ecc6f66694` | rocksbrothers-png/epi-controle-app#454 `c40869fe0eaf07819e1db1b9876740dd41f2462a` |
| UBX | rocksbrothers-png/epi-controle#1079 `b54fd58aeef1338d7d2c57b9da0e209aff61ae2c` | rocksbrothers-png/epi-controle-app#453 `3336acca5e6ae3f20127eee9c8260cf3218bae18` |
| `main` (base de ambos) | `5c6d13fdfcee81743c946764dec8c9f5e0890077` | `7664c5713ac2c53c0a35c5595b80fd82896e3618` |

## Simulação feita (worktree temporária, sem push)

Em cada repositório: `main` + merge da I18N, depois merge do PR UBX.

**Resultado nos dois produtos:**
1. I18N sobre a `main`: merge **limpo**.
2. UBX sobre a I18N: conflitos em **3 arquivos**:
   - `static/index.html`, que é gerado e foi regenerado com `python scripts/build_index.py build`;
   - `tests/test_343_f4_portal_cpf_sem_cache.py` (`DIGESTO_PARIDADE_F4`);
   - `tests/test_343_f5b_navegacao_estado_inicial.py` (`DIGESTO_PARIDADE_F5B`).
3. `static/app.js` mesclou **sem conflito**.
4. Os digests recalculados sobre o conjunto combinado saem **iguais nos dois produtos**:
   - F4 `e11440f04ffc…`
   - F5B `746530220c8a…`

   O valor de F5B só fica certo depois de recalculado: herdar o do PR UBX reprova `test_g11_paridade_f5b`, ou seja, o conflito não é só textual.
5. Verificação semântica no combinado:

| Verificação | Corporate | SaaS |
|---|---|---|
| Guarda UBX | 725 declarações (−2 pela extração do logo), 104 endpoints, 0 ciclos | idem |
| JS | 670 | 670 |
| pytest | 4.956 aprovados, 49 pulados, 0 falhas | 4.854 aprovados, 45 pulados, 2 falhas |
| Chromium I18N (7 cenários × 5 idiomas) | 35/35 | 35/35 |

As 2 falhas do SaaS são de ambiente: PyMuPDF 2.1 no container e o teste de tempo, que passa isolado.

Funções sobrepostas: `formatCompanyCurrency`, `updateTopbarCompanyBadge` e `renderMyCompanyDomains`. A I18N traduz essas funções e a UBX extrai apenas `companyLogoMarkup`/`companyLogoSrc`, que a I18N não tocou. A I18N também não tocou `static/tenant-init.js` nem `static/views/_scripts.html`, que a UBX altera.

## Sequência por repositório (cada passo depende de autorização onde indicado)

1. **[autorização]** Merge do PR I18N (#1080 no Corporate, #454 no SaaS) na `main`.
2. Validar a `main`: CI completo verde. Pulados não contam como aprovados; hoje são 4 jobs Android/Flutter Web nos dois.
3. **[autorização para tocar o PR UBX]** Atualizar o PR UBX com a nova `main`, por merge e sem force-push.
4. Regenerar `static/index.html` (`python scripts/build_index.py build`).
5. Recalcular `DIGESTO_PARIDADE_F4` e `DIGESTO_PARIDADE_F5B` **nos dois produtos, no mesmo conteúdo**. Conferir que os valores dos dois repositórios coincidem.
6. Rodar de novo:
   - `node static/js/test/run-tests.js`
   - `node static/js/test/app-js-boundary.js` (esperado: 725 declarações)
   - `node static/js/test/security-logo-xss-runtime.js`
   - `pytest tests`
   - `python scripts/browser/i18n_commercial.py`
7. Auditoria independente da UBX sobre o resultado.
8. **[autorização]** Integrar a UBX.

Corporate e SaaS seguem a mesma sequência de forma independente. Nenhum passo de um depende do merge no outro, mas os digests de paridade precisam acabar iguais nos dois.

**Ordem relativa ao PR de segurança** (rocksbrothers-png/epi-controle#1081 / rocksbrothers-png/epi-controle-app#455): ele também altera `DIGESTO_PARIDADE_F4`, porque `epi_backend/http_utils.py` é pareado. Quem entrar depois recalcula o F4. O PR de segurança não toca nenhum arquivo da I18N nem da UBX além desse digest.
