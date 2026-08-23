import { useEffect, useRef } from 'react';
import maplibregl, { type GeoJSONSource, type Map } from 'maplibre-gl';
import type { EmergencyDevice, RescueUnit, SearchArea } from '../domain/geo';

interface Props { devices: EmergencyDevice[]; units: RescueUnit[]; areas: SearchArea[]; is3d: boolean; visible: Record<string, boolean>; onSelect: (id: string) => void; }
const styleUrl = import.meta.env.VITE_MAP_STYLE_URL || 'https://demotiles.maplibre.org/style.json';

export function MapCanvas({ devices, units, areas, is3d, visible, onSelect }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const selectRef = useRef(onSelect);
  selectRef.current = onSelect;

  useEffect(() => {
    if (!container.current || mapRef.current) return;
    const map = new maplibregl.Map({ container: container.current, style: styleUrl, center: [-74.0721, 4.711], zoom: 13.3, attributionControl: false });
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'bottom-right');
    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-left');
    map.on('load', () => {
      map.addSource('search-areas', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      map.addLayer({ id: 'search-areas', type: 'fill', source: 'search-areas', paint: { 'fill-color': ['match',['get','priority'],'HIGH','#b94f4d','#b17b3d'], 'fill-opacity': 0.18, 'fill-outline-color': '#c89a58' } });
      map.addSource('emergency-devices', { type: 'geojson', cluster: true, clusterRadius: 44, data: { type: 'FeatureCollection', features: [] } });
      map.addLayer({ id: 'device-clusters', type: 'circle', source: 'emergency-devices', filter: ['has','point_count'], paint: { 'circle-color': '#397f79', 'circle-radius': ['step',['get','point_count'],16,10,21], 'circle-stroke-color':'#edf1ed','circle-stroke-width':2 } });
      map.addLayer({ id: 'cluster-count', type: 'symbol', source: 'emergency-devices', filter: ['has','point_count'], layout: { 'text-field':['get','point_count_abbreviated'], 'text-size':12 }, paint: { 'text-color':'#edf1ed' } });
      map.addLayer({ id: 'emergency-devices', type: 'circle', source: 'emergency-devices', filter: ['!', ['has','point_count']], paint: { 'circle-color':['case',['get','sos'],'#b94f4d',['match',['get','evidenceType'],'CURRENT_GPS','#397f79','LAST_KNOWN','#557691','HISTORICAL_ESTIMATE','#766d84','#768186']], 'circle-radius':['case',['get','sos'],9,7], 'circle-stroke-color':'#edf1ed','circle-stroke-width':2 } });
      map.addSource('rescue-units', { type:'geojson', data:{ type:'FeatureCollection', features:[] } });
      map.addLayer({ id:'rescue-units', type:'circle', source:'rescue-units', paint:{ 'circle-color':'#72a184','circle-radius':8,'circle-stroke-color':'#0d1518','circle-stroke-width':3 } });
      map.on('click', 'emergency-devices', (event) => { const id = event.features?.[0]?.properties?.id; if (id) selectRef.current(id); });
      map.on('click', 'device-clusters', async (event) => { const feature=event.features?.[0]; const id=feature?.properties?.cluster_id; if (id == null) return; const zoom=await (map.getSource('emergency-devices') as GeoJSONSource).getClusterExpansionZoom(id); if (feature?.geometry.type === 'Point') map.easeTo({ center:feature.geometry.coordinates as [number,number], zoom }); });
    });
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
  }, []);

  useEffect(() => { const map=mapRef.current; if (!map) return; const update=() => {
    (map.getSource('emergency-devices') as GeoJSONSource)?.setData({type:'FeatureCollection',features:devices.map(d=>({type:'Feature',geometry:{type:'Point',coordinates:d.coordinates},properties:{id:d.id,sos:d.sos,evidenceType:d.evidenceType}}))});
    (map.getSource('rescue-units') as GeoJSONSource)?.setData({type:'FeatureCollection',features:units.map(u=>({type:'Feature',geometry:{type:'Point',coordinates:u.coordinates},properties:{id:u.id}}))});
    (map.getSource('search-areas') as GeoJSONSource)?.setData({type:'FeatureCollection',features:areas.map(a=>({type:'Feature',geometry:{type:'Polygon',coordinates:a.coordinates},properties:{id:a.id,priority:a.priority}}))});
  }; if (map.isStyleLoaded()) update(); else map.once('load',update); }, [devices, units, areas]);
  useEffect(() => { mapRef.current?.easeTo({ pitch:is3d?58:0, bearing:is3d?-18:0, duration:300 }); }, [is3d]);
  useEffect(() => { const map=mapRef.current;if(!map?.isStyleLoaded())return; for(const id of ['emergency-devices','device-clusters','cluster-count']) if(map.getLayer(id)) map.setLayoutProperty(id,'visibility',visible.devices?'visible':'none'); if(map.getLayer('rescue-units'))map.setLayoutProperty('rescue-units','visibility',visible.rescue?'visible':'none');if(map.getLayer('search-areas'))map.setLayoutProperty('search-areas','visibility',visible.areas?'visible':'none'); },[visible]);
  return <div ref={container} className="map-canvas" role="application" aria-label="Interactive incident map" />;
}
