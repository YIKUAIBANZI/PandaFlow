import test from "node:test";
import assert from "node:assert/strict";

import {
  buildDemoViewModel,
  statusMeta,
} from "../../src/pandaflow/web/view-model.js";


const step = (node_id, label) => ({ node_id, label, minutes: 10 });

const response = {
  status: "ok",
  skill: "pandaflow-demo-orchestrator",
  demo_data: true,
  source_refs: ["open-meteo"],
  rule_refs: ["welfare.demo.heat"],
  warnings: [],
  next_actions: ["Continue"],
  data: {
    replanned: true,
    weather: {
      source: "provided_synthetic",
      temperature_celsius: 33,
      demo_data: true,
    },
    initial_itinerary: {
      data: {
        itinerary: [
          step("north_gate", "北门"),
          step("bamboo_grove", "竹林"),
        ],
      },
    },
    final_itinerary: {
      data: {
        itinerary: [
          step("north_gate", "北门"),
          step("science_hall", "科普馆"),
        ],
      },
    },
    execution_records: [
      {
        record_id: "req_1",
        skill: "visitor-policy-check",
        status: "ok",
        demo_data: true,
      },
    ],
    review: {
      status: "ok",
      data: {
        total_calls: 1,
        status_counts: { ok: 1 },
        skill_counts: { "visitor-policy-check": 1 },
        record_ids: ["req_1"],
      },
    },
  },
};


test("replanned response exposes removed route nodes and demo provenance", () => {
  const model = buildDemoViewModel(response);

  assert.equal(model.statusLabel, "演示规则检查通过");
  assert.equal(model.headline, "路线已按动物福利与无障碍约束调整");
  assert.match(model.scopeNote, /固定入园字段/);
  assert.match(model.scopeNote, /未检查/);
  assert.deepEqual(
    model.removedNodes.map((row) => row.nodeId),
    ["bamboo_grove"],
  );
  assert.equal(model.weather.kind, "synthetic");
  assert.equal(model.isDemo, true);
});


test("route summary uses the real lake node and auditable duration", () => {
  const model = buildDemoViewModel({
    ...response,
    data: {
      ...response.data,
      initial_itinerary: {
        data: {
          itinerary: [
            { node_id: "north_gate", arrival_after_minutes: 0, dwell_minutes: 0 },
            { node_id: "lake_pavilion", arrival_after_minutes: 12, dwell_minutes: 15 },
          ],
          total_minutes: 27,
        },
      },
      final_itinerary: {
        data: {
          itinerary: [
            { node_id: "north_gate", arrival_after_minutes: 0, dwell_minutes: 0 },
            { node_id: "lake_pavilion", arrival_after_minutes: 12, dwell_minutes: 15 },
          ],
          total_minutes: 27,
        },
      },
    },
  });

  assert.equal(model.finalRoute[1].label, "湖畔休憩亭");
  assert.equal(model.finalRoute[1].dwellMinutes, 15);
  assert.equal(model.initialTotalMinutes, 27);
  assert.equal(model.finalTotalMinutes, 27);
});


test("incident actions and registered sources are judge-readable", () => {
  const model = buildDemoViewModel({
    ...response,
    source_refs: ["source_panda_base_diet"],
    data: {
      stopped_after: "incident-triage-dispatch",
      response: {
        status: "escalated",
        data: {
          priority: "P1",
          dispatch_status: "draft",
          sent: false,
          immediate_actions: ["暂停普通游览安排，立即寻求现场工作人员协助。"],
        },
      },
      execution_records: [],
      review: response.data.review,
    },
  });

  assert.deepEqual(model.incident.actions, [
    "暂停普通游览安排，立即寻求现场工作人员协助。",
  ]);
  const source = model.evidence.find((item) => item.value === "source_panda_base_diet");
  assert.equal(source.label, "成都熊猫基地：熊猫知识·进食");
  assert.equal(
    source.url,
    "https://www.panda.org.cn/yd/education/database/kpzs/2025-06-05/8786.html",
  );
});


test("escalated response does not invent a route", () => {
  const model = buildDemoViewModel({
    ...response,
    status: "escalated",
    data: {
      stopped_after: "incident-triage-dispatch",
      response: {
        data: {
          priority: "P0",
          dispatch_status: "draft",
          sent: false,
        },
      },
      execution_records: [],
      review: response.data.review,
    },
  });

  assert.equal(model.statusLabel, "需要人工介入");
  assert.equal(model.headline, "安全事件已阻断普通规划");
  assert.deepEqual(model.finalRoute, []);
  assert.equal(model.incident.sent, false);
  assert.match(model.scopeNote, /有限关键词事件门禁/);
  assert.match(model.scopeNote, /未执行入园、路线或天气检查/);
  assert.doesNotMatch(model.scopeNote, /本次仅检查固定入园字段/);
});


test("fixed fallback stays degraded and is never labeled live", () => {
  const model = buildDemoViewModel({
    ...response,
    status: "degraded",
    data: {
      ...response.data,
      weather: {
        source: "fixed_fallback",
        temperature_celsius: 33,
        demo_data: true,
      },
    },
  });

  assert.equal(model.statusLabel, "已安全降级");
  assert.equal(model.weather.kind, "fallback");
  assert.notEqual(model.weather.label, "Open-Meteo 实时天气");
});


test("optional knowledge failure keeps a validated route visibly partial", () => {
  const model = buildDemoViewModel({
    ...response,
    status: "needs_input",
    data: {
      ...response.data,
      replanned: false,
      knowledge: {
        status: "needs_input",
        data: { answer: null },
        source_refs: [],
        warnings: ["No registered evidence supports this question."],
      },
    },
  });

  assert.equal(model.headline, "路线已生成，科普信息需补充来源");
  assert.equal(model.finalRoute.length, 2);
  assert.equal(model.knowledge.status, "needs_input");
  assert.equal(model.knowledge.answer, null);
});


test("unknown status is explicit rather than successful", () => {
  assert.deepEqual(statusMeta("unexpected"), {
    label: "未知状态",
    tone: "unknown",
  });
});


test("missing optional response fields produce an explicit empty model", () => {
  const model = buildDemoViewModel(undefined);

  assert.equal(model.status, "unknown");
  assert.equal(model.statusLabel, "未知状态");
  assert.deepEqual(model.initialRoute, []);
  assert.deepEqual(model.finalRoute, []);
  assert.deepEqual(model.executionRecords, []);
  assert.deepEqual(model.evidence, []);
  assert.equal(model.weather, null);
  assert.equal(model.incident, null);
  assert.equal(model.review, null);
});
