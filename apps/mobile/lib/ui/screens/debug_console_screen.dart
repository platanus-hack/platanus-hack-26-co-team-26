import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../app/feature_flags.dart';
import '../../app/mesh_controller.dart';
import '../../core/logging.dart';

/// Consola de depuración y panel de flags.
///
/// Todo log lleva bundle_id: con tres teléfonos sobre la mesa, un bug que no
/// se puede rastrear por bundle_id no se puede depurar en vivo.
class DebugConsoleScreen extends StatefulWidget {
  const DebugConsoleScreen({super.key});
  @override
  State<DebugConsoleScreen> createState() => _DebugConsoleScreenState();
}

class _DebugConsoleScreenState extends State<DebugConsoleScreen> {
  void _tick() => setState(() {});

  @override
  void initState() {
    super.initState();
    log.listeners.add(_tick);
  }

  @override
  void dispose() {
    log.listeners.remove(_tick);
    super.dispose();
  }

  static const _colors = {
    LogLevel.d: Colors.grey, LogLevel.i: Colors.lightBlueAccent,
    LogLevel.w: Colors.orange, LogLevel.e: Colors.redAccent,
  };

  @override
  Widget build(BuildContext context) {
    final c = context.read<MeshController>();
    final lines = log.ring.toList().reversed.toList();
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Depuración'),
          bottom: const TabBar(tabs: [Tab(text: 'LOG'), Tab(text: 'FLAGS')]),
          actions: [
            IconButton(
              icon: const Icon(Icons.delete_sweep),
              tooltip: 'Reset del demo',
              onPressed: () async {
                await c.resetDemo();
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Store y log vaciados')));
                }
              },
            ),
          ],
        ),
        body: TabBarView(children: [
          ListView.builder(
            itemCount: lines.length,
            itemBuilder: (_, i) => Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
              child: Text(
                '${lines[i].at.toIso8601String().substring(11, 19)}  ${lines[i].message}',
                style: TextStyle(
                    fontFamily: 'monospace', fontSize: 11,
                    color: _colors[lines[i].level]),
              ),
            ),
          ),
          ListView(
            children: FeatureFlags.all.entries.map((e) => SwitchListTile(
                  dense: true,
                  title: Text(e.key, style: const TextStyle(fontFamily: 'monospace', fontSize: 13)),
                  value: e.value,
                  onChanged: (v) => setState(() => FeatureFlags.set(e.key, v)),
                )).toList(),
          ),
        ]),
      ),
    );
  }
}
