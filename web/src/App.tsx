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
    <header className="topbar"><div className="brand"><span className="brand-mark"><SignalIcon/></span><div><strong>Helios</strong><span>Inteligencia de ubicación para emergencias</span></div></div><div className="incident"><span className="live-indicator"/>SIMULACIÓN · Bogotá Central</div><div className="connectivity">Conexión en tiempo real <span className="role">RESPUESTA</span></div></header>
    <section className="workspace">
      <aside className="layers"><div className="section-title"><LayersIcon/><div><h1>Capas del incidente</h1><span>24 dispositivos · 3 unidades</span></div></div>
        <fieldset><legend>Evidencia operativa</legend>{([['devices','Dispositivos de emergencia'],['rescue','Unidades de rescate'],['areas','Áreas de búsqueda']] as const).map(([key,label])=><label className="layer-row" key={key}><input type="checkbox" checked={visible[key]} onChange={()=>setVisible(v=>({...v,[key]:!v[key]}))}/><span>{label}</span><b>{key==='devices'?24:key==='rescue'?3:2}</b></label>)}</fieldset>
        <div className="summary"><span>Nodos activos<strong>{live}</strong></span><span>SOS activos<strong className="critical-text">2</strong></span><span>Paquetes antiguos<strong>6</strong></span></div>
        <div className="privacy-note"><TargetIcon/><div><strong>Vista autorizada</strong><p>Las coordenadas exactas están limitadas al personal de respuesta. Las vistas públicas solo reciben agregados.</p></div></div>
      </aside>
      <section className="map-region"><MapCanvas devices={simulatedDevices} units={rescueUnits} areas={searchAreas} is3d={is3d} visible={visible} onSelect={setSelectedId}/><div className="map-mode" aria-label="Perspectiva del mapa"><button className={!is3d?'active':''} onClick={()=>setIs3d(false)}>2D</button><button className={is3d?'active':''} onClick={()=>setIs3d(true)}>3D</button></div><div className="map-legend"><span><i className="gps"/>GPS actual</span><span><i className="last"/>Última ubicación</span><span><i className="estimate"/>Estimación histórica</span><span><i className="sos"/>SOS</span></div></section>
      <DevicePanel device={selected} onClose={()=>setSelectedId(null)}/>
    </section>
    <footer className="timeline"><div><strong>Línea de tiempo</strong><span>{timeOffset===0?'En vivo':`hace ${Math.abs(timeOffset)} min`}</span></div><input aria-label="Inspeccionar línea de tiempo" type="range" min="-120" max="0" value={timeOffset} onChange={e=>setTimeOffset(Number(e.target.value))}/><time>20:42:16 COT</time></footer>
  </main>;
}
