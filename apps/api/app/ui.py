HOME_HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Football Predictor 2026</title>
  <style>
    :root {
      color-scheme: light;
      --bg:#f4f6f8; --surface:#ffffff; --surface-2:#eef3f1; --ink:#121826; --muted:#617083;
      --line:#d8dee8; --accent:#0f6b50; --accent-2:#17406d; --danger:#9f2f2f; --warn:#a86400;
      --good:#0b7a45; --shadow:0 12px 30px rgba(18,24,38,.08);
    }
    * { box-sizing:border-box; }
    body { margin:0; font-family:Inter, Segoe UI, Arial, sans-serif; background:var(--bg); color:var(--ink); }
    header { background:var(--surface); border-bottom:1px solid var(--line); padding:18px 22px; position:sticky; top:0; z-index:3; }
    .topbar { display:flex; justify-content:space-between; gap:18px; align-items:center; max-width:1500px; margin:0 auto; }
    h1 { margin:0; font-size:24px; letter-spacing:0; }
    h2 { margin:0 0 10px; font-size:17px; }
    h3 { margin:0 0 8px; font-size:14px; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; }
    p { margin:0; color:var(--muted); line-height:1.45; }
    main { max-width:1500px; margin:0 auto; padding:18px; display:grid; grid-template-columns:380px 1fr; gap:18px; }
    section, aside { background:var(--surface); border:1px solid var(--line); border-radius:8px; box-shadow:var(--shadow); }
    aside { padding:14px; display:grid; gap:14px; align-content:start; }
    section { padding:16px; }
    label { display:block; font-size:12px; font-weight:750; color:#334155; margin:12px 0 6px; }
    select, input, textarea, button { width:100%; font:inherit; border-radius:6px; }
    select, input, textarea { border:1px solid var(--line); background:#fff; padding:10px 11px; color:var(--ink); }
    textarea { min-height:130px; resize:vertical; font-family:Consolas, ui-monospace, monospace; font-size:12px; }
    button { border:0; background:var(--accent); color:#fff; padding:10px 12px; font-weight:800; cursor:pointer; margin-top:8px; }
    button:hover { filter:brightness(.96); }
    button.secondary { background:var(--accent-2); }
    button.warn { background:var(--warn); }
    button.ghost { background:#e8edf3; color:#182235; }
    .grid { display:grid; gap:14px; }
    .actions { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
    .metrics { display:grid; grid-template-columns:repeat(4, minmax(140px, 1fr)); gap:10px; margin-bottom:14px; }
    .metric { background:var(--surface-2); border:1px solid var(--line); border-radius:8px; padding:12px; min-height:82px; }
    .metric strong { display:block; font-size:22px; margin-top:6px; }
    .metric span { color:var(--muted); font-size:12px; font-weight:700; }
    .decision { border-radius:8px; padding:16px; margin-bottom:14px; border:1px solid var(--line); }
    .decision.red { background:#fff1f1; border-color:#f0b4b4; }
    .decision.yellow { background:#fff8e8; border-color:#e8c878; }
    .decision.green { background:#eaf8ef; border-color:#94d3aa; }
    .decision.blue { background:#edf5ff; border-color:#9dc3ef; }
    .decision-title { font-size:24px; font-weight:950; margin:2px 0 6px; }
    .decision-main { display:grid; grid-template-columns:1.2fr 1fr 1fr; gap:10px; margin-top:10px; }
    .step { background:#f8fafc; border:1px solid var(--line); border-radius:8px; padding:10px; }
    .pillbar { display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; }
    .pill { display:inline-flex; align-items:center; padding:6px 9px; border-radius:999px; background:#e9f5ef; color:#0f5a43; font-size:12px; font-weight:800; }
    .pill.warn { background:#fff4df; color:#7a4600; }
    .pill.bad { background:#fde8e8; color:#8d2424; }
    .tabs { display:flex; gap:6px; margin-bottom:12px; flex-wrap:wrap; }
    .tab { width:auto; margin:0; background:#e8edf3; color:#1d2939; padding:8px 11px; }
    .tab.active { background:var(--accent); color:#fff; }
    .panel { display:none; }
    .panel.active { display:block; }
    .report { background:#0d1526; color:#edf2f7; border-radius:8px; padding:16px; min-height:560px; overflow:auto; line-height:1.48; }
    .report h1, .report h2 { color:#fff; margin:14px 0 8px; }
    .report h1 { font-size:22px; }
    .report h2 { font-size:17px; border-top:1px solid rgba(255,255,255,.12); padding-top:12px; }
    .report ul { padding-left:18px; }
    .report li { margin:5px 0; }
    pre { white-space:pre-wrap; word-break:break-word; background:#0d1526; color:#edf2f7; padding:14px; border-radius:8px; min-height:360px; }
    details { border:1px solid var(--line); border-radius:8px; padding:10px; background:#fbfcfd; }
    summary { cursor:pointer; font-weight:800; }
    .small { font-size:12px; color:var(--muted); }
    .match-title { font-weight:900; font-size:18px; margin-bottom:4px; }
    .split { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
    @media (max-width:1050px) { main { grid-template-columns:1fr; } .metrics { grid-template-columns:1fr 1fr; } }
    @media (max-width:620px) { .topbar { align-items:flex-start; flex-direction:column; } .metrics, .actions, .split { grid-template-columns:1fr; } }
  </style>
</head>
<body>
  <header>
    <div class="topbar">
      <div>
        <h1>Football Predictor 2026</h1>
        <p>Analisis partido a partido con datos StatsBomb, lineups, cuotas y control de confianza.</p>
      </div>
      <div class="pillbar">
        <span class="pill">Sin Docker</span>
        <span class="pill">StatsBomb activo</span>
        <span class="pill warn">No validado para produccion</span>
      </div>
    </div>
  </header>
  <main>
    <aside>
      <section>
        <h2>Partido</h2>
        <div class="step"><b>1.</b> Elige el partido. <b>2.</b> Toca Analizar. <b>3.</b> Mira el semaforo: apostar, esperar o no apostar.</div>
        <label for="fixture">Fixture cargado</label>
        <select id="fixture"></select>
        <div id="matchCard" class="metric" style="margin-top:10px;"></div>
        <label for="question">Pregunta</label>
        <input id="question" value="Analiza Mexico vs Sudafrica" />
        <button onclick="analyze()">Analizar partido</button>
        <div class="split">
          <input id="genericHome" placeholder="Local: Real Madrid" />
          <input id="genericAway" placeholder="Visitante: Barcelona" />
        </div>
        <input id="genericDate" placeholder="Fecha opcional YYYY-MM-DD" />
        <button class="secondary" onclick="researchAnyMatch()">Investigar cualquier partido</button>
      </section>

      <section>
        <h2>Acciones rapidas</h2>
        <div class="actions">
          <button class="secondary" onclick="refreshOverview()">Resumen</button>
          <button class="secondary" onclick="trustScore()">Confianza</button>
          <button class="secondary" onclick="matchReadiness()">Readiness</button>
          <button class="secondary" onclick="fixedBets()">Apuesta fija</button>
          <button class="secondary" onclick="cockpit()">Cockpit</button>
          <button class="ghost" onclick="valueBets()">Value bets</button>
          <button class="ghost" onclick="oddsBoard()">Cuotas</button>
          <button class="ghost" onclick="priceTargets()">Cuotas objetivo</button>
          <button class="ghost" onclick="prematchAlerts()">Alertas</button>
          <button class="ghost" onclick="dataAudit()">Auditoria</button>
          <button class="ghost" onclick="providerLive()">Live API</button>
          <button class="ghost" onclick="trainingGuide()">Entrenar</button>
          <button class="ghost" onclick="modelHealth()">Health</button>
          <button class="ghost" onclick="statsBombBacktest()">Backtest</button>
          <button class="ghost" onclick="rollingBacktest()">Rolling xG</button>
          <button class="ghost" onclick="dataCoverage()">Cobertura</button>
        </div>
      </section>

      <details>
        <summary>Importar cuotas</summary>
        <p class="small">Pega cuotas 1X2 de casas de apuestas en formato JSON permitido.</p>
        <textarea id="odds">{"records":[{"match_id":"fwc26-001","bookmaker":"Manual","market":"1X2","selection":"Home","decimal_odds":1.72},{"match_id":"fwc26-001","bookmaker":"Manual","market":"1X2","selection":"Draw","decimal_odds":3.75},{"match_id":"fwc26-001","bookmaker":"Manual","market":"1X2","selection":"Away","decimal_odds":5.4}]}</textarea>
        <button class="warn" onclick="importOdds()">Importar cuotas</button>
      </details>

      <details>
        <summary>Importar formaciones</summary>
        <p class="small">Puedes usar "updated_at":"NOW". Ideal 30/40 minutos antes del partido.</p>
        <textarea id="lineups">{"lineups":[{"match_id":"fwc26-001","team_id":"mex","status":"confirmed","source":"manual","updated_at":"NOW","formation":"4-2-3-1","players":[{"name":"Jugador 1","position":"GK","status":"starter","rating":77,"fitness":0.96,"expected_minutes":90}]},{"match_id":"fwc26-001","team_id":"rsa","status":"confirmed","source":"manual","updated_at":"NOW","formation":"4-3-3","players":[{"name":"Jugador 1","position":"GK","status":"starter","rating":72,"fitness":0.96,"expected_minutes":90}]}]}</textarea>
        <button class="warn" onclick="importLineups()">Importar formaciones</button>
      </details>

      <details>
        <summary>Datos reales</summary>
        <p class="small">Sincroniza StatsBomb o pega metricas permitidas/manuales.</p>
        <textarea id="metrics">{"records":[{"team_id":"mex","source":"manual_verified","source_name":"Manual verified","source_url":"https://example.com","as_of":"2026-06-10","sample_size_matches":12,"is_real_data":true,"data_quality":"manual_verified","npxg_for_per90":1.35,"npxg_against_per90":1.05,"shots_on_target_for_per90":4.4,"recent_form_points_per_match":1.7}]}</textarea>
        <button class="warn" onclick="importMetrics()">Importar metricas</button>
        <button class="secondary" onclick="syncStatsBomb()">Sincronizar StatsBomb</button>
        <button class="secondary" onclick="importOddsProvider()">Importar cuotas API</button>
      </details>

      <details open>
        <summary>Laboratorio en vivo</summary>
        <p class="small">Carga minuto y marcador para guardar una prediccion in-play y luego compararla con el resultado final.</p>
        <input id="liveHome" placeholder="Local: Flamengo" />
        <input id="liveAway" placeholder="Visitante: Cusco FC" />
        <div class="split">
          <input id="liveMinute" placeholder="Minuto" value="51" />
          <input id="liveScore" placeholder="Marcador 0-0" value="0-0" />
        </div>
        <button class="secondary" onclick="liveSnapshot()">Snapshot en vivo</button>
        <button class="ghost" onclick="liveSnapshots()">Ver snapshots</button>
      </details>
    </aside>

    <section>
      <div id="decisionCard" class="decision yellow">
        <h3>Decision simple</h3>
        <div class="decision-title">Calculando...</div>
        <p>El sistema va a resumir si conviene apostar, esperar o no apostar.</p>
      </div>
      <div class="metrics">
        <div class="metric"><span>Confianza</span><strong id="trustValue">--</strong><p id="trustSub" class="small">Sin calcular</p></div>
        <div class="metric"><span>Readiness</span><strong id="readyValue">--</strong><p id="readySub" class="small">Sin calcular</p></div>
        <div class="metric"><span>Apuesta fija</span><strong id="betValue">--</strong><p id="betSub" class="small">Sin calcular</p></div>
        <div class="metric"><span>Modelo</span><strong id="healthValue">--</strong><p id="healthSub" class="small">Sin calcular</p></div>
      </div>

      <div class="tabs">
        <button class="tab active" onclick="showTab('report')">Reporte</button>
        <button class="tab" onclick="showTab('json')">JSON</button>
        <button class="tab" onclick="showTab('blockers')">Bloqueadores</button>
      </div>

      <div id="panel-report" class="panel active">
        <div id="report" class="report">Cargando fixture...</div>
      </div>
      <div id="panel-json" class="panel">
        <pre id="jsonOutput">Sin datos todavia.</pre>
      </div>
      <div id="panel-blockers" class="panel">
        <section style="box-shadow:none;">
          <h2>Que falta para confiar mas</h2>
          <div id="blockers"></div>
        </section>
      </div>
    </section>
  </main>

  <script>
    let matches = [];
    let currentReadiness = null;
    const fixture = document.getElementById('fixture');
    const question = document.getElementById('question');
    const report = document.getElementById('report');
    const jsonOutput = document.getElementById('jsonOutput');

    function esc(value) {
      return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
    }
    function markdown(text) {
      const lines = String(text).split('\\n');
      let html = '';
      let inList = false;
      for (const raw of lines) {
        const line = raw.trimEnd();
        if (line.startsWith('## ')) { if (inList) { html += '</ul>'; inList=false; } html += `<h2>${esc(line.slice(3))}</h2>`; }
        else if (line.startsWith('# ')) { if (inList) { html += '</ul>'; inList=false; } html += `<h1>${esc(line.slice(2))}</h1>`; }
        else if (line.startsWith('- ')) { if (!inList) { html += '<ul>'; inList=true; } html += `<li>${esc(line.slice(2))}</li>`; }
        else if (!line) { if (inList) { html += '</ul>'; inList=false; } }
        else { if (inList) { html += '</ul>'; inList=false; } html += `<p>${esc(line)}</p>`; }
      }
      if (inList) html += '</ul>';
      return html;
    }
    function showJson(value) { jsonOutput.textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2); }
    async function api(path, options={}) {
      const res = await fetch(path, options);
      const text = await res.text();
      if (!res.ok) throw new Error(text);
      try { return JSON.parse(text); } catch { return text; }
    }
    function showTab(name) {
      document.querySelectorAll('.tab').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.panel').forEach(panel => panel.classList.remove('active'));
      event.target.classList.add('active');
      document.getElementById(`panel-${name}`).classList.add('active');
    }
    function selectedMatch() { return matches.find(m => m.id === fixture.value); }
    function updateMatchCard() {
      const m = selectedMatch();
      if (!m) return;
      document.getElementById('matchCard').innerHTML = `<div class="match-title">${esc(m.home_team.name)} vs ${esc(m.away_team.name)}</div><p>${esc(m.stage)} - ${esc(m.venue.city)} - ${esc(m.date)}</p>`;
      question.value = `Analiza ${m.home_team.name} vs ${m.away_team.name}`;
      document.getElementById('odds').value = JSON.stringify({records:[
        {match_id:m.id, bookmaker:'Manual', market:'1X2', selection:'Home', decimal_odds:1.9},
        {match_id:m.id, bookmaker:'Manual', market:'1X2', selection:'Draw', decimal_odds:3.4},
        {match_id:m.id, bookmaker:'Manual', market:'1X2', selection:'Away', decimal_odds:4.2}
      ]}, null, 2);
    }
    async function loadMatches() {
      matches = await api('/matches');
      fixture.innerHTML = matches.map(m => `<option value="${m.id}">${esc(m.id)} - ${esc(m.home_team.name)} vs ${esc(m.away_team.name)} - ${esc(m.stage)}</option>`).join('');
      fixture.addEventListener('change', () => { updateMatchCard(); refreshOverview(); });
      updateMatchCard();
      await refreshOverview();
      report.innerHTML = 'Listo. Elige un partido y toca <b>Analizar partido</b>.';
    }
    async function refreshOverview() {
      try {
        const [trust, readiness, fixed, health, decision] = await Promise.all([
          api(`/model/trust/${fixture.value}`),
          api(`/model/match-readiness/${fixture.value}`),
          api(`/value-bets/fixed/${fixture.value}`),
          api('/model/health'),
          api(`/value-bets/decision/${fixture.value}`)
        ]);
        currentReadiness = readiness;
        document.getElementById('trustValue').textContent = trust.trust_score;
        document.getElementById('trustSub').textContent = trust.trust_grade;
        document.getElementById('readyValue').textContent = readiness.ready_for_strong_opinion ? 'Listo' : 'Falta';
        document.getElementById('readySub').textContent = readiness.prematch_readiness.overall_readiness;
        document.getElementById('betValue').textContent = fixed.status.replaceAll('_',' ');
        document.getElementById('betSub').textContent = `${fixed.selection} ${(fixed.model_probability*100).toFixed(1)}%`;
        document.getElementById('healthValue').textContent = health.status;
        document.getElementById('healthSub').textContent = health.production_gate_status;
        renderDecision(decision);
        renderBlockers(readiness, trust);
        showJson({decision, trust, readiness, fixed, health});
      } catch (err) {
        report.textContent = 'Error cargando resumen: ' + err.message;
      }
    }
    function decisionLabel(code) {
      return {
        APUESTA_CANDIDATA:'APUESTA CANDIDATA',
        ESPERAR_CONFIRMACION:'ESPERAR',
        BUSCAR_CUOTA:'BUSCAR CUOTA',
        PROBABLE_PERO_SIN_VALOR:'PROBABLE, PERO SIN VALOR',
        NO_APOSTAR:'NO APOSTAR'
      }[code] || code;
    }
    function renderDecision(decision) {
      const card = document.getElementById('decisionCard');
      card.className = `decision ${decision.color || 'yellow'}`;
      const odds = decision.best_odds ? `${decision.best_bookmaker || 'Book'} @ ${decision.best_odds}` : 'Sin cuota real';
      const ev = decision.ev === null || decision.ev === undefined ? 'n/a' : `${(decision.ev * 100).toFixed(1)}%`;
      const stake = decision.suggested_bankroll_fraction ? `${(decision.suggested_bankroll_fraction * 100).toFixed(2)}% banca` : '0%';
      const minOdds = decision.minimum_odds_for_value ? `Minima valor: ${decision.minimum_odds_for_value}` : '';
      card.innerHTML = `
        <h3>Decision simple</h3>
        <div class="decision-title">${esc(decisionLabel(decision.decision))}</div>
        <p>${esc(decision.action)}</p>
        <div class="decision-main">
          <div><b>Seleccion</b><br>${esc(decision.selection_label)} (${(decision.model_probability*100).toFixed(1)}%)</div>
          <div><b>Cuota / EV</b><br>${esc(odds)} / ${esc(ev)}<br>${esc(minOdds)}</div>
          <div><b>Stake sugerido</b><br>${esc(stake)}</div>
        </div>
        ${decision.blockers && decision.blockers.length ? `<ul>${decision.blockers.map(b => `<li>${esc(b)}</li>`).join('')}</ul>` : '<p>Sin bloqueadores fuertes detectados.</p>'}
        <p class="small">${esc(decision.responsible_note)}</p>
      `;
    }
    function renderBlockers(readiness, trust) {
      const items = [...(readiness.blockers || []), ...(trust.blockers || [])];
      const unique = [...new Set(items)];
      document.getElementById('blockers').innerHTML = unique.length
        ? `<ul>${unique.map(item => `<li>${esc(item)}</li>`).join('')}</ul>`
        : '<p>No hay bloqueadores fuertes. Aun asi, revisar lineups y cuotas antes de apostar.</p>';
    }
    async function analyze() {
      report.textContent = 'Analizando...';
      const text = await api('/analysis/query/report', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({question: question.value}) });
      report.innerHTML = markdown(text);
      await refreshOverview();
    }
    async function researchAnyMatch() {
      report.textContent = 'Buscando datos reales del partido...';
      const payload = {
        home_team: document.getElementById('genericHome').value,
        away_team: document.getElementById('genericAway').value,
        match_date: document.getElementById('genericDate').value || null
      };
      const result = await api('/research/match', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
      showJson(result);
      const picks = (result.probabilities || []).slice(0, 5).map(p => `<li>${esc(p.market)} - ${esc(p.selection)}: ${(p.probability*100).toFixed(1)}%, cuota justa ${p.fair_odds}, minima valor ${p.minimum_odds_for_value}</li>`).join('');
      report.innerHTML = `<h1>${esc(result.home_team)} vs ${esc(result.away_team)}</h1><p><b>Estado:</b> ${esc(result.status)} | <b>Confianza:</b> ${esc(result.confidence)}</p><h2>Probabilidades principales</h2><ul>${picks}</ul><h2>Evidencia</h2><ul>${(result.evidence || []).map(x => `<li>${esc(x)}</li>`).join('')}</ul><h2>Limitaciones</h2><ul>${(result.limitations || []).map(x => `<li>${esc(x)}</li>`).join('')}</ul>`;
    }
    async function trustScore() { const v = await api(`/model/trust/${fixture.value}`); showJson(v); renderBlockers(currentReadiness || {blockers:[]}, v); showTabByName('json'); }
    async function matchReadiness() { const v = await api(`/model/match-readiness/${fixture.value}`); currentReadiness = v; showJson(v); renderBlockers(v, {blockers:[]}); showTabByName('json'); }
    async function fixedBets() { showJson(await api(`/value-bets/fixed/${fixture.value}`)); showTabByName('json'); }
    async function cockpit() { showJson(await api(`/analysis/${fixture.value}/cockpit`)); showTabByName('json'); }
    async function oddsBoard() { showJson(await api(`/value-bets/odds-board/${fixture.value}`)); showTabByName('json'); }
    async function priceTargets() { showJson(await api(`/value-bets/price-targets/${fixture.value}`)); showTabByName('json'); }
    async function prematchAlerts() { showJson(await api('/value-bets/prematch-alerts')); showTabByName('json'); }
    async function dataAudit() { showJson(await api('/data/audit')); showTabByName('json'); }
    async function providerLive() { showJson(await api('/providers/api-football/live')); showTabByName('json'); }
    async function trainingGuide() { showJson(await api('/providers/training')); showTabByName('json'); }
    async function valueBets() { showJson(await api('/value-bets/today')); showTabByName('json'); }
    async function modelHealth() { showJson(await api('/model/health')); showTabByName('json'); }
    async function statsBombBacktest() { showJson(await api('/backtests/run?dataset=statsbomb_open_data', { method:'POST' })); showTabByName('json'); }
    async function rollingBacktest() { showJson(await api('/backtests/run?dataset=statsbomb_rolling_xg', { method:'POST' })); showTabByName('json'); }
    async function dataCoverage() { showJson(await api('/data/coverage')); showTabByName('json'); }
    async function importOdds() { showJson(await api('/data/import/odds', { method:'POST', headers:{'Content-Type':'application/json'}, body: document.getElementById('odds').value })); await refreshOverview(); }
    async function importLineups() { showJson(await api('/prematch/lineups/import', { method:'POST', headers:{'Content-Type':'application/json'}, body: document.getElementById('lineups').value })); await refreshOverview(); }
    async function importMetrics() { showJson(await api('/data/import/team_metrics', { method:'POST', headers:{'Content-Type':'application/json'}, body: document.getElementById('metrics').value })); await refreshOverview(); }
    async function syncStatsBomb() {
      report.textContent = 'Sincronizando StatsBomb Open Data...';
      showJson(await api('/data/statsbomb/sync', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({max_matches_total:180, max_matches_per_team:10, recency_decay:0.12}) }));
      await refreshOverview();
    }
    async function importOddsProvider() {
      showJson(await api('/data/odds-provider/the-odds-api?dry_run=false', { method:'POST' }));
      await refreshOverview();
    }
    async function liveSnapshot() {
      const [homeGoals, awayGoals] = document.getElementById('liveScore').value.split('-').map(x => Number(x.trim()));
      const payload = {
        home_team: document.getElementById('liveHome').value,
        away_team: document.getElementById('liveAway').value,
        minute: Number(document.getElementById('liveMinute').value),
        home_goals: homeGoals || 0,
        away_goals: awayGoals || 0
      };
      const result = await api('/live-lab/snapshot', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
      showJson(result);
      report.innerHTML = `<h1>${esc(result.home_team)} vs ${esc(result.away_team)}</h1><p><b>Minuto:</b> ${result.minute} | <b>Marcador:</b> ${result.score.home}-${result.score.away}</p><h2>Probabilidades live</h2><ul>${Object.entries(result.probabilities).map(([k,v]) => `<li>${esc(k)}: ${(v*100).toFixed(1)}%</li>`).join('')}</ul><p><b>Top call:</b> ${esc(result.top_call)}</p><p class="small">${esc(result.notes.join(' '))}</p>`;
      showTabByName('report');
    }
    async function liveSnapshots() { showJson(await api('/live-lab/snapshots')); showTabByName('json'); }
    function showTabByName(name) {
      document.querySelectorAll('.tab').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.panel').forEach(panel => panel.classList.remove('active'));
      const index = {report:0,json:1,blockers:2}[name] || 0;
      document.querySelectorAll('.tab')[index].classList.add('active');
      document.getElementById(`panel-${name}`).classList.add('active');
    }
    loadMatches().catch(err => { report.textContent = 'Error: ' + err.message; });
  </script>
</body>
</html>
"""
