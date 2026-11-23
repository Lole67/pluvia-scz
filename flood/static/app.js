'use strict';
const $=id=>document.getElementById(id),P=FloodPresentation,fmt=(n,d=2)=>Number(n).toLocaleString('es-BO',{maximumFractionDigits:d});
let territory,current,busy=false,selected=null,mapObject=null,mesh=null,mapLoading=false,mapWanted=false,leafletReady=false,floodRenderer=null;
const fields=['rain_mm','duration_h','saturation','drainage_mmh'],names=['Baja','Media','Alta','Muy alta'];
let polygons={report_polygon:[],drain_polygon:[]};
let streetAreas, defaultOutline;
function cellAxes(feature){
 const [nw,ne,,sw]=feature.geometry.coordinates[0];
 return {nw, east:ne.map((v,i)=>v-nw[i]), south:sw.map((v,i)=>v-nw[i])};
}
function streetPoint([x,y]){
 const col=Math.min(23,Math.floor(x)), row=Math.min(23,Math.floor(y));
 const {nw,east,south}=cellAxes(territory.geojson.features[row*24+col]);
 const coord=nw.map((v,i)=>v+(x-col)*east[i]+(y-row)*south[i]);
 return [coord[1],coord[0]];
}
function streetClick(feature,latlng){
 const key=$('draw-target').value;
 if(!key){selectCell(feature.properties);return;}
 if(busy)return;
 const {nw,east,south}=cellAxes(feature);
 const dx=latlng.lng-nw[0],dy=latlng.lat-nw[1];
 const det=east[0]*south[1]-east[1]*south[0];
 const clamp=v=>Math.max(0,Math.min(1,v));
 const x=feature.properties.col+clamp((dx*south[1]-dy*south[0])/det);
 const y=feature.properties.row+clamp((east[0]*dy-east[1]*dx)/det);
 polygons[key].push([+x.toFixed(3),+y.toFixed(3)]);
 drawAreas();intensity();
}
function drawAreas(){
 streetAreas?.clearLayers();
 defaultOutline?.setStyle({opacity:polygons.report_polygon.length?0:1});
 const svg=$('map');
 svg.querySelectorAll('.scenario-area').forEach(el=>el.remove());
 if(!polygons.report_polygon.length)svg.append(node('rect',{class:'scenario-area',x:158,y:130,width:352,height:352,fill:'none',stroke:'#183846','stroke-width':2,'stroke-dasharray':'7 4','pointer-events':'none'}));
 for(const [name,points] of Object.entries(polygons)){
   if(!points.length)continue;
   if(streetAreas){
     const coords=points.map(streetPoint);
     const style={pane:'flood-results',renderer:floodRenderer,interactive:false,color:name==='report_polygon'?'#135cc4':'#ce451e',weight:3};
     if(coords.length>=3)L.polygon(coords,{...style,fillOpacity:.09}).addTo(streetAreas);
     else if(coords.length===2)L.polyline(coords,style).addTo(streetAreas);
     coords.forEach(point=>L.circleMarker(point,{...style,radius:3,fillOpacity:1}).addTo(streetAreas));
   }
   svg.append(node('polygon',{class:'scenario-area',points:points.map(([x,y])=>[70+22*x,42+22*y].join(',')).join(' '),fill:'none',stroke:name==='report_polygon'?'#135cc4':'#ce451e','stroke-width':3,'pointer-events':'none'}));
   for(const [x,y] of points)svg.append(node('circle',{class:'scenario-area',cx:70+22*x,cy:42+22*y,r:3,fill:name==='report_polygon'?'#135cc4':'#ce451e','pointer-events':'none'}));
 }
}
$('draw-target').onchange=()=>{drawAreas();};
$('whole-pilot').onclick=()=>{polygons.report_polygon=[[0,0],[24,0],[24,24],[0,24]];$('draw-target').value='';draw();intensity();};
$('clear-area').onclick=()=>{const key=$('draw-target').value;if(key){polygons[key]=[];drawAreas();intensity();}};
$('map').addEventListener('click',event=>{
 const key=$('draw-target').value;if(!key||busy)return;
 const svg=$('map'),pt=svg.createSVGPoint();pt.x=event.clientX;pt.y=event.clientY;
 const pos=pt.matrixTransform(svg.getScreenCTM().inverse());
 const x=(pos.x-70)/22,y=(pos.y-42)/22;if(x<0||x>24||y<0||y>24)return;
 event.stopPropagation();polygons[key].push([+x.toFixed(3),+y.toFixed(3)]);drawAreas();intensity();
},true);
function config(){
 const data=Object.fromEntries(fields.map(k=>[k,Number($('scenario').elements[k].value)]));
 const profile=$('rain-profile').value;
 if(profile) data.rain_profile=(profile==='custom'?$('rain-custom').value:profile).split(',').map(s=>s.trim()?Number(s):NaN);
 for(const [key,points] of Object.entries(polygons))if(points.length)data[key]=points;
 if(data.drain_polygon)data.local_mmh=Number($('local-rate').value);
 if($('prefer-ml').checked)data.prefer_ml=true;
 return data;
}
$('rain-profile').addEventListener('change',()=>{$('rain-custom-label').hidden=$('rain-profile').value!=='custom';intensity();});
function intensity(){const s=config();$('intensity').textContent=s.duration_h>0?`Intensidad: ${fmt(s.rain_mm/s.duration_h)} mm/h`:'Ingresa una duración mayor que cero.';$('dirty').hidden=!current||P.sameScenario(s,current.scenario);}
function putConfig(s){$('prefer-ml').checked=!!s.prefer_ml;polygons={report_polygon:structuredClone(s.report_polygon||[]),drain_polygon:structuredClone(s.drain_polygon||[])};$('local-rate').value=s.local_mmh??10;$('draw-target').value='';drawAreas();
 const profile=(s.rain_profile||[]).join(',');
 $('rain-profile').value=['','70,30','30,70'].includes(profile)?profile:'custom';
 $('rain-custom-label').hidden=$('rain-profile').value!=='custom';$('rain-custom').value=profile;
const sel=$('saturation');Array.from(sel.options).filter(o=>o.dataset.custom).forEach(o=>o.remove());if(!Array.from(sel.options).some(o=>Number(o.value)===s.saturation)){const o=new Option(`Personalizado · ${fmt(s.saturation)}`,s.saturation);o.dataset.custom='true';sel.add(o);}fields.forEach(k=>$('scenario').elements[k].value=s[k]);intensity();}
function status(message,error=false){$('status').textContent=message;$('status').classList.toggle('error',error);}
async function api(url,options){return PluviaSession.request(url,options);}
function node(tag,attrs,text){const n=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text!==undefined)n.textContent=text;return n;}
function value(p){return $('layer').value==='elevation'?p.elevation_m:current[$('layer').value][p.row][p.col];}
function color(p){const v=value(p),m=territory.manifest;return $('layer').value==='elevation'?`hsl(38,38%,${91-53*(v-m.elevation_min_m)/Math.max(1,m.elevation_max_m-m.elevation_min_m)}%)`:P.colors[P.category(v)];}
function cellText(p){return `${p.cell_id} · ${(current?.report_weights?.[p.row]?.[p.col]??p.report)?'Dentro del reporte':'Margen de cálculo'} · Terreno ${fmt(p.elevation_m)} m${current?` · Agua máxima ${fmt(current.maximum_mm[p.row][p.col])} mm · Índice ${fmt(current.index[p.row][p.col])}/100`:''}`;}
function overlayOpacity(){return Number($('grid-opacity').value)/100;}
function mapStyle(f){const p=f.properties,chosen=selected&&selected.cell_id===p.cell_id;
 const lines=$('grid-lines').checked, zoom=mapObject?mapObject.getZoom():14;
 return {color:chosen?'#e57821':'#415c69',weight:chosen?3:lines?(zoom<13?.2:zoom<15?.5:.8):0,opacity:chosen?1:.45,fillColor:color(p),fillOpacity:overlayOpacity()*((current?.report_weights?.[p.row]?.[p.col]??p.report)?1:.28)};
}
function refreshOverlay(){
 $('opacity-value').textContent=`${$('grid-opacity').value} %`;
 if(mesh)mesh.setStyle(mapStyle);
 if(!territory)return;
 territory.geojson.features.forEach(f=>{const p=f.properties,el=$(`cell-${p.row}-${p.col}`);if(!el)return;
 el.setAttribute('fill-opacity',overlayOpacity()*((current?.report_weights?.[p.row]?.[p.col]??p.report)?1:.28));
 el.setAttribute('stroke-width',selected&&selected.cell_id===p.cell_id?3:$('grid-lines').checked?.4:0);
 });
}
function selectCell(p){selected=p;$('cell-card').hidden=false;
 $('cell-title').textContent=`Fila ${p.row+1} · Columna ${p.col+1}`;
 $('cell-location').textContent=`${(current?.report_weights?.[p.row]?.[p.col]??p.report)?'Dentro del área de reporte':'Margen de cálculo'} · ${p.cell_id}`;
 const values=[['Altura del terreno',`${fmt(p.elevation_m)} m`],['Agua máxima simulada',current?`${fmt(current.maximum_mm[p.row][p.col])} mm`:'Sin simular'],['Índice relativo',current?`${fmt(current.index[p.row][p.col])} / 100`:'Sin simular']];
 const cover=territory.manifest.sources.land_cover;
 const soil=territory.soilgrids?.cells.find(cell=>cell.cell_id===p.cell_id);
 if(soil){
   const texture=soil.status==='sin_datos' && soil.sand_pct==null && soil.clay_pct==null
     ? 'Sin datos de arena y arcilla'
     : [soil.sand_pct==null?'Arena sin datos':`Arena ${fmt(soil.sand_pct)} %`,
        soil.clay_pct==null?'Arcilla sin datos':`Arcilla ${fmt(soil.clay_pct)} %`].join(' · ');
   values.push(['SoilGrids · 0–5 cm',texture]);
   if(soil.status==='valida') values.push(['Conductividad estimada del suelo',`${fmt(soil.soil_ksat_mmh)} mm/h`]);
   if(soil.status==='textura_inconsistente') values.push(['Calidad de la textura','Porcentajes inconsistentes']);
   values.push(['Infiltración base del simulador',`${fmt(p.infiltration_mmh)} mm/h · provisional`]);
 }
 if(cover && p.land_cover_pct){
   const parts=Object.entries(p.land_cover_pct).sort((a,b)=>b[1]-a[1])
     .map(([code,percent])=>`${cover.classes[code]} ${fmt(percent)} %`);
   values.push([`Cobertura del suelo · ${cover.year}`,parts.join(' · ')]);
 }
 $('cell-info').replaceChildren();values.forEach(([label,value])=>{const item=document.createElement('div'),name=document.createElement('span'),number=document.createElement('strong');name.textContent=label;number.textContent=value;item.append(name,number);$('cell-info').append(item);});
 document.querySelectorAll('#map .selected').forEach(e=>e.classList.remove('selected'));const el=$(`cell-${p.row}-${p.col}`);if(el)el.classList.add('selected');refreshOverlay();
}
function clearCell(){const previous=selected;selected=null;$('cell-card').hidden=true;document.querySelectorAll('#map .selected').forEach(e=>e.classList.remove('selected'));if(mapObject)mapObject.closePopup();refreshOverlay();if(previous&&!$('map').hasAttribute('hidden'))$(`cell-${previous.row}-${previous.col}`).focus();else $('layer').focus();}
$('close-cell').addEventListener('click',clearCell);
$('grid-opacity').addEventListener('input',refreshOverlay);
$('grid-lines').addEventListener('change',refreshOverlay);
function draw(){queueMicrotask(drawAreas);const svg=$('map'),layer=$('layer').value,m=territory.manifest,features=territory.geojson.features;svg.replaceChildren();
 features.forEach(f=>{const p=f.properties,v=value(p),cell=node('rect',{id:`cell-${p.row}-${p.col}`,x:70+p.col*22,y:42+p.row*22,width:22,height:22,fill:color(p),stroke:'#71828b','stroke-width':$('grid-lines').checked?.4:0,class:'cell','fill-opacity':overlayOpacity()*((current?.report_weights?.[p.row]?.[p.col]??p.report)?1:.28),'pointer-events':'all',tabindex:0,role:'button','aria-label':`Fila ${p.row+1}, columna ${p.col+1}: ${fmt(v)} ${layer==='index'?'puntos':layer==='elevation'?'m de elevación':'mm simulados'}`});cell.addEventListener('click',()=>selectCell(p));cell.addEventListener('keydown',e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();selectCell(p);}});cell.append(node('title',{},cellText(p)));svg.append(cell);});
 svg.append(node('text',{x:630,y:38,fill:'#173442','font-size':16},'↑ N'),node('line',{x1:70,y1:590,x2:158,y2:590,stroke:'#173442','stroke-width':3}),node('text',{x:70,y:610,'font-size':12},'1 km'));
 const nw=features[0].geometry.coordinates[0][0],se=features.at(-1).geometry.coordinates[0][2];svg.append(node('text',{x:70,y:25,'font-size':12},`${fmt(nw[1],4)}°, ${fmt(nw[0],4)}°`),node('text',{x:410,y:590,'font-size':12},`${fmt(se[1],4)}°, ${fmt(se[0],4)}°`));
 $('map-title').textContent=layer==='elevation'?'Altura del terreno':layer==='index'?'Susceptibilidad relativa':'Agua máxima simulada';$('map-caption').textContent=layer==='elevation'?'FABDEM público/modelado · promedio a 250 m':`Resultado ${current.run_id.slice(0,8)} · ${fmt(current.scenario.rain_mm)} mm en ${fmt(current.scenario.duration_h)} h · ${current.motor==='ml'?'ML experimental':'Simulador'} · Reporte de ${fmt(current.summary.report_km2??m.report_area_km2)} km²`;
 $('legend').classList.toggle('terrain-legend',layer==='elevation');$('legend').replaceChildren();if(layer==='elevation'){$('legend').textContent=`${fmt(m.elevation_min_m)}–${fmt(m.elevation_max_m)} m · Oscuro = mayor elevación.`;$('layer-help').textContent='Es la altura del suelo, no la cantidad de agua.';}else{names.forEach((name,i)=>{const el=document.createElement('span'),sw=document.createElement('i');sw.className='swatch';sw.style.background=P.colors[i];el.append(sw,document.createTextNode(layer==='index'?`${name}: ${['0–<25','25–<50','50–<75','75–100'][i]}`:['0–<25 mm','25–<50 mm','50–<75 mm','≥75 mm'][i]));$('legend').append(el);});$('layer-help').textContent=layer==='index'?'Escala provisional común: 1 punto por mm simulado, hasta 100 puntos.':'El último color incluye todos los valores desde 75 mm. Selecciona una celda para conocer el máximo exacto.';}
 if(mesh){mapObject.closePopup();mesh.setStyle(f=>mapStyle(f));}if(selected)selectCell(selected);refreshOverlay();
}
function renderAreas(areas){$('areas').replaceChildren();['baja','media','alta','muy_alta'].forEach((key,i)=>{const row=document.createElement('div');row.className='area-row';const label=document.createElement('span');label.textContent=names[i];const track=document.createElement('div');track.className='area-track';const bar=document.createElement('div');bar.style.width=`${areas[key]/(current?.summary?.report_km2??territory.manifest.report_area_km2)*100}%`;bar.style.background=P.colors[i];track.append(bar);const n=document.createElement('span');n.textContent=`${fmt(areas[key])} km²`;row.append(label,track,n);$('areas').append(row);});}
function showResult(d){if(!P.compatible(d,territory))throw Error('Resultado de otra versión territorial o matrices incompatibles. El mapa no se modificó.');current=d;$('report-area').textContent=fmt(d.summary.report_km2??territory.manifest.report_area_km2)+' km²';putConfig(d.scenario);Array.from($('layer').options).forEach(o=>o.disabled=false);$('layer').value='index';draw();$('maximum').textContent=`${fmt(d.summary.max_mm)} mm`;$('mean').textContent=`${fmt(d.summary.mean_index)} / 100`;$('elapsed').textContent=`${fmt(d.elapsed_s,3)} s`;
 const high=d.summary.category_area_km2.alta+d.summary.category_area_km2.muy_alta;$('result-heading').textContent=`Escenario de ${fmt(d.scenario.rain_mm)} mm en ${fmt(d.scenario.duration_h)} horas`;$('explanation').textContent=`Con estos supuestos, ${fmt(high)} de los ${fmt(d.summary.report_km2??territory.manifest.report_area_km2)} km² del reporte alcanzan un índice de al menos 50. La mayor acumulación simulada es ${fmt(d.summary.max_mm)} mm. ${d.summary.max_mm>d.scenario.rain_mm?'Puede superar la lluvia local porque recibe agua de celdas vecinas. ':''}No es una profundidad real validada.`;
 $('result-context').textContent=`Ejecución ${d.run_id.slice(0,8)} · ${new Date(d.created_at).toLocaleString('es-BO')} · ${d.scenario.rain_mm} mm en ${d.scenario.duration_h} h · Saturación ${d.scenario.saturation} · Drenaje ${d.scenario.drainage_mmh} mm/h · Motor ${d.engine_version} · Índice ${d.index_version}`;if(d.step_s)$('result-context').textContent+=' · Paso '+fmt(d.step_s)+' s';renderAreas(d.summary.category_area_km2);$('result-context').textContent+=' · '+(d.motor_reason||'Simulación');if(d.motor==='ml'){$('balance').textContent='Acumulación máxima estimada por ML.';return;}const b=d.ledger.at(-1);$('balance').textContent=`Dominio completo: lluvia ${fmt(b.rain_m3)} m³ − infiltración ${fmt(b.infiltration_m3)} m³ − drenaje ${fmt(b.drainage_m3)} m³ = almacenamiento final ${fmt(b.stored_m3)} m³. Residuo ${b.residual_m3.toExponential(2)} m³; tolerancia ${d.tolerance_m3.toExponential(2)} m³.`;
}
async function history(){
 const data=await api('/api/runs?include_warnings=1');
 $('history').replaceChildren(new Option('Selecciona una ejecución',''));
 data.runs.filter(r=>!r.status||r.status==='completed').forEach(r=>$('history').add(new Option(`${new Date(r.created_at).toLocaleString('es-BO')} · ${r.scenario.rain_mm} mm / ${r.scenario.duration_h} h · ${r.run_id.slice(0,6)}${r.owner_username ? ` · ${r.owner_username}` : ""}`,r.run_id)));
 const warning=$('history-warning');const incomplete=data.runs.filter(r=>r.status&&r.status!=='completed');warning.hidden=data.warnings.length===0&&incomplete.length===0;
 warning.textContent=data.warnings.length?`No se pudieron leer ${data.warnings.length} archivos. Los demás resultados siguen disponibles. No se borró ningún archivo. Revisar: ${data.warnings.join(', ')}`:incomplete.length?`${incomplete.length} ejecuciones sin resultado: ${incomplete.filter(r=>r.status==='failed').length} fallidas y ${incomplete.filter(r=>r.status==='running').length} en curso.`:'';
}
function lock(v){busy=v;['saved-scenarios','scenario-name','save-scenario'].forEach(id=>{if($(id))$(id).disabled=v;});window.PluviaScenarios?.updateControls?.();$('inputs').disabled=v;$('history').disabled=v;document.querySelectorAll('[data-rain]').forEach(b=>b.disabled=v);$('execute').textContent=v?'Calculando…':'Simular';}
$('scenario').addEventListener('input',intensity);$('scenario').addEventListener('change',intensity);intensity();document.querySelectorAll('[data-rain]').forEach(b=>b.addEventListener('click',()=>{if(busy)return;putConfig({rain_mm:Number(b.dataset.rain),duration_h:2,saturation:.5,drainage_mmh:5});status('Ejemplo cargado. Pulsa «Simular» para calcularlo.');}));
$('scenario').addEventListener('submit',async e=>{e.preventDefault();if(busy||!territory)return;const payload=config();lock(true);status('Calculando y guardando…');try{const d=await api(window.PluviaScenarios?.executionUrl(payload)||'/api/simulate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});showResult(d);status('Resultado calculado y guardado. Explora las celdas.');try{await history();if(window.PluviaScenarios)await PluviaScenarios.refresh();$('history').value=d.run_id;}catch(_){status('Resultado guardado. No se pudo actualizar la lista; recarga para consultarlo.');}}catch(e){status(e.message,true);}finally{lock(false);}});
$('history').addEventListener('change',async()=>{if(!$('history').value||busy)return;lock(true);try{showResult(await api('/api/runs/'+$('history').value));window.PluviaScenarios?.resetSelection?.();status('Resultado guardado recuperado; no se volvió a calcular.');}catch(e){status(e.message,true);}finally{lock(false);}});$('layer').addEventListener('change',()=>{if(territory)draw();});
function resource(tag,url){return new Promise((resolve,reject)=>{const el=document.createElement(tag);if(tag==='link'){el.rel='stylesheet';el.href=url;}else{el.src=url;el.async=true;}const timer=setTimeout(()=>{el.remove();reject(Error('Tiempo agotado'));},6000);el.onload=()=>{clearTimeout(timer);resolve();};el.onerror=()=>{clearTimeout(timer);el.remove();reject(Error('Recurso no disponible'));};document.head.append(el);});}
function localView(){mapWanted=false;$('leaflet-map').hidden=true;$('map').removeAttribute('hidden');$('online-map').setAttribute('aria-pressed','false');$('local-map').setAttribute('aria-pressed','true');$('reset-view').hidden=true;$('map-status').textContent='Vista local sin internet. Cálculo, valores y selección de celdas siguen disponibles.';}
async function onlineView(){if(!territory)return;mapWanted=true;if(mapLoading)return;mapLoading=true;$('online-map').disabled=true;$('map-status').textContent='Cargando mapa de referencia… La vista local sigue disponible.';try{
 if(!leafletReady){const base=territory.leaflet_local?'/static/vendor/leaflet/':'https://unpkg.com/leaflet@1.9.4/dist/';await Promise.all([resource('link',base+'leaflet.css'),resource('script',base+'leaflet.js')]);if(!window.L)throw Error('Biblioteca no disponible');leafletReady=true;}if(!mapWanted)return;$('leaflet-map').hidden=false;$('map').setAttribute('hidden','');
 if(!mapObject){mapObject=L.map('leaflet-map',{minZoom:11,maxZoom:18,preferCanvas:true}).setView([-17.779,-63.179],13);const pane=mapObject.createPane('flood-results');pane.style.zIndex='450';floodRenderer=L.canvas({pane:'flood-results',padding:.25});L.control.scale({imperial:false}).addTo(mapObject);const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(mapObject);tiles.on('tileerror',()=>{if(mapWanted)$('map-status').textContent='Algunas calles no pudieron cargarse. La malla sigue disponible; puedes usar la vista local.';});
 mesh=L.geoJSON(territory.geojson,{pane:'flood-results',renderer:floodRenderer,style:f=>mapStyle(f),onEachFeature:(f,layer)=>layer.on('click',event=>streetClick(f,event.latlng))}).addTo(mapObject);
 const fs=territory.geojson.features,corner=(r,c,k)=>fs[r*24+c].geometry.coordinates[0][k],ring=[corner(4,4,0),corner(4,19,1),corner(19,19,2),corner(19,4,3)];defaultOutline=L.polygon(ring.map(([x,y])=>[y,x]),{pane:'flood-results',renderer:floodRenderer,fill:false,color:'#183846',weight:2,dashArray:'7 4',interactive:false}).addTo(mapObject);streetAreas=L.layerGroup().addTo(mapObject);drawAreas();mapObject.fitBounds(mesh.getBounds());mapObject.setMaxBounds(mesh.getBounds().pad(.7));mapObject.on('zoomend',refreshOverlay);}
 mapObject.invalidateSize({pan:false});mesh.setStyle(f=>mapStyle(f));drawAreas();requestAnimationFrame(()=>{mapObject.invalidateSize({pan:false});mesh.eachLayer(layer=>layer.redraw());});$('online-map').setAttribute('aria-pressed','true');$('local-map').setAttribute('aria-pressed','false');$('reset-view').hidden=false;$('map-status').textContent='Selecciona una celda para ver sus valores.';
 }catch(_){if(mapWanted){localView();$('map-status').textContent='Mapa con calles no disponible. Continúa con la vista local o vuelve a intentarlo.';}}finally{mapLoading=false;$('online-map').disabled=false;}}
$('online-map').addEventListener('click',onlineView);$('local-map').addEventListener('click',localView);$('reset-view').addEventListener('click',()=>{if(mapObject)mapObject.fitBounds(mesh.getBounds());});
(async()=>{lock(true);try{if(window.PluviaSession)await PluviaSession.requireUser();territory=await api('/api/territory');territory.manifest.warnings.forEach(w=>{const li=document.createElement('li');li.textContent=w;$('warnings').append(li);});draw();$('report-area').textContent=`${fmt(territory.manifest.report_area_km2)} km²`;lock(false);status('Terreno listo. Elige un ejemplo o configura tu escenario.');try{await history();}catch(_){status('Terreno listo. El historial no está disponible temporalmente.',true);}}catch(e){status('No se pudo cargar el terreno: '+e.message,true);$('execute').textContent='Terreno no disponible';}})();
