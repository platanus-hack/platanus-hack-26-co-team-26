import { evidenceLabel, freshnessAt, type EmergencyDevice } from '../domain/geo';
import { CloseIcon, SignalIcon } from './icons';
export function DevicePanel({ device, onClose }: { device: EmergencyDevice | null; onClose: () => void }) {
  if (!device) return <aside className="evidence empty-evidence"><SignalIcon/><h2>Evidencia</h2><p>Selecciona un dispositivo para consultar su evidencia operativa autorizada.</p></aside>;
  const freshness=freshnessAt(device.observedAt);
  return <aside className="evidence" aria-label={`Evidencia de ${device.label}`}>
    <div className="panel-heading"><div><span className={`status-dot ${freshness.toLowerCase()}`} /> <span>{freshness === 'LIVE' ? 'EN VIVO' : freshness === 'RECENT' ? 'RECIENTE' : freshness === 'AGING' ? 'ENVEJECIENDO' : 'ANTIGUA'}</span><h2>{device.label}</h2></div><button className="icon-button" onClick={onClose} aria-label="Cerrar panel de evidencia"><CloseIcon/></button></div>
    {device.sos && <div className="critical-banner">Paquete SOS recibido</div>}
    <dl className="evidence-grid">
      <div><dt>Evidencia</dt><dd>{evidenceLabel[device.evidenceType]}</dd></div>
      <div><dt>Precisión</dt><dd>±{device.accuracyMeters} m</dd></div>
      <div><dt>Coordenadas</dt><dd className="mono">{device.coordinates[1].toFixed(5)}, {device.coordinates[0].toFixed(5)}</dd></div>
      <div><dt>Batería</dt><dd>{device.batteryPercent}%</dd></div>
      <div><dt>Movimiento</dt><dd>{device.motionState === 'STATIONARY' ? 'Sin movimiento reciente' : 'Movimiento reciente detectado'}</dd></div>
      <div><dt>Red</dt><dd>{device.network.replace('_',' ')} · {device.relayHops} saltos</dd></div>
    </dl>
    <div className="microchart" role="img" aria-label={`GPS accuracy currently plus or minus ${device.accuracyMeters} meters`}><span style={{height:'32%'}}/><span style={{height:'55%'}}/><span style={{height:'42%'}}/><span style={{height:`${Math.min(90,device.accuracyMeters)}%`}}/><span style={{height:'36%'}}/><span style={{height:'48%'}}/></div>
    <p className="clinical-note">El movimiento y las señales fisiológicas son solo evidencia. No prueban vida ni constituyen un diagnóstico clínico.</p>
  </aside>;
}
