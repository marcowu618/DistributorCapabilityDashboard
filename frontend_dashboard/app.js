const DIMS = ["专业技术能力", "工作态度与责任心", "学习成长能力", "沟通协助能力", "执行力与结果产出"];
const TECH_DIMS = [
  "性能验证能力", "无忧切换能力", "结果问题解决能力", "风险管理能力",
  "IQC/EQA管理能力", "瑞印课堂-系列课能力", "产品价值优势传递能力", "学术支持&文章合作能力"
];

let rawData = [];
let charts = {};

async function loadData() {
  try {
    const res = await fetch("./data.json", { cache: "no-store" });
    if (!res.ok) {
      throw new Error(`读取 data.json 失败: ${res.status}`);
    }
    return await res.json();
  } catch (e) {
    // file:// 直开或受限环境下 fetch 可能被浏览器拦截
    if (Array.isArray(window.__CSA_DATA__) && window.__CSA_DATA__.length) {
      return window.__CSA_DATA__;
    }
    throw e;
  }
}

function calcFields(rows) {
  return rows.map(r => {
    const techAvg = avg(TECH_DIMS.map(k => Number(r[k] || 0)));
    const total = techAvg * 4 + Number(r["工作态度与责任心"] || 0) * 1 + Number(r["学习成长能力"] || 0) * 2 + Number(r["沟通协助能力"] || 0) * 1.5 + Number(r["执行力与结果产出"] || 0) * 1.5;
    return { ...r, 专业技术能力: round1(techAvg), 评分合计: round1(total) };
  });
}

function setupSelectors(data) {
  const areaSelect = document.getElementById("areaSelect");
  const branchSelect = document.getElementById("branchSelect");
  const personSelect = document.getElementById("personSelect");

  const areas = unique(data.map(x => x["区域"]));
  fillSelect(areaSelect, areas);

  function refreshBranches() {
    const branches = unique(data.filter(x => x["区域"] === areaSelect.value).map(x => x["分公司"]));
    fillSelect(branchSelect, branches);
    refreshPersons();
  }

  function refreshPersons() {
    const persons = data
      .filter(x => x["区域"] === areaSelect.value && x["分公司"] === branchSelect.value)
      .map(x => x["应用专员"]);
    fillSelect(personSelect, persons);
    render();
  }

  areaSelect.onchange = refreshBranches;
  branchSelect.onchange = refreshPersons;
  personSelect.onchange = render;

  refreshBranches();
}

function getContext() {
  const area = document.getElementById("areaSelect").value;
  const branch = document.getElementById("branchSelect").value;
  const person = document.getElementById("personSelect").value;

  const filtered = rawData.filter(x => x["区域"] === area && x["分公司"] === branch);
  const personRow = filtered.find(x => x["应用专员"] === person);
  return { area, branch, filtered, personRow };
}

function render() {
  const { filtered, personRow } = getContext();
  if (!personRow) return;

  setText("totalScore", personRow["评分合计"]);
  setText("kpiTech", personRow["专业技术能力"]);
  setText("kpiAttitude", personRow["工作态度与责任心"]);
  setText("kpiLearning", personRow["学习成长能力"]);
  setText("kpiComm", personRow["沟通协助能力"]);
  setText("kpiExec", personRow["执行力与结果产出"]);

  renderRadar(personRow, filtered);
  renderTechBar(personRow);
  renderLevelPie(filtered);
  renderChannelBar(filtered);
  renderChannelScatter(filtered);
  renderTopTable(filtered);
}

function renderRadar(personRow, filtered) {
  const areaAvg = DIMS.map(k => avg(filtered.map(x => Number(x[k] || 0))));
  const person = DIMS.map(k => Number(personRow[k] || 0));

  charts.radar.setOption({
    tooltip: { trigger: "item" },
    legend: { data: [personRow["应用专员"], "分公司平均"] },
    radar: { indicator: DIMS.map(k => ({ name: k, max: 10 })) },
    series: [{
      type: "radar",
      data: [
        { value: person, name: personRow["应用专员"] },
        { value: areaAvg, name: "分公司平均" }
      ]
    }]
  });
}

function renderTechBar(personRow) {
  const labels = TECH_DIMS.map(s => s.replace("能力", ""));
  const values = TECH_DIMS.map(k => Number(personRow[k] || 0));

  charts.techBar.setOption({
    tooltip: { trigger: "axis" },
    xAxis: { type: "value", max: 10 },
    yAxis: { type: "category", data: labels, inverse: true },
    series: [{ type: "bar", data: values, itemStyle: { color: "#0f8b8d" }, label: { show: true, position: "right" } }]
  });
}

function renderLevelPie(filtered) {
  const m = new Map();
  filtered.forEach(x => m.set(x["能力评级"], (m.get(x["能力评级"]) || 0) + 1));
  const data = [...m.entries()].map(([name, value]) => ({ name, value }));

  charts.levelPie.setOption({
    tooltip: { trigger: "item" },
    series: [{ type: "pie", radius: ["45%", "70%"], data }]
  });
}

function renderChannelBar(filtered) {
  const g = groupBy(filtered, "渠道名称");
  const rows = Object.keys(g).map(name => ({
    name,
    avg: avg(g[name].map(x => Number(x["评分合计"] || 0)))
  })).sort((a, b) => a.avg - b.avg);

  charts.channelBar.setOption({
    tooltip: { trigger: "axis" },
    xAxis: { type: "value", max: 100 },
    yAxis: { type: "category", data: rows.map(x => x.name) },
    series: [{ type: "bar", data: rows.map(x => round1(x.avg)), itemStyle: { color: "#12a4a6" }, label: { show: true, position: "right" } }]
  });
}

function renderChannelScatter(filtered) {
  const g = groupBy(filtered, "渠道名称");
  const rows = Object.keys(g).map(name => {
    const arr = g[name];
    const avgScore = avg(arr.map(x => Number(x["评分合计"] || 0)));
    return { name, headcount: arr.length, avgScore };
  });

  charts.channelScatter.setOption({
    tooltip: { formatter: p => `${p.data.name}<br/>人数: ${p.data.value[0]}<br/>均分: ${round1(p.data.value[1])}` },
    xAxis: { name: "专员人数", type: "value", minInterval: 1 },
    yAxis: { name: "渠道平均分", type: "value", min: 0, max: 100 },
    series: [{
      type: "scatter",
      data: rows.map(r => ({ name: r.name, value: [r.headcount, r.avgScore, r.avgScore] })),
      symbolSize: v => Math.max(10, v[2] / 4),
      itemStyle: { color: "#3a7ca5" }
    }]
  });
}

function renderTopTable(filtered) {
  const top = [...filtered].sort((a, b) => Number(b["评分合计"]) - Number(a["评分合计"])).slice(0, 5);
  const tbody = document.querySelector("#topTable tbody");
  tbody.innerHTML = top.map(x => `
    <tr>
      <td>${x["应用专员"]}</td>
      <td>${x["分公司"]}</td>
      <td>${x["渠道名称"]}</td>
      <td>${round1(Number(x["评分合计"] || 0))}</td>
      <td>${x["能力评级"]}</td>
    </tr>
  `).join("");
}

function initCharts() {
  charts.radar = echarts.init(document.getElementById("radarChart"));
  charts.techBar = echarts.init(document.getElementById("techBarChart"));
  charts.levelPie = echarts.init(document.getElementById("levelPieChart"));
  charts.channelBar = echarts.init(document.getElementById("channelBarChart"));
  charts.channelScatter = echarts.init(document.getElementById("channelScatterChart"));
  window.addEventListener("resize", () => Object.values(charts).forEach(c => c.resize()));
}

function fillSelect(el, arr) {
  el.innerHTML = arr.map(x => `<option value="${x}">${x}</option>`).join("");
}
function setText(id, v) { document.getElementById(id).textContent = round1(Number(v || 0)); }
function unique(arr) { return [...new Set(arr)].filter(Boolean); }
function avg(arr) { return arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0; }
function round1(x) { return Math.round(x * 10) / 10; }
function groupBy(arr, key) {
  return arr.reduce((acc, cur) => {
    const k = cur[key] || "未知";
    (acc[k] = acc[k] || []).push(cur);
    return acc;
  }, {});
}

function mockData() {
  return [
    { 区域: "华东区", 分公司: "上海", 渠道名称: "渠道A", 应用专员: "张三", 能力评级: "A", 性能验证能力: 8, 无忧切换能力: 7.5, 结果问题解决能力: 8, 风险管理能力: 7, "IQC/EQA管理能力": 8.5, "瑞印课堂-系列课能力": 8, 产品价值优势传递能力: 7.5, "学术支持&文章合作能力": 7, 工作态度与责任心: 9, 学习成长能力: 8.5, 沟通协助能力: 8, 执行力与结果产出: 8.5 },
    { 区域: "华东区", 分公司: "上海", 渠道名称: "渠道A", 应用专员: "李四", 能力评级: "B", 性能验证能力: 7, 无忧切换能力: 6.5, 结果问题解决能力: 7, 风险管理能力: 6.5, "IQC/EQA管理能力": 7.5, "瑞印课堂-系列课能力": 7, 产品价值优势传递能力: 6.8, "学术支持&文章合作能力": 6.5, 工作态度与责任心: 8, 学习成长能力: 7.5, 沟通协助能力: 7.2, 执行力与结果产出: 7.8 },
    { 区域: "华东区", 分公司: "南京", 渠道名称: "渠道B", 应用专员: "王五", 能力评级: "A", 性能验证能力: 8.6, 无忧切换能力: 8, 结果问题解决能力: 8.4, 风险管理能力: 7.7, "IQC/EQA管理能力": 8.2, "瑞印课堂-系列课能力": 7.9, 产品价值优势传递能力: 8.1, "学术支持&文章合作能力": 7.8, 工作态度与责任心: 8.8, 学习成长能力: 8.1, 沟通协助能力: 8.3, 执行力与结果产出: 8.4 },
    { 区域: "华南区", 分公司: "广州", 渠道名称: "渠道C", 应用专员: "赵六", 能力评级: "B", 性能验证能力: 6.8, 无忧切换能力: 7.1, 结果问题解决能力: 7, 风险管理能力: 6.9, "IQC/EQA管理能力": 7.2, "瑞印课堂-系列课能力": 6.7, 产品价值优势传递能力: 6.9, "学术支持&文章合作能力": 6.8, 工作态度与责任心: 7.9, 学习成长能力: 7.4, 沟通协助能力: 7.3, 执行力与结果产出: 7.6 }
  ];
}

(async function boot() {
  const rows = await loadData();
  rawData = calcFields(rows);
  initCharts();
  setupSelectors(rawData);
})();
