# Parecer linguístico parcial — Feedback17

Foram revistos os 17 recursos propostos em cinco idiomas, somente como texto. A duplicação de Ended/Closed em inglês e espanhol foi identificada pelo auditor e corrigida pelo root: Concluded/Closed e Finalizado/Cerrado. FR Clôturé/Fermé e NO Avsluttet/Lukket já são distintos. NotApproved permanece separado de Rejected; Gestor de EPI/HSEQ e a sequência de revisão/aprovação mantêm o significado da fonte.

Não foi confirmada outra troca material de significado. Sugestão pontual NO: Åpent korrigerende tiltak tem ordem mais natural para ação corretiva aberta. Recomendações e fontes em FLUTTER_LINGUISTIC_REVIEW_PARTIAL.json.

Este parecer cobre as mensagens do TSV, não lógica, filtros, ações, cores, integrações, delegates gerados ou runtime de FeedbackScreen. Nenhum gerador ou arquivo de produto foi alterado pelo auditor.

Atualização de fonte: o root aplicou `Åpent korrigerende tiltak`; as nove recomendações deste conjunto foram conferidas nos regionais, aliases e getters gerados. Nenhum SDK foi executado para esta atualização. A ressalva de datas foi resolvida pelo helper dedicado com DateTime.parse; ver FLUTTER_FEEDBACK_STATIC_AUDIT.md. FeedbackScreen continua sem certificação independente de runtime.
