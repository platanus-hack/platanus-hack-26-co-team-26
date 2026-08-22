/// Registro central de flags. Todo nace apagado salvo lo que es P0 y está
/// probado en hardware físico. Ver docs/CORE-5H.md §9.
class FeatureFlags {
  static final Map<String, bool> _v = {
    'transport.nearby': true,      // P0: el camino crítico
    'transport.bleGatt': false,    // fallback, fuera del núcleo de 5 h
    'transport.acoustic': false,   // P2
    'signals.ppg': false,          // P1 — el campo del bundle ya existe en null
    'signals.motion': false,       // P1 — idem
    'localization.zone': false,    // P1
    'voice.cachedPack': false,     // P1
    'ai.claudeAnalysis': false,    // P2, nunca en el camino del SOS
    'ranging.uwb': false,          // P2
  };

  static bool on(String k) => _v[k] ?? false;
  static void set(String k, bool v) => _v[k] = v;
  static Map<String, bool> get all => Map.unmodifiable(_v);
}
