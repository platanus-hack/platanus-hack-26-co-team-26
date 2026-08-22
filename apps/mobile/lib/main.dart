import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'app/mesh_controller.dart';
import 'ui/screens/preflight_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const SismoMeshApp());
}

class SismoMeshApp extends StatelessWidget {
  const SismoMeshApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => MeshController(),
      child: MaterialApp(
        title: 'SismoMesh',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          useMaterial3: true,
          colorScheme: ColorScheme.fromSeed(
              seedColor: const Color(0xFFB3261E), brightness: Brightness.dark),
        ),
        home: const PreflightScreen(),
      ),
    );
  }
}
