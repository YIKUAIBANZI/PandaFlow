import { buildDemoViewModel } from "/demo/assets/view-model.js";


const scenarioNotes = {
  normal_all_skills: {
    index: "A",
    note: "失物咨询、科普回答与运营复盘依次完成。",
  },
  heat_replan: {
    index: "B",
    note: "合成高温触发动物福利约束，并重新规划路线。",
  },
  human_escalation: {
    index: "C",
    note: "走失事件立即阻断普通游览流程并转人工。",
  },
  live_current_weather: {
    index: "D",
    note: "主动读取当天网格天气；失败时使用固定安全回退。",
  },
};

const statusSymbols = {
  ok: "✓",
  degraded: "△",
  escalated: "!",
  rejected: "×",
  "needs-input": "?",
  unknown: "○",
};

const skillLabels = {
  "visitor-policy-check": "预约与入园核验",
  "accessible-itinerary-planner": "无障碍路线规划",
  "welfare-risk-dispatcher": "动物福利风险调度",
  "incident-triage-dispatch": "现场事件分诊",
  "panda-knowledge-guard": "熊猫知识守卫",
  "operations-review": "运营复盘",
};

const elements = {
  startDemo: document.querySelector("#start-demo"),
  catalogStatus: document.querySelector("#catalog-status"),
  scenarioList: document.querySelector("#scenario-list"),
  runScenario: document.querySelector("#run-scenario"),
  decisionResult: document.querySelector("#decision-result"),
  resultEmpty: document.querySelector("#result-empty"),
  resultContent: document.querySelector("#result-content"),
  statusBanner: document.querySelector("#status-banner"),
  statusSymbol: document.querySelector("#status-symbol"),
  statusLabel: document.querySelector("#status-label"),
  statusCode: document.querySelector("#status-code"),
  resultHeadline: document.querySelector("#result-headline"),
  scenarioCaption: document.querySelector("#scenario-caption"),
  scopeNote: document.querySelector("#scope-note"),
  routeSection: document.querySelector("#route-section"),
  routeVerdict: document.querySelector("#route-verdict"),
  initialRoute: document.querySelector("#initial-route"),
  initialRouteSummary: document.querySelector("#initial-route-summary"),
  finalRoute: document.querySelector("#final-route"),
  finalRouteSummary: document.querySelector("#final-route-summary"),
  removedRoute: document.querySelector("#removed-route"),
  removedNodeList: document.querySelector("#removed-node-list"),
  weatherSection: document.querySelector("#weather-section"),
  weatherKind: document.querySelector("#weather-kind"),
  weatherFacts: document.querySelector("#weather-facts"),
  weatherAttribution: document.querySelector("#weather-attribution"),
  incidentSection: document.querySelector("#incident-section"),
  incidentPriority: document.querySelector("#incident-priority"),
  incidentFacts: document.querySelector("#incident-facts"),
  incidentActions: document.querySelector("#incident-actions"),
  knowledgeSection: document.querySelector("#knowledge-section"),
  knowledgeStatus: document.querySelector("#knowledge-status"),
  knowledgeAnswer: document.querySelector("#knowledge-answer"),
  evidenceEmpty: document.querySelector("#evidence-empty"),
  evidenceContent: document.querySelector("#evidence-content"),
  timelineList: document.querySelector("#timeline-list"),
  reviewSummary: document.querySelector("#review-summary"),
  evidenceList: document.querySelector("#evidence-list"),
  rawJson: document.querySelector("#raw-json"),
};

let scenarios = [];
let selectedScenarioId = null;


function textNode(tag, text, className = null) {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) {
    node.className = className;
  }
  return node;
}


function replaceText(parent, value) {
  parent.replaceChildren(document.createTextNode(value ?? "—"));
}


function setSelectedScenario(id) {
  selectedScenarioId = id;
  for (const button of elements.scenarioList.querySelectorAll("button")) {
    const selected = button.dataset.scenarioId === id;
    button.setAttribute("aria-pressed", String(selected));
    button.dataset.selected = String(selected);
  }
  elements.runScenario.disabled = false;
}


function renderScenarioCatalog(catalog) {
  scenarios = Array.isArray(catalog.scenarios) ? catalog.scenarios : [];
  elements.scenarioList.replaceChildren();

  for (const scenario of scenarios) {
    const note = scenarioNotes[scenario.id] ?? { index: "?", note: "固定演示场景" };
    const button = document.createElement("button");
    button.type = "button";
    button.className = "scenario-card";
    button.dataset.scenarioId = scenario.id;
    button.dataset.selected = "false";
    button.setAttribute("aria-pressed", "false");
    button.append(
      textNode("span", note.index, "scenario-index"),
      textNode("strong", scenario.title),
      textNode("span", note.note, "scenario-note"),
    );
    button.addEventListener("click", () => setSelectedScenario(scenario.id));
    elements.scenarioList.append(button);
  }

  if (scenarios.length === 0) {
    throw new Error("场景目录为空。请检查后端资源后重试。");
  }
  setSelectedScenario(scenarios[0].id);
  replaceText(elements.catalogStatus, `已加载 ${scenarios.length} 个固定场景。选择后主动运行。`);
}


function renderRouteList(target, route, emptyText) {
  target.replaceChildren();
  if (route.length === 0) {
    target.append(textNode("li", emptyText, "route-empty"));
    return;
  }
  route.forEach((stop, index) => {
    const item = document.createElement("li");
    item.append(
      textNode("span", String(index + 1), "route-number"),
      textNode("strong", stop.label),
    );
    if (stop.arrivalMinutes !== null) {
      item.append(textNode("span", `约 ${stop.arrivalMinutes} 分钟到达`, "route-time"));
    }
    if (stop.dwellMinutes > 0) {
      item.append(textNode("span", `停留 ${stop.dwellMinutes} 分钟`, "route-time"));
    }
    target.append(item);
  });
}


function renderRoutes(model) {
  const hasRoutes = model.initialRoute.length > 0 || model.finalRoute.length > 0;
  elements.routeSection.hidden = !hasRoutes;
  if (!hasRoutes) {
    return;
  }
  renderRouteList(elements.initialRoute, model.initialRoute, "没有初始路线");
  renderRouteList(elements.finalRoute, model.finalRoute, "没有最终路线");
  replaceText(
    elements.initialRouteSummary,
    model.initialTotalMinutes === null ? "总用时未提供" : `游览段总用时 ${model.initialTotalMinutes} 分钟`,
  );
  replaceText(
    elements.finalRouteSummary,
    model.finalTotalMinutes === null ? "总用时未提供" : `游览段总用时 ${model.finalTotalMinutes} 分钟`,
  );
  replaceText(elements.routeVerdict, model.replanned ? "已重新规划" : "路线保持不变");
  elements.removedNodeList.replaceChildren();
  elements.removedRoute.hidden = model.removedNodes.length === 0;
  for (const stop of model.removedNodes) {
    elements.removedNodeList.append(textNode("li", `${stop.label}：已避开`));
  }
}


function addFact(list, label, value) {
  if (value === null || value === undefined || value === "") {
    return;
  }
  const group = document.createElement("div");
  group.append(textNode("dt", label), textNode("dd", String(value)));
  list.append(group);
}


function renderWeather(weather) {
  elements.weatherSection.hidden = !weather;
  if (!weather) {
    return;
  }
  replaceText(elements.weatherKind, weather.label);
  elements.weatherFacts.replaceChildren();
  addFact(elements.weatherFacts, "温度", weather.temperature === null ? null : `${weather.temperature} °C`);
  addFact(elements.weatherFacts, "体感", weather.apparentTemperature === null ? null : `${weather.apparentTemperature} °C`);
  addFact(elements.weatherFacts, "降水", weather.precipitation === null ? null : `${weather.precipitation} mm`);
  addFact(elements.weatherFacts, "风速", weather.windSpeed === null ? null : `${weather.windSpeed} km/h`);
  addFact(elements.weatherFacts, "观测时间", weather.observedAt);
  addFact(elements.weatherFacts, "抓取时间", weather.fetchedAt);

  elements.weatherAttribution.replaceChildren();
  if (weather.kind === "live" && weather.attributionUrl === "https://open-meteo.com/") {
    const link = document.createElement("a");
    link.href = weather.attributionUrl;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = weather.attribution ?? "Weather data by Open-Meteo.com";
    elements.weatherAttribution.append(link);
  } else {
    replaceText(elements.weatherAttribution, weather.attribution ?? "PandaFlow 演示天气");
  }
}


function renderIncident(incident) {
  elements.incidentSection.hidden = !incident;
  if (!incident) {
    return;
  }
  replaceText(elements.incidentPriority, incident.priority ?? "待人工判断");
  elements.incidentFacts.replaceChildren();
  addFact(elements.incidentFacts, "事件类别", incident.category);
  addFact(elements.incidentFacts, "负责岗位", incident.responsibleRole);
  addFact(elements.incidentFacts, "处置状态", incident.dispatchStatus === "draft" ? "仅生成草稿" : incident.dispatchStatus);
  addFact(elements.incidentFacts, "是否已发送", incident.sent ? "是" : "否（sent=false）");
  elements.incidentActions.replaceChildren();
  for (const action of incident.actions) {
    elements.incidentActions.append(textNode("li", action));
  }
}


function renderKnowledge(knowledge) {
  elements.knowledgeSection.hidden = !knowledge;
  if (!knowledge) {
    return;
  }
  replaceText(elements.knowledgeStatus, knowledge.status);
  replaceText(elements.knowledgeAnswer, knowledge.answer ?? "当前来源不足，未生成回答。");
}


function renderTimeline(records) {
  elements.timelineList.replaceChildren();
  if (records.length === 0) {
    elements.timelineList.append(textNode("li", "没有可展示的调用记录。", "timeline-empty"));
    return;
  }
  records.forEach((record, index) => {
    const item = document.createElement("li");
    item.dataset.tone = record.status ?? "unknown";
    item.append(
      textNode("span", String(index + 1), "timeline-index"),
      textNode("strong", skillLabels[record.skill] ?? record.skill ?? "未知 Skill"),
      textNode("span", record.status ?? "unknown", "timeline-status"),
    );
    elements.timelineList.append(item);
  });
  const reviewItem = document.createElement("li");
  reviewItem.dataset.tone = "review";
  reviewItem.append(
    textNode("span", String(records.length + 1), "timeline-index"),
    textNode("strong", "运营复盘"),
    textNode("span", "基于以上元数据", "timeline-status"),
  );
  elements.timelineList.append(reviewItem);
}


function renderReview(review) {
  elements.reviewSummary.replaceChildren();
  if (!review) {
    elements.reviewSummary.append(textNode("p", "本次没有可展示的复盘结果。"));
    return;
  }
  const calls = textNode("strong", String(review.total_calls ?? 0));
  const summary = document.createElement("p");
  summary.append(calls, document.createTextNode(" 次实际 Skill 调用被纳入复盘。"));
  elements.reviewSummary.append(summary);

  const counts = review.skill_counts && typeof review.skill_counts === "object"
    ? Object.entries(review.skill_counts)
    : [];
  if (counts.length > 0) {
    const list = document.createElement("ul");
    for (const [skill, count] of counts) {
      list.append(textNode("li", `${skillLabels[skill] ?? skill} × ${count}`));
    }
    elements.reviewSummary.append(list);
  }
}


function renderEvidence(evidence) {
  elements.evidenceList.replaceChildren();
  if (evidence.length === 0) {
    elements.evidenceList.append(textNode("li", "没有额外的来源或规则引用。"));
    return;
  }
  for (const item of evidence) {
    const row = document.createElement("li");
    row.dataset.kind = item.kind;
    const value = item.url ? document.createElement("a") : document.createElement("span");
    value.className = "evidence-value";
    value.textContent = item.label;
    if (item.url) {
      value.href = item.url;
      value.target = "_blank";
      value.rel = "noopener noreferrer";
    }
    row.append(
      textNode("span", item.scope, "evidence-scope"),
      value,
    );
    elements.evidenceList.append(row);
  }
}


function renderResult(model, scenario) {
  elements.resultEmpty.hidden = true;
  elements.resultContent.hidden = false;
  elements.evidenceEmpty.hidden = true;
  elements.evidenceContent.hidden = false;

  elements.statusBanner.dataset.tone = model.tone;
  if (model.tone === "escalated") {
    elements.statusBanner.setAttribute("role", "alert");
  } else {
    elements.statusBanner.removeAttribute("role");
  }
  replaceText(elements.statusSymbol, statusSymbols[model.tone] ?? statusSymbols.unknown);
  replaceText(elements.statusLabel, model.statusLabel);
  replaceText(elements.statusCode, model.status);
  replaceText(elements.resultHeadline, model.headline);
  replaceText(elements.scenarioCaption, scenario?.title ?? "固定演示场景");
  replaceText(elements.scopeNote, model.scopeNote);

  renderRoutes(model);
  renderWeather(model.weather);
  renderIncident(model.incident);
  renderKnowledge(model.knowledge);
  renderTimeline(model.executionRecords);
  renderReview(model.review);
  renderEvidence(model.evidence);
  replaceText(elements.rawJson, JSON.stringify(model.raw, null, 2));
}


function renderRequestError(message) {
  elements.resultEmpty.hidden = true;
  elements.resultContent.hidden = false;
  elements.evidenceEmpty.hidden = false;
  elements.evidenceContent.hidden = true;
  elements.statusBanner.dataset.tone = "escalated";
  elements.statusBanner.setAttribute("role", "alert");
  replaceText(elements.statusSymbol, "!");
  replaceText(elements.statusLabel, "请求未完成");
  replaceText(elements.statusCode, "request_error");
  replaceText(elements.resultHeadline, message);
  replaceText(elements.scenarioCaption, "你可以保持当前场景并重试。");
  elements.routeSection.hidden = true;
  elements.weatherSection.hidden = true;
  elements.incidentSection.hidden = true;
  elements.knowledgeSection.hidden = true;
}


async function loadScenarios() {
  try {
    const response = await fetch("/api/v1/demo/scenarios");
    if (!response.ok) {
      throw new Error("场景目录暂时不可用。请检查后端后重试。");
    }
    renderScenarioCatalog(await response.json());
  } catch (error) {
    replaceText(elements.catalogStatus, error instanceof Error ? error.message : "场景目录加载失败。");
    elements.catalogStatus.setAttribute("role", "alert");
  }
}


async function runSelectedScenario() {
  const scenario = scenarios.find((item) => item.id === selectedScenarioId);
  if (!scenario) {
    return;
  }

  elements.decisionResult.setAttribute("aria-busy", "true");
  elements.runScenario.disabled = true;
  replaceText(elements.runScenario, "正在运行安全流程……");
  try {
    const response = await fetch("/api/v1/demo/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(scenario.request),
    });
    if (!response.ok) {
      throw new Error("后端未接受这个演示请求。请检查服务后重试。");
    }
    const body = await response.json();
    renderResult(buildDemoViewModel(body), scenario);
  } catch (error) {
    renderRequestError(error instanceof Error ? error.message : "场景运行失败。请重试。");
  } finally {
    elements.decisionResult.setAttribute("aria-busy", "false");
    elements.runScenario.disabled = false;
    replaceText(elements.runScenario, "运行所选场景");
  }
}


elements.startDemo.addEventListener("click", () => {
  elements.scenarioList.querySelector("button")?.focus();
});
elements.runScenario.addEventListener("click", runSelectedScenario);

loadScenarios();
