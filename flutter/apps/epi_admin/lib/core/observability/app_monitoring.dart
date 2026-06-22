/// Telemetria leve de erros/instabilidade por tela e API, com limites (caps)
/// para não crescer indefinidamente. Paridade com o `__EPI_MONITORING__` do
/// frontend legado (caps 50/50/100). Pura — sem platform channels, testável.
class AppMonitoring {
  AppMonitoring._();
  static final AppMonitoring instance = AppMonitoring._();

  static const int maxModules = 50;
  static const int maxApis = 50;
  static const int maxCritical = 100;

  final Map<String, int> _errorsByModule = {};
  final Map<String, int> _unstableApis = {};
  final List<MonitoringEvent> _criticalFailures = [];

  /// Conta um erro atribuído a uma tela/módulo. Novos módulos são ignorados
  /// após atingir [maxModules]; módulos já registrados seguem incrementando.
  void recordError(String module) {
    if (!_errorsByModule.containsKey(module) &&
        _errorsByModule.length >= maxModules) {
      return;
    }
    _errorsByModule[module] = (_errorsByModule[module] ?? 0) + 1;
  }

  /// Registra o resultado de uma chamada de API. Respostas de sucesso
  /// (2xx/3xx) são ignoradas; 4xx/5xx e falhas de rede (status 0) contam como
  /// instabilidade, agrupadas por `endpoint:status`.
  void recordApiResult(String endpoint, int status) {
    if (status >= 200 && status < 400) return;
    final key = '$endpoint:$status';
    if (!_unstableApis.containsKey(key) && _unstableApis.length >= maxApis) {
      return;
    }
    _unstableApis[key] = (_unstableApis[key] ?? 0) + 1;
  }

  /// Buffer FIFO de falhas críticas (cap [maxCritical]).
  void recordCritical(String message, {String? module}) {
    _criticalFailures.add(
      MonitoringEvent(message: message, module: module, at: DateTime.now()),
    );
    if (_criticalFailures.length > maxCritical) {
      _criticalFailures.removeAt(0);
    }
  }

  MonitoringSnapshot snapshot() => MonitoringSnapshot(
        errorsByModule: Map.unmodifiable(_errorsByModule),
        unstableApis: Map.unmodifiable(_unstableApis),
        criticalFailures: List.unmodifiable(_criticalFailures),
      );

  void reset() {
    _errorsByModule.clear();
    _unstableApis.clear();
    _criticalFailures.clear();
  }
}

class MonitoringEvent {
  const MonitoringEvent({required this.message, this.module, required this.at});
  final String message;
  final String? module;
  final DateTime at;
}

class MonitoringSnapshot {
  const MonitoringSnapshot({
    required this.errorsByModule,
    required this.unstableApis,
    required this.criticalFailures,
  });

  final Map<String, int> errorsByModule;
  final Map<String, int> unstableApis;
  final List<MonitoringEvent> criticalFailures;

  int get totalErrors => errorsByModule.values.fold(0, (s, v) => s + v);
  int get unstableApiCount => unstableApis.length;
  int get criticalCount => criticalFailures.length;
}
