# Formulários de dados das lojas — Data Safety (Google) & App Privacy (Apple)

> Respostas prontas para transcrever nos consoles. Base: matriz de dados da
> `docs/AUDITORIA_PUBLICACAO_MOBILE.md` §6. **Localização: NÃO coletada** (removida no M0).

## A) Google Play — Data Safety

**Coleta dados?** Sim. **Compartilha com terceiros?** Não (apenas processadores sob contrato).
**Criptografia em trânsito?** Sim (HTTPS). **Usuário pode pedir exclusão?** Sim (via suporte).

| Categoria | Tipo | Coletado | Compart. | Finalidade | Opcional? |
|---|---|---|---|---|---|
| Informações pessoais | Nome | Sim | Não | Funcionalidade | Não |
| Informações pessoais | CPF (outro ID) | Sim | Não | Funcionalidade | Não |
| Fotos e vídeos | Fotos | Sim | Não | Funcionalidade | Sim (só ao anexar) |
| Identificadores | ID de usuário | Sim | Não | Funcionalidade / segurança | Não |
| Identificadores | ID do dispositivo (push token) | Sim | Não | Funcionalidade (notificações) | Não |
| Atividade no app | Ações no app (entregas/estoque) | Sim | Não | Funcionalidade | Não |
| Info do app/desempenho | Logs/diagnóstico | Sim | Não | Diagnóstico | Não |

> **Não declarar Localização** (foi removida). Câmera/biometria são **permissões**, não "dados
> coletados" no Data Safety.

## B) Apple — App Privacy (Nutrition Label)

**Tracking?** Não (`NSPrivacyTracking=false`). **Dados vinculados ao usuário:** sim.

| Tipo de dado | Vinculado? | Tracking? | Finalidade |
|---|---|---|---|
| Name | Sim | Não | App Functionality |
| Sensitive Info (CPF) | Sim | Não | App Functionality |
| Photos or Videos | Sim | Não | App Functionality |
| User ID | Sim | Não | App Functionality |
| Device ID | Sim | Não | App Functionality |
| Product Interaction | Sim | Não | App Functionality |
| Crash/Performance Data | Não | Não | App Functionality |

> Reflete o `ios/Runner/PrivacyInfo.xcprivacy` (M1). Manter os dois **consistentes**.

## C) Classificação indicativa (IARC)
Questionário: sem violência/conteúdo adulto/jogos de azar → tende a **Livre / 4+**. Responder o
questionário em cada console (gera o rating IARC).

## D) Checklist de submissão dos formulários
- [ ] Play Data Safety preenchido conforme (A) e publicado.
- [ ] Apple App Privacy preenchido conforme (B).
- [ ] `PrivacyInfo.xcprivacy` consistente com (B).
- [ ] Questionário IARC respondido (Play) e Age Rating (Apple).
- [ ] URL da Política de Privacidade informada nos dois consoles.
