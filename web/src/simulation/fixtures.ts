import type { EmergencyDevice, RescueUnit, SearchArea } from '../domain/geo';

const center: [number, number] = [-74.0721, 4.7110];
const now = Date.now();
const evidence = ['CURRENT_GPS', 'CURRENT_GPS', 'LAST_KNOWN', 'HISTORICAL_ESTIMATE', 'RELAY_OBSERVATION'] as const;

export const simulatedDevices: EmergencyDevice[] = Array.from({ length: 24 }, (_, index) => {
  const angle = index * 1.71;
  const radius = 0.004 + (index % 7) * 0.0017;
  return {
    id: `node-${String(index + 1).padStart(2, '0')}`,
    label: `Device ${String(index + 1).padStart(2, '0')}`,
    coordinates: [center[0] + Math.cos(angle) * radius, center[1] + Math.sin(angle) * radius],
    evidenceType: evidence[index % evidence.length],
    observedAt: now - [12_000, 54_000, 7 * 60_000, 34 * 60_000][index % 4],
    accuracyMeters: 7 + (index * 11) % 68,
    batteryPercent: 9 + (index * 17) % 88,
    motionState: index % 6 === 0 ? 'RAPID_MOVEMENT' : index % 3 === 0 ? 'MOVING' : 'STATIONARY',
    motionConfidence: 0.45 + (index % 5) * 0.1,
    sos: index === 2 || index === 13,
    relayHops: index % 4,
    network: index % 3 === 0 ? 'BLE_RELAY' : index % 3 === 1 ? 'WIFI_AWARE' : 'INTERNET',
  };
});

export const rescueUnits: RescueUnit[] = [
  { id: 'rescue-1', label: 'Brigade North', coordinates: [-74.078, 4.719], status: 'ASSIGNED' },
  { id: 'rescue-2', label: 'Medical Alpha', coordinates: [-74.064, 4.706], status: 'AVAILABLE' },
  { id: 'rescue-3', label: 'USAR 04', coordinates: [-74.073, 4.699], status: 'ASSIGNED' },
];

export const searchAreas: SearchArea[] = [
  { id: 'area-1', label: 'Sector A', priority: 'HIGH', coordinates: [[[-74.081,4.714],[-74.075,4.722],[-74.068,4.717],[-74.071,4.710],[-74.081,4.714]]] },
  { id: 'area-2', label: 'Sector B', priority: 'MEDIUM', coordinates: [[[-74.070,4.707],[-74.062,4.711],[-74.060,4.701],[-74.068,4.698],[-74.070,4.707]]] },
];
