/// Estado reportado por el nodo.
///
/// No existe DEAD y no debe agregarse nunca. Inferir muerte por ausencia de
/// movimiento es la línea roja del proyecto; que el valor no sea representable
/// en el tipo es más barato que revisarlo en cada PR.
enum NodeStatus {
  safe('SAFE'),
  help('HELP'),
  trapped('TRAPPED'),
  unconfirmed('UNCONFIRMED');

  const NodeStatus(this.wire);
  final String wire;

  static NodeStatus parse(String? s) => NodeStatus.values.firstWhere(
        (e) => e.wire == s,
        orElse: () => NodeStatus.unconfirmed,
      );
}
