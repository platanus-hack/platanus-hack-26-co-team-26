import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:provider/provider.dart';

import '../../app/mesh_controller.dart';
import '../../transport/permissions.dart';
import 'home_screen.dart';

/// Preflight de permisos ANTES de armar el incidente.
///
/// Existe por una razón concreta: Nearby Connections falla en silencio cuando
/// falta un permiso — sin excepción, sin log, simplemente no aparece ningún
/// peer. Descubrirlo en vivo cuesta el demo.
class PreflightScreen extends StatefulWidget {
  const PreflightScreen({super.key});
  @override
  State<PreflightScreen> createState() => _PreflightScreenState();
}

class _PreflightScreenState extends State<PreflightScreen> {
  Map<Permission, PermissionStatus> _status = {};
  bool _initialized = false;

  @override
  void initState() {
    super.initState();
    _boot();
  }

  Future<void> _boot() async {
    await context.read<MeshController>().init();
    final s = await MeshPermissions.check();
    if (mounted) setState(() { _status = s; _initialized = true; });
  }

  Future<void> _request() async {
    final s = await MeshPermissions.request();
    if (mounted) setState(() => _status = s);
  }

  bool get _allGranted =>
      _status.isNotEmpty && _status.values.every((s) => s.isGranted);

  @override
  Widget build(BuildContext context) {
    final ctrl = context.watch<MeshController>();
    if (!_initialized) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return Scaffold(
      appBar: AppBar(title: const Text('Verificación previa')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: ListTile(
              title: const Text('Identidad del nodo'),
              subtitle: Text(ctrl.identity.pseudonym,
                  style: const TextStyle(fontFamily: 'monospace')),
              trailing: const Icon(Icons.verified_user),
            ),
          ),
          Card(
            child: ListTile(
              leading: Icon(ctrl.transportCaps?.supported == true
                  ? Icons.wifi_tethering : Icons.error_outline,
                  color: ctrl.transportCaps?.supported == true
                      ? Colors.green : Colors.orange),
              title: const Text('Transporte de proximidad'),
              subtitle: Text(ctrl.transportCaps?.supported == true
                  ? 'Nearby Connections disponible'
                  : ctrl.transportCaps?.reason ?? 'sin verificar'),
            ),
          ),
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 12),
            child: Text('PERMISOS', style: TextStyle(letterSpacing: 1.2, fontSize: 12)),
          ),
          ..._status.entries.map((e) => ListTile(
                dense: true,
                leading: Icon(e.value.isGranted ? Icons.check_circle : Icons.cancel,
                    color: e.value.isGranted ? Colors.green : Colors.red),
                title: Text(MeshPermissions.label(e.key)),
                subtitle: Text(e.value.name),
              )),
          const SizedBox(height: 16),
          if (!_allGranted)
            FilledButton.icon(
              onPressed: _request,
              icon: const Icon(Icons.lock_open),
              label: const Text('Conceder todos los permisos'),
            ),
          const SizedBox(height: 8),
          FilledButton.tonalIcon(
            // Se permite continuar sin todos los permisos, pero el estado real
            // queda a la vista. Ocultarlo sería fingir capacidad.
            onPressed: () => Navigator.of(context).pushReplacement(
                MaterialPageRoute(builder: (_) => const HomeScreen())),
            icon: const Icon(Icons.arrow_forward),
            label: Text(_allGranted ? 'Continuar' : 'Continuar de todos modos'),
          ),
        ],
      ),
    );
  }
}
