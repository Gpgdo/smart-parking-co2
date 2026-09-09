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
    { label: "Total de veículos", value: fmt(summary.total_veiculos, 0) },
    { label: "CO₂ médio (ppm)", value: fmt(summary.co2_medio), cls: "accent" },
    { label: "CO₂ máximo (ppm)", value: fmt(summary.co2_maximo), cls: "warn" },
    { label: "Picos de CO₂ detectados", value: fmt(summary.total_picos, 0) },
    { label: "Maior movimento real", value: summary.dia_maior_movimento_real ?? "—" },
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
          label: "Movimentação real (veículos)",
          data: daily.map((d) => d.movimento_real),
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
    // Escalas bem diferentes (veículos x índice de CO₂ acumulado):
    // cada série ganha seu próprio eixo Y para as duas ficarem visíveis.
    options: chartOptions("Veículos", "Índice de atividade (CO₂)"),
  });
}

async function renderDayChart(day) {
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

async function populateDaySelect() {
  const days = await getJSON("/readings/days");
  const select = document.getElementById("day-select");

  select.innerHTML = days
    .map((d) => `<option value="${d}">${d}</option>`)
    .join("");

  select.addEventListener("change", () => renderDayChart(select.value));

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

init();
