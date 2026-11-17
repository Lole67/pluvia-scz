const assert=require('node:assert/strict');const P=require('../flood/static/presentation.js');
for(const [v,e] of [[0,0],[24.99,0],[25,1],[49.99,1],[50,2],[75,3],[100,3],[615,3]])assert.equal(P.category(v),e);
const s={rain_mm:50,duration_h:2,saturation:.5,drainage_mmh:5};assert(P.sameScenario(s,{...s,rain_mm:'50'}));assert(!P.sameScenario(s,{...s,rain_mm:100}));
const t={manifest:{version:'v1',shape:[2,2]}},r={territory_version:'v1',maximum_mm:[[1,2],[3,4]],index:[[1,2],[3,4]],final_mm:[[1,2],[3,4]]};assert(P.compatible(r,t));assert(!P.compatible({...r,territory_version:'old'},t));assert(!P.compatible({...r,index:[[1,2]]},t));assert(!P.compatible({...r,index:[[NaN,2],[3,4]]},t));console.log('Presentación: umbrales, edición y compatibilidad PASS.');
