export type EvidenceType = 'CURRENT_GPS' | 'LAST_KNOWN' | 'HISTORICAL_ESTIMATE' | 'RELAY_OBSERVATION';
export type Freshness = 'LIVE' | 'RECENT' | 'AGING' | 'STALE';
export type MotionState = 'UNKNOWN' | 'STATIONARY' | 'MOVING' | 'RAPID_MOVEMENT';

export interface EmergencyDevice {
  id: string;
  label: string;
  coordinates: [number, number];
  evidenceType: EvidenceType;
  observedAt: number;
  accuracyMeters: number;
  batteryPercent: number;
  motionState: MotionState;
  motionConfidence?: number;
  sos: boolean;
  relayHops: number;
  network: 'INTERNET' | 'BLE_RELAY' | 'WIFI_AWARE';
}

export interface RescueUnit { id: string; label: string; coordinates: [number, number]; status: 'AVAILABLE' | 'ASSIGNED'; }
export interface SearchArea { id: string; label: string; priority: 'HIGH' | 'MEDIUM'; coordinates: [number, number][][]; }

export const freshnessAt = (timestamp: number, now = Date.now()): Freshness => {
  const age = Math.max(0, now - timestamp);
  if (age <= 30_000) return 'LIVE';
  if (age <= 120_000) return 'RECENT';
  if (age <= 1_800_000) return 'AGING';
  return 'STALE';
};

export const evidenceLabel: Record<EvidenceType, string> = {
  CURRENT_GPS: 'GPS actual', LAST_KNOWN: 'Última ubicación',
  HISTORICAL_ESTIMATE: 'Estimación histórica', RELAY_OBSERVATION: 'Observación retransmitida',
};
