const STATUS_META = {
  ok: { label: "演示规则检查通过", tone: "ok" },
  degraded: { label: "已安全降级", tone: "degraded" },
  escalated: { label: "需要人工介入", tone: "escalated" },
  rejected: { label: "未生成安全方案", tone: "rejected" },
  needs_input: { label: "需要补充信息", tone: "needs-input" },
};

const NODE_LABELS = {
  north_gate: "北门",
  panda_nursery: "熊猫幼年园",
  bamboo_grove: "竹林步道",
  science_hall: "熊猫科普馆",
  lake_pavilion: "湖畔休憩亭",
  south_gate: "南门",
};

const SOURCE_META = {
  source_open_meteo_forecast: {
    label: "Open-Meteo 天气 API 文档",
    url: "https://open-meteo.com/en/docs",
  },
  source_open_meteo_license: {
    label: "Open-Meteo 使用条款与署名",
    url: "https://open-meteo.com/en/terms",
  },
  source_panda_base_diet: {
    label: "成都熊猫基地：熊猫知识·进食",
    url: "https://www.panda.org.cn/yd/education/database/kpzs/2025-06-05/8786.html",
  },
  source_base_visitor_service: {
    label: "成都熊猫基地：游客服务",
    url: "https://m.panda.org.cn/cn/service/",
  },
  source_demo_weather_fallback: { label: "PandaFlow 合成天气与固定回退" },
  source_demo_incident_rules: { label: "PandaFlow 合成事件分诊矩阵" },
  source_demo_review_rules: { label: "PandaFlow 执行元数据复盘规则" },
  source_demo_park_graph: { label: "PandaFlow 合成园区图" },
  source_demo_welfare_rules: { label: "PandaFlow 合成福利风险规则" },
};

const RULE_LABELS = {
  rule_accessibility_hard_constraint: "无台阶硬约束",
  rule_time_budget: "游览段时间预算",
  rule_demo_area_closure: "演示区域关闭规则",
  rule_demo_high_heat_outdoor: "演示高温室外节点规则",
  rule_demo_normal_conditions: "演示常规条件规则",
  rule_registered_knowledge_only: "仅回答已登记知识",
};

const NESTED_RESPONSE_KEYS = [
  "policy",
  "initial_itinerary",
  "risk",
  "final_itinerary",
  "incident",
  "knowledge",
  "response",
  "review",
];


export function statusMeta(status) {
  return STATUS_META[status] ?? { label: "未知状态", tone: "unknown" };
}


function asArray(value) {
  return Array.isArray(value) ? value : [];
}


function normalizeRoute(envelope) {
  const itinerary = asArray(envelope?.data?.itinerary);
  return itinerary
    .filter((row) => row && typeof row.node_id === "string")
    .map((row) => ({
      nodeId: row.node_id,
      label: row.label ?? NODE_LABELS[row.node_id] ?? row.node_id,
      arrivalMinutes: row.arrival_after_minutes ?? row.minutes ?? null,
      dwellMinutes: row.dwell_minutes ?? null,
    }));
}


function normalizeWeather(weather) {
  if (!weather || typeof weather !== "object") {
    return null;
  }

  const definitions = {
    open_meteo: { kind: "live", label: "Open-Meteo 实时天气" },
    provided_synthetic: { kind: "synthetic", label: "合成演示天气" },
    fixed_fallback: { kind: "fallback", label: "固定安全回退天气" },
  };
  const definition = definitions[weather.source] ?? {
    kind: "unknown",
    label: "未识别天气来源",
  };

  return {
    ...definition,
    source: weather.source ?? "unknown",
    temperature: weather.temperature_celsius ?? null,
    apparentTemperature: weather.apparent_temperature_celsius ?? null,
    precipitation: weather.precipitation_mm ?? null,
    weatherCode: weather.weather_code ?? null,
    windSpeed: weather.wind_speed_kmh ?? null,
    observedAt: weather.observed_at ?? null,
    fetchedAt: weather.fetched_at ?? null,
    timezone: weather.timezone ?? null,
    attribution: weather.attribution ?? null,
    attributionUrl: weather.attribution_url ?? null,
    isDemo: weather.demo_data === true,
  };
}


function normalizeIncident(data) {
  const envelope = data?.incident
    ?? (data?.stopped_after === "incident-triage-dispatch" ? data.response : null);
  const incident = envelope?.data;
  if (!incident || typeof incident !== "object") {
    return null;
  }
  return {
    status: envelope.status ?? "unknown",
    category: incident.category ?? null,
    priority: incident.priority ?? null,
    responsibleRole: incident.responsible_role ?? null,
    dispatchStatus: incident.dispatch_status ?? null,
    sent: incident.sent === true,
    actions: asArray(incident.immediate_actions),
    prohibitedActions: asArray(incident.prohibited_actions),
  };
}


function normalizeKnowledge(data) {
  const envelope = data?.knowledge
    ?? (data?.stopped_after === "panda-knowledge-guard" ? data.response : null);
  if (!envelope || typeof envelope !== "object") {
    return null;
  }
  return {
    status: envelope.status ?? "unknown",
    answer: envelope.data?.answer ?? null,
    sourceRefs: asArray(envelope.source_refs),
    warnings: asArray(envelope.warnings),
  };
}


function headlineFor(status, data) {
  if (status === "escalated" || data?.stopped_after === "incident-triage-dispatch") {
    return "安全事件已阻断普通规划";
  }
  if (status === "degraded") {
    return "实时依赖不可用，已使用安全回退";
  }
  if (status === "rejected") {
    return "当前条件下无法生成安全方案";
  }
  if (status === "needs_input" && normalizeRoute(data?.final_itinerary).length > 0) {
    return "路线已生成，科普信息需补充来源";
  }
  if (status === "needs_input") {
    return "需要补充信息后再继续";
  }
  if (data?.replanned === true) {
    return "路线已按动物福利与无障碍约束调整";
  }
  if (status === "ok") {
    return "演示规则允许生成此路线";
  }
  return "返回了未识别的执行状态";
}


function scopeNoteFor(data) {
  const executedSkills = new Set(
    asArray(data?.execution_records)
      .map((record) => record?.skill)
      .filter((skill) => typeof skill === "string"),
  );
  if (data?.stopped_after === "incident-triage-dispatch") {
    executedSkills.add("incident-triage-dispatch");
  }

  const labels = [
    ["incident-triage-dispatch", "有限关键词事件门禁"],
    ["visitor-policy-check", "固定入园字段"],
    ["accessible-itinerary-planner", "合成图无台阶路径与游览段时长"],
    ["welfare-risk-dispatcher", "演示温度与关闭规则"],
    ["panda-knowledge-guard", "已登记知识卡"],
  ]
    .filter(([skill]) => executedSkills.has(skill))
    .map(([, label]) => label);
  const checked = labels.length > 0 ? labels.join("、") : "没有可确认的业务检查";

  if (data?.stopped_after === "incident-triage-dispatch") {
    return `本次已执行：${checked}；高风险事件已阻断，未执行入园、路线或天气检查。未确认真实人员已接手或事件已解决。`;
  }
  return `本次已执行：${checked}；未检查真实坡度、排队、场馆运营或个体动物状态。`;
}


function collectEvidence(response) {
  const envelopes = [
    ["总控", response],
    ...NESTED_RESPONSE_KEYS.map((key) => [key, response?.data?.[key]]),
  ];
  const evidence = [];
  const seen = new Set();

  for (const [scope, envelope] of envelopes) {
    if (!envelope || typeof envelope !== "object") {
      continue;
    }
    for (const [kind, field] of [
      ["source", "source_refs"],
      ["rule", "rule_refs"],
      ["warning", "warnings"],
      ["action", "next_actions"],
    ]) {
      for (const value of asArray(envelope[field])) {
        if (typeof value !== "string") {
          continue;
        }
        const identity = `${kind}:${value}`;
        if (!seen.has(identity)) {
          seen.add(identity);
          const metadata = kind === "source" ? SOURCE_META[value] : null;
          evidence.push({
            kind,
            scope,
            value,
            label: metadata?.label ?? (kind === "rule" ? RULE_LABELS[value] : null) ?? value,
            url: metadata?.url ?? null,
          });
        }
      }
    }
  }
  return evidence;
}


export function buildDemoViewModel(response) {
  const safeResponse = response && typeof response === "object" ? response : {};
  const data = safeResponse.data && typeof safeResponse.data === "object"
    ? safeResponse.data
    : {};
  const meta = statusMeta(safeResponse.status);
  const initialRoute = normalizeRoute(data.initial_itinerary);
  const finalRoute = normalizeRoute(data.final_itinerary);
  const finalNodeIds = new Set(finalRoute.map((row) => row.nodeId));
  const removedNodes = initialRoute.filter((row) => !finalNodeIds.has(row.nodeId));

  return {
    status: safeResponse.status ?? "unknown",
    statusLabel: meta.label,
    tone: meta.tone,
    headline: headlineFor(safeResponse.status, data),
    scopeNote: scopeNoteFor(data),
    isDemo: safeResponse.demo_data === true,
    replanned: data.replanned === true,
    initialRoute,
    finalRoute,
    initialTotalMinutes: data.initial_itinerary?.data?.total_minutes ?? null,
    finalTotalMinutes: data.final_itinerary?.data?.total_minutes ?? null,
    removedNodes,
    weather: normalizeWeather(data.weather),
    incident: normalizeIncident(data),
    knowledge: normalizeKnowledge(data),
    executionRecords: asArray(data.execution_records),
    review: data.review?.data ?? null,
    evidence: collectEvidence(safeResponse),
    raw: safeResponse,
  };
}
