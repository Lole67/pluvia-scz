'use strict';
window.PluviaScenarios = {
  items: [],
  async refresh() {
    const chosen = $('saved-scenarios').value;
    this.items = await api('/api/scenarios');
    $('saved-scenarios').replaceChildren(new Option('Nuevo escenario',''));
    this.items.forEach(s => $('saved-scenarios').add(new Option(s.name,s.id)));
    $('saved-scenarios').value = chosen;
  },
  executionUrl(parameters) {
    const saved = this.items.find(s=>s.id === $('saved-scenarios').value);
    return saved && P.sameScenario(saved.parameters,parameters) ? `/api/scenarios/${saved.id}/simulate` : '/api/simulate';
  }
};
$('saved-scenarios').addEventListener('change', () => {
  const saved = PluviaScenarios.items.find(s=>s.id === $('saved-scenarios').value);
  $('scenario-name').value = saved?.name || '';
  if (saved) { putConfig(saved.parameters); status('Escenario cargado. Pulsa «Simular» para calcular.'); }
});
$('save-scenario').addEventListener('click', async () => {
  if (busy || !$('scenario').reportValidity()) return;
  const name = $('scenario-name').value.trim();
  if (!name) { status('Escribe un nombre para el escenario.',true); $('scenario-name').focus(); return; }
  const id = $('saved-scenarios').value; $('save-scenario').disabled = true;
  try {
    const saved = await api('/api/scenarios' + (id ? '/' + id : ''), {
      method:id?'PUT':'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name,parameters:config()})
    });
    await PluviaScenarios.refresh(); $('saved-scenarios').value = saved.id; status('Escenario guardado.');
  } catch(error) { status(error.message,true); } finally { $('save-scenario').disabled = false; }
});
PluviaScenarios.refresh().catch(error=>status(error.message,true));
