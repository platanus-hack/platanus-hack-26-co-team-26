import { useMemo, useState } from 'react';
import { DevicePanel } from './components/DevicePanel';
import { LayersIcon, SignalIcon, TargetIcon } from './components/icons';
import { MapCanvas } from './components/MapCanvas';
import { freshnessAt } from './domain/geo';
import { rescueUnits, searchAreas, simulatedDevices } from './simulation/fixtures';

export function App() {
  const [selectedId,setSelectedId]=useState<string|null>('node-03');
  const [is3d,setIs3d]=useState(false);
  const [visible,setVisible]=useState({devices:true,rescue:true,areas:true});
  const [timeOffset,setTimeOffset]=useState(0);
  const selected=useMemo(()=>simulatedDevices.find(d=>d.id===selectedId)??null,[selectedId]);
  const live=simulatedDevices.filter(d=>freshnessAt(d.observedAt)==='LIVE').length;
  return <main className="app-shell">
    <header className="topbar"><div className="brand"><span className="brand-mark"><SignalIcon/></span><div><strong>SismoMesh</strong><span>Emergency location intelligence</span></div></div><div className="incident"><span className="live-indicator"/>SIMULATION · Bogotá Central</div><div className="connectivity">Realtime connected <span className="role">RESPONDER</span></div></header>
    <section className="workspace">
      <aside className="layers"><div className="section-title"><LayersIcon/><div><h1>Incident layers</h1><span>24 devices · 3 units</span></div></div>
        <fieldset><legend>Operational evidence</legend>{([['devices','Emergency devices'],['rescue','Rescue units'],['areas','Search areas']] as const).map(([key,label])=><label className="layer-row" key={key}><input type="checkbox" checked={visible[key]} onChange={()=>setVisible(v=>({...v,[key]:!v[key]}))}/><span>{label}</span><b>{key==='devices'?24:key==='rescue'?3:2}</b></label>)}</fieldset>
        <div className="summary"><span>Live nodes<strong>{live}</strong></span><span>SOS active<strong className="critical-text">2</strong></span><span>Stale packets<strong>6</strong></span></div>
        <div className="privacy-note"><TargetIcon/><div><strong>Authorized view</strong><p>Exact coordinates are limited to response personnel. Public views receive aggregates only.</p></div></div>
      </aside>
      <section className="map-region"><MapCanvas devices={simulatedDevices} units={rescueUnits} areas={searchAreas} is3d={is3d} visible={visible} onSelect={setSelectedId}/><div className="map-mode" aria-label="Map perspective"><button className={!is3d?'active':''} onClick={()=>setIs3d(false)}>2D</button><button className={is3d?'active':''} onClick={()=>setIs3d(true)}>3D</button></div><div className="map-legend"><span><i className="gps"/>Current GPS</span><span><i className="last"/>Last known</span><span><i className="estimate"/>Historical estimate</span><span><i className="sos"/>SOS</span></div></section>
      <DevicePanel device={selected} onClose={()=>setSelectedId(null)}/>
    </section>
    <footer className="timeline"><div><strong>Incident timeline</strong><span>{timeOffset===0?'Live':`${timeOffset} min ago`}</span></div><input aria-label="Inspect incident timeline" type="range" min="-120" max="0" value={timeOffset} onChange={e=>setTimeOffset(Number(e.target.value))}/><time>20:42:16 COT</time></footer>
  </main>;
}
