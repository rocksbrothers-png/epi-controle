import 'package:connectivity_plus/connectivity_plus.dart';

/// Verificação de conectividade — abstrai o `connectivity_plus` para permitir
/// testar os caminhos online/offline dos cubits sem platform channels.
abstract class ConnectivityChecker {
  Future<bool> get isOnline;
}

/// Implementação real baseada no `connectivity_plus`.
class RealConnectivityChecker implements ConnectivityChecker {
  const RealConnectivityChecker();

  @override
  Future<bool> get isOnline async {
    final results = await Connectivity().checkConnectivity();
    return !results.contains(ConnectivityResult.none);
  }
}
