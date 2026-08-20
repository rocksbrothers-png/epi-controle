import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';

/// Badge do EPI no **catálogo corporativo** (`epis_screen`, `epi_detail_screen`).
///
/// A criticidade aqui é a da empresa e vem pronta de
/// `is_company_stock_critical` — soma dos saldos das Unidades contra o padrão
/// corporativo, calculada no backend. Não é a criticidade da Unidade, e não
/// deve ser usada em tela operacional: para isso existe [epiUnitBadgeStatus].
///
/// Esta função **não compara saldo com mínimo**. Fazia isso até a fatia
/// 1.1D-C2, através do antigo `Epi.isCriticalStock`, misturando saldo
/// corporativo com um mínimo que hoje é por Unidade.
EpiBadgeStatus epiBadgeStatus(Epi epi) {
  if (epi.stockQuantity == 0) return EpiBadgeStatus.noStock;
  final validade = epiValidityBadgeStatus(epi);
  if (validade != null) return validade;
  return epi.isCompanyStockCritical == true
      ? EpiBadgeStatus.critical
      : EpiBadgeStatus.active;
}

/// Vencimento do CA ou da validade do fabricante, quando houver.
///
/// A validade do fabricante rege a entrega do EPI (NT 146/2015); por isso o
/// status considera os dois e prioriza o caso mais crítico. `null` significa
/// que não há nada a sinalizar sobre validade — é independente de estoque.
EpiBadgeStatus? epiValidityBadgeStatus(Epi epi) {
  final ca = epi.caStatus;
  final fabricante = epi.manufacturerValidityStatus;
  if (ca == 'expired' || fabricante == 'expired') return EpiBadgeStatus.expired;
  if (ca == 'expiring' || fabricante == 'expiring') {
    return EpiBadgeStatus.expiring;
  }
  return null;
}

/// Classificação de estoque **na Unidade**, lida de `stock_status` (#271).
///
/// Só transporta a decisão do servidor. Não recalcula, não infere e não
/// completa lacuna: `null` — inclusive para um `stock_status` desconhecido de
/// um backend mais novo — significa "não há classificação por Unidade neste
/// contexto", que é diferente de `normal`. A tela responde a `null` não
/// desenhando badge, nunca desenhando "normal".
EpiStockStatus? epiUnitBadgeStatus(Epi epi) => switch (epi.stockStatus) {
      'critical' => EpiStockStatus.critical,
      'near_minimum' => EpiStockStatus.nearMinimum,
      'normal' => EpiStockStatus.normal,
      'disabled' => EpiStockStatus.disabled,
      _ => null,
    };

/// Se o EPI está crítico **naquela Unidade**, pela classificação do servidor.
///
/// Falso para `disabled` — inclusive quando `underlyingStatus` é `critical`:
/// contar um EPI com monitoramento desligado desfaria a escolha da Unidade. E
/// falso para `null`, que é ausência de contexto, não ausência de problema.
///
/// Existe para que contadores e ordenações não precisem importar o pacote de
/// design só para comparar com um valor de enum.
bool epiIsUnitCritical(Epi epi) =>
    epiUnitBadgeStatus(epi) == EpiStockStatus.critical;

/// Progresso do saldo da Unidade até sair da faixa de atenção — 0.0 a 1.0.
///
/// A referência é `attention_limit`, o topo da faixa, calculado pelo servidor
/// sobre o mínimo DAQUELA Unidade. Até a fatia 1.1D-C2 a barra usava
/// `minimumStock * 3` — o padrão CORPORATIVO, multiplicado por um número
/// arbitrário: uma Unidade com mínimo 40 aparecia medida contra o 100 da
/// empresa.
///
/// `null` quando não há limite, isto é, quando não há classificação por
/// Unidade. A tela então não desenha barra: uma barra vazia diria "no fim da
/// faixa" e uma cheia diria "com folga".
double? epiUnitStockGauge(Epi epi) {
  final limite = epi.attentionLimit;
  if (limite == null) return null;
  // Limite zero = mínimo zero: não há faixa a percorrer e o EPI está sempre
  // fora dela. Barra cheia, não divisão por zero.
  if (limite <= 0) return 1.0;
  return ((epi.unitStockQuantity ?? 0) / limite).clamp(0.0, 1.0);
}
