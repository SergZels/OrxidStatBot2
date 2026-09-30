"use strict";

const MONTHS = [
  "Січень", "Лютий", "Березень", "Квітень", "Травень", "Червень",
  "Липень", "Серпень", "Вересень", "Жовтень", "Листопад", "Грудень"
];
const MONTHS_GENITIVE = [
  "січня", "лютого", "березня", "квітня", "травня", "червня",
  "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"
];
const SHORT_MONTHS = ["Січ", "Лют", "Бер", "Кві", "Тра", "Чер", "Лип", "Сер", "Вер", "Жов", "Лис", "Гру"];
const SEASON_MONTHS = ["Жов", "Лис", "Гру", "Січ", "Лют", "Бер", "Кві"];
const OFFSEASON_MONTHS = ["Тра", "Чер", "Лип", "Сер", "Вер"];
const number = new Intl.NumberFormat("uk-UA", { maximumFractionDigits: 2 });
const decimal = new Intl.NumberFormat("uk-UA", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const baseSelect = document.querySelector("#base-year");
const compareSelect = document.querySelector("#compare-year");
const errorBox = document.querySelector("#report-error");
let requestId = 0;

const cash = value => `${number.format(value)} ₴`;
const signedCash = value => `${value > 0 ? "+" : ""}${cash(value)}`;
const signedPercent = value => value == null ? "—" : `${value > 0 ? "+" : ""}${decimal.format(value)}%`;
const tone = value => value > 0 ? "tone-positive" : value < 0 ? "tone-negative" : "tone-neutral";
const dateLabel = iso => iso.split("-").reverse().join(".");

function shortValue(value) {
  if (value >= 1_000_000) return `${decimal.format(value / 1_000_000)} млн`;
  if (value >= 10_000) return `${decimal.format(value / 1_000)} тис.`;
  return number.format(value);
}

function grid(maximum) {
  let output = "";
  for (let i = 0; i <= 4; i++) {
    const y = 245 - i * 48;
    output += `<line class="gridline" x1="70" y1="${y}" x2="925" y2="${y}"></line>`;
    output += `<text class="axis-label" x="57" y="${y + 4}" text-anchor="end">${shortValue(maximum * i / 4)}</text>`;
  }
  return output;
}

function drawBars(svgId, values, label, barClass) {
  const svg = document.querySelector(svgId);
  if (!values.length) {
    svg.innerHTML = '<text class="axis-label" x="470" y="150" text-anchor="middle">Немає даних</text>';
    return;
  }
  const max = Math.max(1, ...values.map(item => item.total));
  const step = 830 / values.length;
  const width = Math.min(72, step * .49);
  let output = grid(max);
  values.forEach((item, index) => {
    const center = 85 + step * (index + .5);
    const height = item.total / max * 192;
    const cls = item.status === "full" ? barClass : "bar-incomplete";
    output += `<rect class="${cls}" x="${center - width / 2}" y="${245 - height}" width="${width}" height="${height}" rx="7"><title>${label(item)}: ${cash(item.total)}</title></rect>`;
    output += `<text class="axis-label" x="${center}" y="272" text-anchor="middle">${label(item)}</text>`;
    if (item.status !== "full") output += `<text class="axis-label" x="${center}" y="289" text-anchor="middle">неповний</text>`;
  });
  svg.innerHTML = output;
}

function createText(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = text;
  return element;
}

function growthText(period) {
  if (period.change == null) return "Без зіставлення з попереднім повним періодом";
  return `${signedCash(period.change)} · ${signedPercent(period.percent)}`;
}

function renderPeriods(periods, chartId, listId, label, barClass, monthLabels, miniClass) {
  drawBars(chartId, periods, label, barClass);
  const list = document.querySelector(listId);
  list.replaceChildren();
  periods.forEach(period => {
    const card = createText("article", "season-card", "");
    const top = createText("div", "season-card-top", "");
    top.append(createText("span", "season-card-title", label(period)));
    const status = createText("span", `period-status ${period.status === "full" ? "" : "partial"}`,
      period.status === "full" ? "Завершено" : period.status === "current" ? "Триває" : "Початок даних");
    top.append(status);
    card.append(top, createText("strong", "", cash(period.total)));
    card.append(createText("span", `growth ${period.change == null ? "tone-neutral" : tone(period.change)}`, growthText(period)));
    const mini = createText("div", `season-mini ${miniClass}`, "");
    const peak = Math.max(1, ...period.months);
    period.months.forEach(value => {
      const bar = document.createElement("span");
      bar.style.height = `${Math.max(3, value / peak * 38)}px`;
      bar.title = cash(value);
      mini.append(bar);
    });
    card.append(mini);
    const labels = createText("div", "season-month-labels", "");
    monthLabels.forEach(value => labels.append(createText("span", "", value)));
    card.append(labels);
    list.append(card);
  });
}

function renderYears(years) {
  drawBars("#annual-chart", years, item => item.year, "bar-annual");
  const list = document.querySelector("#year-list");
  list.replaceChildren();
  const max = Math.max(1, ...years.map(item => item.total));
  years.forEach(year => {
    const row = createText("div", "year-row", "");
    row.append(createText("strong", "", String(year.year)));
    const details = createText("div", "year-details", "");
    const track = createText("div", `year-track ${year.status === "full" ? "" : "partial"}`, "");
    for (const [key, className] of [["season_total", "year-season-fill"], ["offseason_total", "year-offseason-fill"]]) {
      const fill = createText("div", className, "");
      fill.style.width = `${year[key] / max * 100}%`;
      track.append(fill);
    }
    const split = createText("div", "year-split", "");
    split.append(createText("span", "", `Сезонні місяці ${cash(year.season_total)}`));
    split.append(createText("span", "", `Міжсезоння ${cash(year.offseason_total)}`));
    details.append(track, split);
    row.append(details, createText("span", "year-total", cash(year.total)));
    const average = createText("span", "year-average", "");
    average.append(createText("small", "", "СЕРЕДНЯ / МІСЯЦЬ"));
    average.append(createText("strong", "", cash(year.average_monthly)));
    average.title = `Місяців у розрахунку: ${year.covered_months}`;
    row.append(average);
    row.append(createText("span", `year-change ${year.change == null ? "tone-neutral" : tone(year.change)}`,
      year.change == null ? year.status === "full" ? "—" : "Неповний" : signedPercent(year.percent)));
    list.append(row);
  });
}

function drawComparison(comparison) {
  const svg = document.querySelector("#compare-chart");
  if (!comparison.available) {
    svg.innerHTML = '<text class="axis-label" x="470" y="150" text-anchor="middle">Для цих років немає спільного проміжку дат</text>';
    return;
  }
  const window = comparison.window;
  const values = comparison.months.filter(item =>
    item.month >= window.start_month && item.month <= window.end_month);
  const max = Math.max(1, ...values.flatMap(item => [item.base, item.compare]));
  const x = index => values.length === 1 ? 490 : 90 + index * 815 / (values.length - 1);
  const y = value => 245 - value / max * 192;
  let output = grid(max);
  for (const [key, cls] of [["base", "base"], ["compare", "compare"]]) {
    const points = values.map((item, index) => [x(index), y(item[key])]);
    const line = points.map(([px, py], index) => `${index ? "L" : "M"}${px} ${py}`).join(" ");
    const area = `${line} L${points.at(-1)[0]} 245 L${points[0][0]} 245 Z`;
    output += `<path class="chart-area-${cls}" d="${area}"></path>`;
    output += `<path class="chart-line-${cls}" d="${line}"></path>`;
    points.forEach(([px, py], index) => {
      output += `<circle class="chart-point-${cls}" cx="${px}" cy="${py}" r="6"><title>${MONTHS[values[index].month - 1]} ${key === "base" ? comparison.base_year : comparison.compare_year}: ${cash(values[index][key])}</title></circle>`;
    });
  }
  values.forEach((item, index) => {
    output += `<text class="axis-label" x="${x(index)}" y="271" text-anchor="middle">${SHORT_MONTHS[item.month - 1]}</text>`;
  });
  svg.innerHTML = output;
}

function renderComparison(comparison) {
  const window = comparison.window;
  const period = `${window.start_day} ${MONTHS_GENITIVE[window.start_month - 1]} — ${window.end_day} ${MONTHS_GENITIVE[window.end_month - 1]}`;
  document.querySelector("#compare-period").textContent = comparison.available
    ? `Однаковий проміжок для обох років: ${period}. Неповні місяці обрізані по однаковий день.`
    : "Для обраних років немає спільного проміжку дат.";
  document.querySelector("#base-total-label").textContent = `${comparison.base_year} · базовий рік`;
  document.querySelector("#compare-total-label").textContent = `${comparison.compare_year} · рік порівняння`;
  document.querySelector("#base-total").textContent = comparison.available ? cash(comparison.base_total) : "—";
  document.querySelector("#compare-total").textContent = comparison.available ? cash(comparison.compare_total) : "—";
  const delta = document.querySelector("#compare-delta");
  delta.textContent = comparison.available ? signedCash(comparison.change) : "—";
  delta.className = comparison.available ? tone(comparison.change) : "tone-neutral";
  const percent = document.querySelector("#compare-percent");
  percent.textContent = comparison.available ? signedPercent(comparison.percent) : "—";
  percent.className = delta.className;
  document.querySelector("#legend-base").textContent = String(comparison.base_year);
  document.querySelector("#legend-compare").textContent = String(comparison.compare_year);
  document.querySelector("#table-base").textContent = String(comparison.base_year);
  document.querySelector("#table-compare").textContent = String(comparison.compare_year);
  drawComparison(comparison);
  const tbody = document.querySelector("#comparison-rows");
  tbody.replaceChildren();
  if (!comparison.available) return;
  comparison.months
    .filter(item => item.month >= window.start_month && item.month <= window.end_month)
    .forEach(item => {
      const row = document.createElement("tr");
      const change = item.compare - item.base;
      row.append(
        createText("td", "", MONTHS[item.month - 1]),
        createText("td", "", cash(item.base)),
        createText("td", "", cash(item.compare)),
        createText("td", tone(change), signedCash(change))
      );
      tbody.append(row);
    });
}

function populateSelectors(years, comparison) {
  const yearValues = years.map(item => item.year);
  if (baseSelect.options.length !== yearValues.length) {
    for (const select of [baseSelect, compareSelect]) {
      select.replaceChildren();
      yearValues.forEach(year => {
        const option = document.createElement("option");
        option.value = String(year);
        option.textContent = String(year);
        select.append(option);
      });
    }
  }
  baseSelect.value = String(comparison.base_year);
  compareSelect.value = String(comparison.compare_year);
}

function render(data) {
  populateSelectors(data.years, data.comparison);
  document.querySelector("#data-note").textContent =
    `Дані з ${dateLabel(data.first_record)} до ${dateLabel(data.as_of)}. Виручка = оборот ÷ 2, до вирахування витрат; неповні періоди позначені.`;
  renderPeriods(data.seasons, "#season-chart", "#season-list", item => item.label,
    "bar-season", SEASON_MONTHS, "");
  renderPeriods(data.offseasons, "#offseason-chart", "#offseason-list", item => item.year,
    "bar-offseason", OFFSEASON_MONTHS, "offseason-mini");
  renderYears(data.years);
  renderComparison(data.comparison);
  const fullSeasons = data.seasons.filter(item => item.status === "full");
  const season = fullSeasons.at(-1);
  const fullOffseasons = data.offseasons.filter(item => item.status === "full");
  const offseason = fullOffseasons.at(-1);
  const fullYears = data.years.filter(item => item.status === "full");
  const year = fullYears.at(-1);
  if (season) {
    document.querySelector("#highlight-season-total").textContent = cash(season.total);
    document.querySelector("#highlight-season-label").textContent = `Сезон ${season.label}`;
    const change = document.querySelector("#highlight-season-change");
    change.textContent = growthText(season);
    change.className = `highlight-change ${season.change == null ? "tone-neutral" : tone(season.change)}`;
  }
  if (offseason) {
    document.querySelector("#highlight-offseason-total").textContent = cash(offseason.total);
    document.querySelector("#highlight-offseason-label").textContent = `Міжсезоння ${offseason.year}`;
    const change = document.querySelector("#highlight-offseason-change");
    change.textContent = growthText(offseason);
    change.className = `highlight-change ${offseason.change == null ? "tone-neutral" : tone(offseason.change)}`;
  }
  if (year) {
    document.querySelector("#highlight-year-total").textContent = cash(year.total);
    document.querySelector("#highlight-year-label").textContent = `Календарний ${year.year} рік`;
    const change = document.querySelector("#highlight-year-change");
    change.textContent = growthText(year);
    change.className = `highlight-change ${year.change == null ? "tone-neutral" : tone(year.change)}`;
  }
  const comparison = data.comparison;
  document.querySelector("#highlight-compare-delta").textContent =
    comparison.available ? signedCash(comparison.change) : "—";
  document.querySelector("#highlight-compare-label").textContent =
    `${comparison.compare_year} проти ${comparison.base_year}`;
  const compareChange = document.querySelector("#highlight-compare-percent");
  compareChange.textContent = comparison.available ? signedPercent(comparison.percent) : "Немає спільного періоду";
  compareChange.className = `highlight-change ${comparison.available ? tone(comparison.change) : "tone-neutral"}`;
  document.querySelector("#reports-updated").textContent =
    `Оновлено ${new Intl.DateTimeFormat("uk-UA", { dateStyle: "short", timeStyle: "short" }).format(new Date())}`;
}

async function load() {
  const id = ++requestId;
  errorBox.hidden = true;
  const params = baseSelect.value && compareSelect.value
    ? `?base=${encodeURIComponent(baseSelect.value)}&compare=${encodeURIComponent(compareSelect.value)}`
    : "";
  try {
    const response = await fetch(`/api/reports${params}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (id === requestId) render(data);
  } catch (error) {
    if (id === requestId) {
      errorBox.textContent = "Не вдалося завантажити звіт. Спробуйте оновити сторінку.";
      errorBox.hidden = false;
    }
  }
}

function selectionChanged(changed) {
  if (baseSelect.value === compareSelect.value) {
    const other = changed === baseSelect ? compareSelect : baseSelect;
    const alternatives = [...other.options].map(option => option.value)
      .filter(value => value !== changed.value);
    other.value = alternatives.at(-1);
  }
  load();
}

baseSelect.addEventListener("change", () => selectionChanged(baseSelect));
compareSelect.addEventListener("change", () => selectionChanged(compareSelect));
load();
