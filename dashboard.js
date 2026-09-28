"use strict";

const months = [
  "Січень", "Лютий", "Березень", "Квітень", "Травень", "Червень",
  "Липень", "Серпень", "Вересень", "Жовтень", "Листопад", "Грудень"
];
const monthShort = ["Січ", "Лют", "Бер", "Кві", "Тра", "Чер", "Лип", "Сер", "Вер", "Жов", "Лис", "Гру"];
const money = new Intl.NumberFormat("uk-UA", { maximumFractionDigits: 0 });
const monthSelect = document.querySelector("#month");
const yearSelect = document.querySelector("#year");
const errorBox = document.querySelector("#error");
let requestNumber = 0;

months.forEach((name, index) => {
  const option = document.createElement("option");
  option.value = String(index + 1);
  option.textContent = name;
  monthSelect.append(option);
});

function currency(value) {
  return `${money.format(value)} ₴`;
}

function shortNumber(value) {
  if (value >= 1_000_000) return `${money.format(value / 1_000_000)} млн`;
  if (value >= 10_000) return `${money.format(value / 1_000)} тис.`;
  return money.format(value);
}

function chartGrid(maximum) {
  let lines = "";
  for (let i = 0; i <= 4; i++) {
    const y = 230 - i * 45;
    const value = maximum * i / 4;
    lines += `<line class="gridline" x1="58" y1="${y}" x2="886" y2="${y}"></line>`;
    lines += `<text class="axis-label" x="47" y="${y + 4}" text-anchor="end">${shortNumber(value)}</text>`;
  }
  return lines;
}

function drawDaily(days) {
  const svg = document.querySelector("#daily-chart");
  const hasData = days.some(day => day.revenue || day.expenses);
  if (!hasData) {
    svg.innerHTML = '<text class="axis-label" x="450" y="145" text-anchor="middle">Немає записів за цей місяць</text>';
    return;
  }
  const maximum = Math.max(1, ...days.flatMap(day => [day.revenue, day.expenses]));
  const step = 822 / days.length;
  const barWidth = Math.max(4, Math.min(10, step * .32));
  let output = chartGrid(maximum);
  days.forEach((day, index) => {
    const center = 58 + step * (index + .5);
    const earnedHeight = day.revenue / maximum * 180;
    const spentHeight = day.expenses / maximum * 180;
    output += `<rect class="bar-revenue" x="${center - barWidth - 1}" y="${230 - earnedHeight}" width="${barWidth}" height="${earnedHeight}" rx="3"><title>${day.day}: виручка ${currency(day.revenue)}</title></rect>`;
    output += `<rect class="bar-expenses" x="${center + 1}" y="${230 - spentHeight}" width="${barWidth}" height="${spentHeight}" rx="3"><title>${day.day}: витрати ${currency(day.expenses)}</title></rect>`;
    if (day.day === 1 || day.day % 5 === 0 || index === days.length - 1) {
      output += `<text class="axis-label" x="${center}" y="254" text-anchor="middle">${day.day}</text>`;
    }
  });
  svg.innerHTML = output;
}

function drawYearly(values) {
  const svg = document.querySelector("#year-chart");
  const hasData = values.some(month => month.revenue || month.expenses);
  if (!hasData) {
    svg.innerHTML = '<text class="axis-label" x="450" y="145" text-anchor="middle">Немає записів за цей рік</text>';
    return;
  }
  const maximum = Math.max(1, ...values.flatMap(month => [month.revenue, month.expenses]));
  const step = 822 / 12;
  const barWidth = 19;
  let output = chartGrid(maximum);
  values.forEach((month, index) => {
    const center = 58 + step * (index + .5);
    const earnedHeight = month.revenue / maximum * 180;
    const spentHeight = month.expenses / maximum * 180;
    output += `<rect class="bar-revenue" x="${center - barWidth - 2}" y="${230 - earnedHeight}" width="${barWidth}" height="${earnedHeight}" rx="4"><title>${months[index]}: виручка ${currency(month.revenue)}</title></rect>`;
    output += `<rect class="bar-expenses" x="${center + 2}" y="${230 - spentHeight}" width="${barWidth}" height="${spentHeight}" rx="4"><title>${months[index]}: витрати ${currency(month.expenses)}</title></rect>`;
    output += `<text class="axis-label" x="${center}" y="254" text-anchor="middle">${monthShort[index]}</text>`;
  });
  svg.innerHTML = output;
}

function drawRecent(entries) {
  const list = document.querySelector("#recent-list");
  list.replaceChildren();
  if (!entries.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "За цей місяць витрат ще немає.";
    list.append(empty);
    return;
  }
  entries.forEach(entry => {
    const row = document.createElement("div");
    row.className = "recent-item";
    const icon = document.createElement("div");
    icon.className = "recent-icon";
    icon.textContent = "↘";
    const text = document.createElement("div");
    text.className = "recent-text";
    const title = document.createElement("strong");
    title.textContent = entry.description;
    title.title = entry.description;
    const date = document.createElement("small");
    date.textContent = entry.date.split("-").reverse().join(".");
    text.append(title, date);
    const amount = document.createElement("strong");
    amount.className = "recent-amount";
    amount.textContent = currency(entry.cash);
    row.append(icon, text, amount);
    list.append(row);
  });
}

function render(data) {
  const { summary, period } = data;
  monthSelect.value = String(period.month);
  if (yearSelect.options.length !== data.years.length) {
    yearSelect.replaceChildren();
    data.years.forEach(year => {
      const option = document.createElement("option");
      option.value = String(year);
      option.textContent = String(year);
      yearSelect.append(option);
    });
  }
  yearSelect.value = String(period.year);
  for (const key of ["revenue", "expenses", "balance", "average"]) {
    document.querySelector(`#${key}`).textContent = currency(summary[key]);
  }
  document.querySelector("#daily-subtitle").textContent = `${months[period.month - 1]} ${period.year} · щоденний огляд`;
  document.querySelector("#donut-balance").textContent = currency(summary.balance);
  document.querySelector("#split-revenue").textContent = currency(summary.revenue);
  document.querySelector("#split-expenses").textContent = currency(summary.expenses);
  document.querySelector("#active-days").textContent = `Днів із виручкою: ${summary.active_days}`;
  document.querySelector("#best-day").textContent = summary.best_day
    ? `Найкращий день: ${summary.best_day.slice(8, 10)}.${summary.best_day.slice(5, 7)}`
    : "Найкращий день: —";
  const total = summary.revenue + summary.expenses;
  const share = total ? summary.revenue / total * 100 : 0;
  const donut = document.querySelector("#donut");
  donut.style.background = total
    ? `conic-gradient(#6de2ba 0% ${share}%, #fc8f9a ${share}% 100%)`
    : "#344258";
  donut.setAttribute("aria-label", `Виручка ${currency(summary.revenue)}, витрати ${currency(summary.expenses)}`);
  drawDaily(data.daily);
  drawYearly(data.monthly);
  drawRecent(data.recent_expenses);
  document.querySelector("#updated-at").textContent =
    `Оновлено ${new Intl.DateTimeFormat("uk-UA", { dateStyle: "short", timeStyle: "short" }).format(new Date())}`;
}

async function load() {
  const currentRequest = ++requestNumber;
  const params = yearSelect.value && monthSelect.value
    ? `?year=${encodeURIComponent(yearSelect.value)}&month=${encodeURIComponent(monthSelect.value)}`
    : "";
  errorBox.hidden = true;
  try {
    const response = await fetch(`/api/stats${params}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (currentRequest === requestNumber) render(data);
  } catch (error) {
    if (currentRequest === requestNumber) {
      errorBox.textContent = "Не вдалося завантажити статистику. Спробуйте оновити сторінку.";
      errorBox.hidden = false;
    }
  }
}

monthSelect.addEventListener("change", load);
yearSelect.addEventListener("change", load);
document.querySelector("#refresh").addEventListener("click", load);
load();
