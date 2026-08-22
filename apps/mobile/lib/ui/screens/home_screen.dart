import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../app/mesh_controller.dart';
import '../../app/node_role.dart';
import '../../protocol/status.dart';
import 'debug_console_screen.dart';
import 'mesh_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final c = context.watch<MeshController>();
    return Scaffold(
      appBar: AppBar(
        title: Text('SismoMesh · ${c.identity.pseudonym}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.terminal),
            tooltip: 'Consola de depuración',
            onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const DebugConsoleScreen())),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text('ROL DE ESTE TELÉFONO',
              style: TextStyle(fontSize: 12, letterSpacing: 1.2)),
          const SizedBox(height: 8),
          SegmentedButton<NodeRole>(
            segments: NodeRole.values
                .map((r) => ButtonSegment(value: r, label: Text(r.label)))
                .toList(),
            selected: {c.role},
            onSelectionChanged: (s) => c.setRole(s.first),
          ),
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(c.role.description,
                style: Theme.of(context).textTheme.bodySmall),
          ),
          const Divider(height: 32),
          const Text('ESTADO A REPORTAR',
              style: TextStyle(fontSize: 12, letterSpacing: 1.2)),
          const SizedBox(height: 8),
          _StatusButton(NodeStatus.trapped, 'ATRAPADO', Colors.red,
              'No puedo salir por mis medios'),
          _StatusButton(NodeStatus.help, 'NECESITO AYUDA', Colors.orange,
              'Estoy accesible pero requiero asistencia'),
          _StatusButton(NodeStatus.safe, 'ESTOY BIEN', Colors.green,
              'Sin lesiones, no requiero rescate'),
          const Divider(height: 32),
          Card(
            child: Column(children: [
              ListTile(
                leading: const Icon(Icons.hub),
                title: Text('${c.peers.length} peers · ${c.bundles.length} bundles'),
                subtitle: Text('recibidos ${c.receivedCount} · reenviados ${c.forwarded}'
                    '${c.role == NodeRole.gateway ? " · subidos ${c.uploaded}" : ""}'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const MeshScreen())),
              ),
              if (c.uploadError != null)
                ListTile(
                  dense: true,
                  leading: const Icon(Icons.cloud_off, color: Colors.orange),
                  title: Text('En cola: ${c.uploadError}',
                      style: const TextStyle(fontSize: 12)),
                ),
            ]),
          ),
          if (c.emergencyActive)
            Padding(
              padding: const EdgeInsets.only(top: 16),
              child: OutlinedButton.icon(
                onPressed: c.emitReport,
                icon: const Icon(Icons.refresh),
                label: const Text('Emitir nuevo reporte'),
              ),
            ),
        ],
      ),
    );
  }
}

class _StatusButton extends StatelessWidget {
  const _StatusButton(this.status, this.label, this.color, this.help);
  final NodeStatus status;
  final String label, help;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final c = context.watch<MeshController>();
    final active = c.emergencyActive && c.status == status;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: FilledButton(
        style: FilledButton.styleFrom(
          backgroundColor: active ? color : color.withValues(alpha: 0.15),
          foregroundColor: active ? Colors.white : color,
          minimumSize: const Size.fromHeight(64),
        ),
        onPressed: () => c.activateEmergency(status),
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          Text(label, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          Text(help, style: const TextStyle(fontSize: 11)),
        ]),
      ),
    );
  }
}
