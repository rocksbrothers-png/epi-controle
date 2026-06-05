/// Breakpoints oficiais do EPI Controle.
/// Ponto único de verdade — todos os layouts devem usar estas constantes.
abstract final class EpiBreakpoints {
  /// Limite superior do layout mobile (< 600 px).
  static const double tablet  = 600;

  /// Limite inferior do layout desktop com sidebar (>= 768 px).
  static const double desktop = 768;

  /// Layout wide — sidebar expandida por padrão (>= 1200 px).
  static const double wide    = 1200;

  static bool isMobile(double width)  => width < tablet;
  static bool isTablet(double width)  => width >= tablet && width < desktop;
  static bool isDesktop(double width) => width >= desktop && width < wide;
  static bool isWide(double width)    => width >= wide;
}
