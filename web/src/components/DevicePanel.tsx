import { evidenceLabel, freshnessAt, type EmergencyDevice } from '../domain/geo';
import { CloseIcon, SignalIcon } from './icons';
export function DevicePanel({ device, onClose }: { device: EmergencyDevice | null; onClose: () => void }) {
  if (!device) return <aside className="evidence empty-evidence"><SignalIcon/><h2>Evidence</h2><p>Select a device to inspect its authorized operational evidence.</p></aside>;
  const freshness=freshnessAt(device.observedAt);
  return <aside className="evidence" aria-label={`Evidence for ${device.label}`}>
    <div className="panel-heading"><div><span className={`status-dot ${freshness.toLowerCase()}`} /> <span>{freshness}</span><h2>{device.label}</h2></div><button className="icon-button" onClick={onClose} aria-label="Close evidence panel"><CloseIcon/></button></div>
    {device.sos && <div className="critical-banner">SOS packet received</div>}
    <dl className="evidence-grid">
      <div><dt>Evidence</dt><dd>{evidenceLabel[device.evidenceType]}</dd></div>
      <div><dt>Accuracy</dt><dd>±{device.accuracyMeters} m</dd></div>
      <div><dt>Coordinates</dt><dd className="mono">{device.coordinates[1].toFixed(5)}, {device.coordinates[0].toFixed(5)}</dd></div>
      <div><dt>Battery</dt><dd>{device.batteryPercent}%</dd></div>
      <div><dt>Movement</dt><dd>{device.motionState === 'STATIONARY' ? 'No recent device movement' : 'Recent device movement detected'}</dd></div>
      <div><dt>Network</dt><dd>{device.network.replace('_',' ')} · {device.relayHops} hops</dd></div>
    </dl>
    <div className="microchart" role="img" aria-label={`GPS accuracy currently plus or minus ${device.accuracyMeters} meters`}><span style={{height:'32%'}}/><span style={{height:'55%'}}/><span style={{height:'42%'}}/><span style={{height:`${Math.min(90,device.accuracyMeters)}%`}}/><span style={{height:'36%'}}/><span style={{height:'48%'}}/></div>
    <p className="clinical-note">Movement and physiological signals are evidence only. They are not proof of life or a clinical diagnosis.</p>
  </aside>;
}
