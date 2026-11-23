(function(root){'use strict';
 const colors=['#d3ebee','#81c6ce','#338fa9','#303e80'];
 function category(v){return Math.min(3,Math.floor(Math.max(0,v)/25));}
 function sameScenario(a,b){return (a.prefer_ml??false)===(b.prefer_ml??false) && ["report_polygon","drain_polygon","local_mmh"].every(k=>JSON.stringify(a[k]??null)===JSON.stringify(b[k]??null)) && JSON.stringify(a.rain_profile||null)===JSON.stringify(b.rain_profile||null) && ['rain_mm','duration_h','saturation','drainage_mmh'].every(k=>Number(a[k])===Number(b[k]));}
 function compatible(run,t){const [rows,cols]=t.manifest.shape;return run.territory_version===t.manifest.version&&(run.motor==='ml'?['maximum_mm','index']:['maximum_mm','index','final_mm']).every(k=>Array.isArray(run[k])&&run[k].length===rows&&run[k].every(r=>Array.isArray(r)&&r.length===cols&&r.every(Number.isFinite)));}
 const api={colors,category,sameScenario,compatible};if(typeof module==='object'&&module.exports)module.exports=api;else root.FloodPresentation=api;
})(globalThis);
