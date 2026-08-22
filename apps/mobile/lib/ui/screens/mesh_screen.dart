import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../app/mesh_controller.dart';
import '../../transport/transport_adapter.dart';

/// Vista de la malla: peers y bundles almacenados.
///
/// Muestra explícitamente procedencia, saltos e integridad — el playbook exige
/// que bundle_id, seq, prioridad y provenance sean visibles en modo debug.
class MeshScreen extends StatelessWidget {
  const MeshScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final c = context.watch<MeshController>();
    return Scaffold(
      appBar: AppBar(title: const Text('Malla')),
      body: ListView(children: [
        const _Header('PEERS'),
        if (c.peers.isEmpty)
          const ListTile(dense: true, title: Text('Ninguno a la vista',
              style: TextStyle(fontStyle: FontStyle.italic, color: Colors.grey))),
        ...c.peers.values.map((p) => ListTile(
              dense: true,
              leading: Icon(
                p.state == PeerState.connected ? Icons.link : Icons.link_off,
                color: p.state == PeerState.connected ? Colors.green : Colors.grey,
              ),
              title: Text(p.name ?? p.peerId,
                  style: const TextStyle(fontFamily: 'monospace')),
              subtitle: Text(p.state.name),
              trailing: p.rssi == null ? null : Text('${p.rssi} dBm'),
            )),
        const _Header('BUNDLES ALMACENADOS'),
        ...c.bundles.map((s) {
          final b = s.bundle;
          final mine = b.payload.nodePseudonym == c.identity.pseudonym;
          return ListTile(
            dense: true,
            leading: Icon(
              s.verified ? Icons.verified : Icons.gpp_bad,
              color: s.verified ? Colors.green : Colors.red,
            ),
            title: Text('${b.payload.status.wire} · seq ${b.payload.seq}'
                '${mine ? " (propio)" : ""}'),
            subtitle: Text(
              '${b.bundleId.substring(b.bundleId.length - 12)} · '
              'hop ${b.relay.hopCount} · ${b.relay.transport ?? "local"}'
              '${s.rejectReason != null ? "\n${s.rejectReason}" : ""}',
              style: const TextStyle(fontFamily: 'monospace', fontSize: 11),
            ),
            trailing: Icon(s.uploaded ? Icons.cloud_done : Icons.cloud_queue,
                size: 18, color: s.uploaded ? Colors.green : Colors.grey),
          );
        }),
      ]),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 20, 16, 8),
        child: Text(text, style: const TextStyle(fontSize: 12, letterSpacing: 1.2)),
      );
}
