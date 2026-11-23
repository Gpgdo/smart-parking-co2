const API = "/api";

let charts = {};
let allPeaks = [];

function fmt(n, digits = 1) {
  if (n === null || n === undefined) return "—";
  return Number(n).toLocaleString("pt-BR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function fmtDateTime(iso) {
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function getJSON(path) {
  const res = await fetch(API + path);
  if (!res.ok) {
    throw new Error(`Falha em ${path}: HTTP ${res.status}`);
  }
  return res.json();
}

async function postJSON(path) {
  const res = await fetch(API + path, { method: "POST" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg =
      (data.detail && (data.detail.mensagem || data.detail)) ||
      `HTTP ${res.status}`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

function downsample(rows, maxPoints) {
  if (rows.length <= maxPoints) return rows;
  const step = Math.ceil(rows.length / maxPoints);
  return rows.filter((_, i) => i % step === 0);
}

async function checkHealth() {
  const dot = document.getElementById("status-dot");
  const text = document.getElementById("status-text");

  try {
    const health = await getJSON("/health");
    dot.className = "dot ok";
    text.textContent = "API e banco conectados";
  } catch (err) {
    dot.className = "dot error";
    text.textContent = "API/banco indisponível";
  }
}

function renderCards(summary) {
  const cards = [
    { label: "Leituras processadas", value: fmt(summary.total_leituras, 0) },
    { label: "Minutos ocupados", value: fmt(summary.total_minutos_ocupados, 0) },
    { label: "CO₂ médio (ppm)", value: fmt(summary.co2_medio), cls: "accent" },
    { label: "CO₂ máximo (ppm)", value: fmt(summary.co2_maximo), cls: "warn" },
    { label: "Picos de CO₂ detectados", value: fmt(summary.total_picos, 0) },
    { label: "Maior ocupação real", value: summary.dia_maior_ocupacao_real ?? "—" },
    { label: "Maior atividade (CO₂)", value: summary.dia_maior_atividade_co2 ?? "—" },
  ];

  const container = document.getElementById("summary-cards");
  container.innerHTML = cards
    .map(
      (c) => `
        <div class="card">
          <div class="label">${c.label}</div>
          <div class="value ${c.cls ?? ""}">${c.value}</div>
        </div>`
    )
    .join("");
}

function renderWeekChart(rows) {
  const ctx = document.getElementById("chart-week");
  const sample = downsample(rows, 1500);

  charts.week?.destroy();
  charts.week = new Chart(ctx, {
    type: "line",
    data: {
      labels: sample.map((r) => fmtDateTime(r.timestamp)),
      datasets: [
        {
          label: "CO₂ sensor (bruto)",
          data: sample.map((r) => r.co2_sensor),
          borderColor: "#93a0bd",
          borderWidth: 1,
          pointRadius: 0,
        },
        {
          label: "CO₂ filtrado",
          data: sample.map((r) => r.co2_filtered),
          borderColor: "#4fd1c5",
          borderWidth: 2,
          pointRadius: 0,
        },
      ],
    },
    options: chartOptions("Concentração de CO₂ (ppm)"),
  });
}

function renderDailyChart(daily) {
  const ctx = document.getElementById("chart-daily");

  charts.daily?.destroy();
  charts.daily = new Chart(ctx, {
    type: "bar",
    data: {
      labels: daily.map((d) => d.weekday),
      datasets: [
        {
          label: "Ocupação real (minutos)",
          data: daily.map((d) => d.ocupacao_real),
          backgroundColor: "#f6ad55",
          yAxisID: "y",
        },
        {
          label: "Atividade estimada (CO₂)",
          data: daily.map((d) => d.atividade_co2),
          backgroundColor: "#4fd1c5",
          yAxisID: "y1",
        },
      ],
    },
    // Escalas bem diferentes (minutos ocupados x índice de CO₂ acumulado):
    // cada série ganha seu próprio eixo Y para as duas ficarem visíveis.
    options: chartOptions("Minutos ocupados", "Índice de atividade (CO₂)"),
  });
}

function fmtHour(iso) {
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

async function renderHourly(day) {
  const todos = day === "todos";
  const rows = await getJSON(todos ? "/stats/hourly" : `/stats/hourly?dia=${day}`);
  const rotulo = (iso) => (todos ? fmtDateTime(iso) : fmtHour(iso));

  document.getElementById("hourly-subtitle").textContent = todos
    ? `Média, mediana e desvio padrão do CO₂ do sensor, por janela de 1 hora — todos os dias (${rows.length} janelas)`
    : `Média, mediana e desvio padrão do CO₂ do sensor, por janela de 1 hora — ${day}`;

  charts.hourly?.destroy();
  charts.hourly = new Chart(document.getElementById("chart-hourly"), {
    type: "bar",
    data: {
      labels: rows.map((r) => rotulo(r.hora)),
      datasets: [
        {
          type: "line",
          label: "Média",
          data: rows.map((r) => r.media),
          borderColor: "#4fd1c5",
          backgroundColor: "#4fd1c5",
          borderWidth: todos ? 1.5 : 2,
          pointRadius: todos ? 0 : 3,
          yAxisID: "y",
        },
        {
          type: "line",
          label: "Mediana",
          data: rows.map((r) => r.mediana),
          borderColor: "#f6ad55",
          backgroundColor: "#f6ad55",
          borderDash: todos ? [] : [6, 4],
          borderWidth: todos ? 1.5 : 2,
          pointStyle: "rectRot",
          pointRadius: todos ? 0 : 6,
          pointBackgroundColor: "transparent",
          pointBorderColor: "#f6ad55",
          pointBorderWidth: 2,
          yAxisID: "y",
        },
        {
          type: "bar",
          label: "Desvio padrão",
          data: rows.map((r) => r.desvio_padrao),
          backgroundColor: "rgba(147, 160, 189, 0.55)",
          yAxisID: "y1",
        },
      ],
    },
    options: chartOptions("CO₂ (ppm)", "Desvio padrão (ppm)"),
  });

  document.querySelector("#hourly-table tbody").innerHTML = rows
    .map(
      (r) => `
        <tr>
          <td>${rotulo(r.hora)}</td>
          <td>${r.amostras}</td>
          <td>${fmt(r.media, 2)}</td>
          <td>${fmt(r.mediana, 2)}</td>
          <td>${fmt(r.desvio_padrao, 2)}</td>
          <td>${fmt(r.ocupacao_pct, 0)}%</td>
        </tr>`
    )
    .join("");
}

async function renderDayChart(day) {
  document.getElementById("hourly-day-select").value = day;
  renderHourly(day);
  const rows = await getJSON(`/readings?dia=${day}`);
  const peaksOfDay = allPeaks.filter(
    (p) => p.timestamp.slice(0, 10) === day
  );

  const ctx = document.getElementById("chart-day");

  charts.day?.destroy();
  charts.day = new Chart(ctx, {
    type: "line",
    data: {
      labels: rows.map((r) => fmtDateTime(r.timestamp)),
      datasets: [
        {
          label: "CO₂ sensor (bruto)",
          data: rows.map((r) => r.co2_sensor),
          borderColor: "#93a0bd",
          borderWidth: 1,
          pointRadius: 0,
        },
        {
          label: "CO₂ filtrado",
          data: rows.map((r) => r.co2_filtered),
          borderColor: "#4fd1c5",
          borderWidth: 2,
          pointRadius: 0,
        },
        {
          label: "Picos detectados",
          data: rows.map((r) => {
            const isPeak = peaksOfDay.some((p) => p.timestamp === r.timestamp);
            return isPeak ? r.co2_filtered : null;
          }),
          borderColor: "#fc8181",
          backgroundColor: "#fc8181",
          pointRadius: 6,
          showLine: false,
        },
      ],
    },
    options: chartOptions("Concentração de CO₂ (ppm)"),
  });
}

function renderPeaksTable(peaks) {
  const tbody = document.querySelector("#peaks-table tbody");
  tbody.innerHTML = peaks
    .map(
      (p) => `
        <tr>
          <td>${fmtDateTime(p.timestamp)}</td>
          <td>${p.weekday}</td>
          <td>${fmt(p.co2_filtered)}</td>
          <td>${fmt(p.prominence)}</td>
        </tr>`
    )
    .join("");
}

function chartOptions(yTitle, y1Title) {
  const scales = {
    x: {
      ticks: { color: "#93a0bd", maxTicksLimit: 12 },
      grid: { color: "#263049" },
    },
    y: {
      position: "left",
      title: { display: !!yTitle, text: yTitle, color: "#93a0bd" },
      ticks: { color: "#93a0bd" },
      grid: { color: "#263049" },
    },
  };

  // Segundo eixo Y, usado quando duas séries têm escalas muito diferentes
  // (ex.: veículos x índice de CO₂ acumulado) e não podem compartilhar eixo.
  if (y1Title) {
    scales.y1 = {
      position: "right",
      title: { display: true, text: y1Title, color: "#93a0bd" },
      ticks: { color: "#93a0bd" },
      grid: { drawOnChartArea: false },
    };
  }

  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    scales,
    plugins: {
      legend: { labels: { color: "#e7ecf7" } },
    },
  };
}

const CORES_GRUPO = ["#93a0bd", "#4fd1c5", "#f6ad55", "#fc8181"];

function nomeGrupo(k, grupo) {
  const nomes = {
    2: ["CO₂ baixo e estável", "CO₂ alto e variável"],
    3: ["CO₂ baixo e estável", "CO₂ médio", "CO₂ muito alto"],
  };
  return (nomes[k] && nomes[k][grupo]) || `Grupo ${grupo + 1}`;
}

async function renderClusters(k) {
  const data = await getJSON(`/clusters?k=${k}`);

  document.getElementById("kmeans-subtitle").textContent =
    `${data.k} grupos · ${data.total_janelas} janelas · silhouette ${fmt(data.silhouette, 2)} (quanto mais perto de 1, mais separados os grupos)`;

  const datasets = data.grupos.map((g) => ({
    label: nomeGrupo(data.k, g.grupo),
    data: data.janelas
      .filter((r) => r.grupo === g.grupo)
      .map((r) => ({ x: r.media, y: r.desvio_padrao, hora: r.hora, ocup: r.ocupacao_pct })),
    backgroundColor: CORES_GRUPO[g.grupo] + "cc",
    borderColor: CORES_GRUPO[g.grupo],
    pointRadius: 4,
    pointHoverRadius: 7,
  }));

  const options = chartOptions("Desvio padrão do CO₂ (ppm)");
  options.interaction = { mode: "nearest", intersect: true };
  options.scales.x = {
    type: "linear",
    title: { display: true, text: "CO₂ médio da janela (ppm)", color: "#93a0bd" },
    ticks: { color: "#93a0bd" },
    grid: { color: "#263049" },
  };
  options.plugins.tooltip = {
    callbacks: {
      label: (ctx) => {
        const p = ctx.raw;
        return `${fmtDateTime(p.hora)} · média ${fmt(p.x)} · desvio ${fmt(p.y)} · ocupação ${fmt(p.ocup, 0)}%`;
      },
    },
  };

  charts.kmeans?.destroy();
  charts.kmeans = new Chart(document.getElementById("chart-kmeans"), {
    type: "scatter",
    data: { datasets },
    options,
  });

  document.querySelector("#kmeans-table tbody").innerHTML = data.grupos
    .map(
      (g) => `
        <tr>
          <td><span class="swatch" style="background:${CORES_GRUPO[g.grupo]}"></span>${nomeGrupo(data.k, g.grupo)}</td>
          <td>${g.janelas}</td>
          <td>${fmt(g.media_co2)}</td>
          <td>${fmt(g.desvio_medio)}</td>
          <td>${fmt(g.pct_ocupada, 0)}%</td>
        </tr>`
    )
    .join("");
}

async function populateDaySelect() {
  const days = await getJSON("/readings/days");
  const select = document.getElementById("day-select");

  select.innerHTML = days
    .map((d) => `<option value="${d}">${d}</option>`)
    .join("");

  select.addEventListener("change", () => renderDayChart(select.value));

  // Seletor próprio da estatística por hora: "todos os dias" + cada dia coletado
  const hourlySelect = document.getElementById("hourly-day-select");
  hourlySelect.innerHTML =
    `<option value="todos">Todos os dias (${days.length})</option>` +
    days.map((d) => `<option value="${d}">${d}</option>`).join("");
  hourlySelect.addEventListener("change", () => renderHourly(hourlySelect.value));

  return days;
}

async function init() {
  checkHealth();
  setInterval(checkHealth, 15000);

  try {
    const [summary, daily, weekRows, peaks, days] = await Promise.all([
      getJSON("/stats/summary"),
      getJSON("/stats/daily"),
      getJSON("/readings?limite=20000"),
      getJSON("/peaks"),
      populateDaySelect(),
    ]);

    allPeaks = peaks;

    const kSelect = document.getElementById("k-select");
    kSelect.addEventListener("change", () => renderClusters(Number(kSelect.value)));
    renderClusters(Number(kSelect.value));

    renderCards(summary);
    renderDailyChart(daily);
    renderWeekChart(weekRows);
    renderPeaksTable(peaks);

    if (days.length > 0) {
      document.getElementById("day-select").value = days[0];
      renderDayChart(days[0]);
    }
  } catch (err) {
    console.error(err);
    document.getElementById("summary-cards").innerHTML = `
      <div class="card">
        <div class="label">Erro</div>
        <div class="value" style="color: var(--danger); font-size: 0.95rem;">
          Não foi possível carregar dados da API. Verifique se o Postgres
          está rodando e se o banco foi populado (src/load_to_db.py).
        </div>
      </div>`;
  }
}

function setupSimulateButton() {
  const btn = document.getElementById("btn-simulate");

  btn.addEventListener("click", async () => {
    const textoOriginal = btn.textContent;

    btn.disabled = true;
    btn.textContent = "Reprocessando… (pode levar alguns segundos)";

    try {
      await postJSON("/simulate");
      // Recarrega a página inteira: mais simples e evita duplicar os
      // listeners que init() registra (ex.: o <select> de dias).
      window.location.reload();
    } catch (err) {
      console.error(err);
      alert(
        "Não foi possível reprocessar o dataset.\n\n" + err.message
      );
      btn.disabled = false;
      btn.textContent = textoOriginal;
    }
  });
}

setupSimulateButton();
init();
