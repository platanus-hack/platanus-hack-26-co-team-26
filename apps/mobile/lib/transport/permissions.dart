import 'package:permission_handler/permission_handler.dart';

/// Preflight de permisos.
///
/// Es la causa #1 de "no aparece ningún peer": Nearby falla SIN excepción y
/// SIN log cuando falta un permiso. Por eso se piden todos juntos antes de
/// armar el incidente y se muestra el estado de cada uno.
class MeshPermissions {
  static const required = <Permission>[
    Permission.bluetoothScan,
    Permission.bluetoothAdvertise,
    Permission.bluetoothConnect,
    Permission.location,
    Permission.nearbyWifiDevices,
    Permission.notification,
  ];

  static Future<Map<Permission, PermissionStatus>> check() async {
    final out = <Permission, PermissionStatus>{};
    for (final p in required) {
      out[p] = await p.status;
    }
    return out;
  }

  static Future<Map<Permission, PermissionStatus>> request() => required.request();

  static String label(Permission p) => switch (p) {
        Permission.bluetoothScan => 'Buscar dispositivos Bluetooth',
        Permission.bluetoothAdvertise => 'Anunciarse por Bluetooth',
        Permission.bluetoothConnect => 'Conectar por Bluetooth',
        Permission.location => 'Ubicación',
        Permission.nearbyWifiDevices => 'Dispositivos Wi-Fi cercanos',
        Permission.notification => 'Notificaciones (servicio en primer plano)',
        _ => p.toString(),
      };
}
