/// El rol es estado de runtime, no un flavor de build: cualquier teléfono
/// puede cambiar de rol durante el demo. Eso es parte del argumento — la malla
/// no depende de hardware dedicado.
enum NodeRole {
  victim('Víctima', 'Genera reportes y los emite a quien pase cerca'),
  relay('Relay', 'Transporta reportes ajenos sin leerlos'),
  gateway('Gateway', 'Recolecta y sube a la nube cuando hay Internet');

  const NodeRole(this.label, this.description);
  final String label, description;
}
