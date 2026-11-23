'use strict';
window.PluviaScenarios = {
  items: [],
  loadedId: null,
  updateControls() {
    const selected = $('saved-scenarios').value;
    $('load-scenario').disabled = busy || !selected;
    $('save-scenario').disabled = busy || Boolean(selected && selected !== this.loadedId);
  },
  resetSelection() {
    this.loadedId = null;
    $('saved-scenarios').value = '';
    $('scenario-name').value = '';
    this.updateControls();
  },
  async refresh() {
    const chosen = $('saved-scenarios').value;
    this.items = await api('/api/scenarios');
    $('saved-scenarios').replaceChildren(new Option('Nuevo escenario',''));
    this.items.forEach(s => $('saved-scenarios').add(new Option(s.name,s.id)));
    $('saved-scenarios').value = chosen;
    this.updateControls();
  },
  executionUrl(parameters) {
    const saved = this.items.find(s=>s.id === this.loadedId);
    return saved && P.sameScenario(saved.parameters,parameters) ? `/api/scenarios/${saved.id}/simulate` : '/api/simulate';
  }
};
$('saved-scenarios').addEventListener('change', () => {
  if (!$('saved-scenarios').value) PluviaScenarios.resetSelection();
  else PluviaScenarios.updateControls();
});
$('load-scenario').addEventListener('click', () => {
  const saved = PluviaScenarios.items.find(item => item.id === $('saved-scenarios').value);
  if (busy || !saved) return;
  putConfig(saved.parameters);
  PluviaScenarios.loadedId = saved.id;
  $('scenario-name').value = saved.name;
  PluviaScenarios.updateControls();
  status('Configuración cargada. Pulsa «Simular» para calcular.');
});
$('save-scenario').addEventListener('click', async () => {
  if (busy || !$('scenario').reportValidity()) return;
  const name = $('scenario-name').value.trim();
  if (!name) { status('Escribe un nombre para el escenario.',true); $('scenario-name').focus(); return; }
  const id = PluviaScenarios.loadedId; $('save-scenario').disabled = true;
  try {
    const saved = await api('/api/scenarios' + (id ? '/' + id : ''), {
      method:id?'PUT':'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name,parameters:config()})
    });
    await PluviaScenarios.refresh(); $('saved-scenarios').value = saved.id; PluviaScenarios.loadedId = saved.id; status('Escenario guardado.');
  } catch(error) { status(error.message,true); } finally { PluviaScenarios.updateControls(); }
});
PluviaScenarios.refresh().catch(error=>status(error.message,true));
