# PandaFlow API 接口文档

版本：2026-09-14 · API `v1` · 应用版本 `0.1.0`

> 交付定位：供赛事评委、WorkHub API 调用节点配置和本地验收使用。本文只描述当前代码中真实存在的接口；示例里的 `request_id` 与 `generated_at` 每次调用都会变化。PandaFlow 是参赛原型，不代表园区官方服务，不发送真实工单，也不收集身份证号、手机号或健康隐私。

## 1. 快速接入

- 本地 Base URL：`http://127.0.0.1:8000`
- 公网 Base URL：`https://pandeflow.yikuaibanz.cn`（2026-09-14 公网验收通过）
- 内容类型：`Content-Type: application/json; charset=utf-8`
- 公开 Demo 鉴权：无；本次授权开放演示接口，不处理真实身份或发送工单。网关限制请求体 64KB；应用并发上限 32。后续如接入真实业务写入，须另行设计访问控制
- 交互式文档：`GET /docs`（FastAPI Swagger UI）
- OpenAPI：`GET /openapi.json`

启动命令：

```bash
PYTHONPATH=src uvicorn pandaflow.api.app:app --host 127.0.0.1 --port 8000
```

最小探活：

```bash
curl -sS http://127.0.0.1:8000/health
# {"status":"ok"}
```

## 2. 接口总览

| 方法与路径 | 用途 | WorkHub 节点建议 |
|---|---|---|
| `GET /health` | 进程级存活检查 | 部署探活，不作为 Skill |
| `GET /ready` | 规则资源与 Web 静态资源就绪检查 | 首次联调前置检查 |
| `GET /api/v1/demo/scenarios` | 获取固定评委演示场景 | Demo 可选辅助节点 |
| `POST /api/v1/skills/visitor-policy-check` | 入园前置核验 | Skill 1 |
| `POST /api/v1/skills/accessible-itinerary-planner` | 无障碍与时长约束路线规划 | Skill 2 |
| `POST /api/v1/skills/panda-knowledge-guard` | 有来源约束的熊猫知识问答 | Skill 3 |
| `POST /api/v1/skills/welfare-risk-dispatcher` | 天气、客流与动物福利规则分发 | Skill 4 |
| `POST /api/v1/skills/incident-triage-dispatch` | 事件分级与未发送处置草稿 | Skill 5 |
| `POST /api/v1/skills/operations-review` | 对执行元数据做描述性复盘 | Skill 6 |
| `POST /api/v1/demo/run` | 固定游客故事线总控编排 | 总控节点 |

## 3. 统一响应包络

六个独立 Skill 与总控均返回同一个 `SkillResponse` 包络：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `status` | string | 是 | 业务状态，见下节；HTTP 200 不等于业务成功 |
| `request_id` | string | 是 | 以 `req_` 开头的单次执行标识，可用于 WorkHub 关联日志 |
| `skill` | string | 是 | 当前 Skill 或总控名称 |
| `data` | object | 是 | 各 Skill 的具体业务结果；OpenAPI 已按六 Skill 与总控暴露七类精确响应模型，字段与本文一致 |
| `source_refs` | string[] | 是 | 使用到的来源 ID，可追溯到来源登记表 |
| `rule_refs` | string[] | 是 | 命中的确定性规则 ID |
| `warnings` | string[] | 是 | 限制、降级或安全提示 |
| `next_actions` | string[] | 是 | 建议的后续动作，不表示动作已经执行 |
| `demo_data` | boolean | 是 | `true` 表示结果含演示规则或合成数据；不得包装成真实园区运营数据 |
| `generated_at` | RFC 3339 datetime | 是 | UTC 生成时间 |

示例：

```json
{
  "status": "ok",
  "request_id": "req_示例值",
  "skill": "visitor-policy-check",
  "data": {"eligible": true, "visit_date": "2026-09-20", "entry_slot": "morning"},
  "source_refs": ["source_base_visitor_service"],
  "rule_refs": ["rule_reservation_required", "rule_document_check"],
  "warnings": ["This prototype uses demo rules and does not guarantee admission."],
  "next_actions": ["Bring the selected document and follow on-site guidance."],
  "demo_data": true,
  "generated_at": "2026-09-12T00:00:00Z"
}
```

### 状态语义

| `status` | WorkHub 分支建议 | 语义 |
|---|---|---|
| `ok` | 继续下一节点 | 当前步骤产生了可用结果 |
| `needs_input` | 暂停并向用户补问 | 缺少继续所需输入，或知识请求缺乏可靠来源 |
| `degraded` | 显示降级提示后谨慎继续 | 外部服务失败但返回固定安全结果；不得标成实时成功 |
| `escalated` | 立即停止普通流程并转人工 | 安全或高风险事件必须优先处理 |
| `rejected` | 停止并修改输入/路线 | 输入在业务规则下不可接受或安全路线不可形成 |

高风险状态不得被普通规划结果或复盘结果覆盖。WorkHub 应首先判断 `status`，再读取 `data`。

## 4. 公共错误与安全降级

### 校验错误 `422`

缺字段、越界、枚举不匹配或额外字段会返回去敏后的错误列表，不回显用户提交的值：

```json
{
  "detail": [
    {"type": "literal_error", "msg": "请求字段不符合输入约束，请参阅接口文档。"}
  ]
}
```

### 运行资源不可用 `503`

规则或打包资源无法读取时返回稳定消息，不泄露文件路径和内部异常：

```json
{"detail":"运行资源暂时不可用。"}
```

演示场景目录不可用时，`GET /api/v1/demo/scenarios` 返回：

```json
{"detail":"演示场景暂时不可用。"}
```

### 安全降级

总控使用 `weather_mode=live_current` 时，Open-Meteo 超时、断网或响应无效不会伪造实时成功；响应为业务状态 `degraded`，天气 `source=fixed_fallback`，同时保留警告。固定回退仍属于 `demo_data=true`。调用方应展示降级来源，不能把它改写成实时天气。

## 5. 独立 Skill 接口

### 5.1 入园核验 `visitor-policy-check`

`POST /api/v1/skills/visitor-policy-check`

请求字段：

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `visit_date` | `YYYY-MM-DD` 或 null | 计划日期 |
| `entry_slot` | `morning` / `afternoon` 或 null | 入园时段 |
| `reservation_status` | `confirmed` / `missing` / `unknown` 或 null | 预约状态 |
| `document_type` | string 或 null | 证件类型名称，不提交号码 |
| `language` | `zh` / `en`，默认 `zh` | 响应语言偏好 |
| `accessibility_needs` | string[] | 非身份化的无障碍需求标签 |

```json
{
  "visit_date": "2026-09-20",
  "entry_slot": "morning",
  "reservation_status": "confirmed",
  "document_type": "passport",
  "language": "zh",
  "accessibility_needs": ["elder_companion"]
}
```

`data` 主要字段：`eligible:boolean`、`visit_date:string|null`、`entry_slot:string|null`。信息不足时返回 `needs_input`；规则不允许时返回 `rejected`。

### 5.2 无障碍路线 `accessible-itinerary-planner`

`POST /api/v1/skills/accessible-itinerary-planner`

请求字段：

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `entry_node` | node ID，1–100 字符 | 起点 |
| `available_minutes` | integer，1–480 | 总可用分钟数 |
| `must_see` | node ID[]，最多 20 | 偏好点位 |
| `mobility_need` | `standard` / `step_free` | 通行需求 |
| `closed_nodes` | node ID[]，最多 20 | 关闭或必须避开的点位 |

```json
{
  "entry_node": "north_gate",
  "available_minutes": 120,
  "must_see": ["panda_nursery", "science_hall"],
  "mobility_need": "step_free",
  "closed_nodes": []
}
```

`data.itinerary[]` 包含 `node_id`、`arrival_after_minutes`、`dwell_minutes`；并返回 `total_minutes`、`rest_stops`、`omitted_preferences`、`fulfilled_preferences`。无法形成安全路线时为 `rejected`，不能继续调用普通游览流程。

### 5.3 来源约束问答 `panda-knowledge-guard`

`POST /api/v1/skills/panda-knowledge-guard`

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `question` | string，1–500 字符 | 问题，不得包含个人隐私 |
| `language` | `zh` / `en`，默认 `zh` | 回答语言 |

```json
{"question":"大熊猫主要吃什么？","language":"zh"}
```

`data.answer` 只使用登记过的知识卡。能回答时为 `ok` 并给出 `source_refs`；无可靠来源时为 `needs_input`，不会编造动物实时位置、诊疗或园区内部信息。

### 5.4 福利风险分发 `welfare-risk-dispatcher`

`POST /api/v1/skills/welfare-risk-dispatcher`

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `temperature_celsius` | number，-50–60 | 必填气温 |
| `apparent_temperature_celsius` | number，-80–80 或 null | 体感温度 |
| `precipitation_mm` | number，0–2000 或 null | 降水量 |
| `weather_code` | integer，0–99 或 null | 天气代码 |
| `wind_speed_kmh` | number，0–500 或 null | 风速 |
| `crowd_level` | `low` / `medium` / `high` | 演示客流等级 |
| `route_nodes` | string[] | 当前路线点位 |
| `closed_nodes` | string[] | 已知关闭点位 |

```json
{
  "temperature_celsius": 33,
  "apparent_temperature_celsius": 36,
  "precipitation_mm": 0,
  "weather_code": 1,
  "wind_speed_kmh": 8,
  "crowd_level": "high",
  "route_nodes": ["north_gate", "panda_nursery", "bamboo_grove"],
  "closed_nodes": []
}
```

`data` 包含 `risk_level`、`replan_required`、`avoid_nodes`、`active_avoid_nodes`、`reasons`、`weather`。若 `replan_required=true`，下一个路线节点必须把全部 `active_avoid_nodes` 放入 `closed_nodes`，并再次验证最终路线没有重新引入禁行点。

### 5.5 事件分级 `incident-triage-dispatch`

`POST /api/v1/skills/incident-triage-dispatch`

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `description` | string，最多 2000 | 去身份化事件描述 |
| `area` | string，最多 100 | 区域名称或点位 ID |
| `involved_groups` | 最多 4 项 | `child`、`elder`、`adult`、`mobility_impaired` |
| `is_ongoing` | boolean 或 null | 是否仍在发生 |
| `measures_taken` | string[]，最多 10 | 已采取措施，不写姓名或联系方式 |
| `category_hint` | 枚举或 null | `medical`、`missing_person`、`lost_property`、`ticketing`、`order`、`facility` |

```json
{
  "description": "手机遗失",
  "area": "north_gate",
  "involved_groups": ["adult"],
  "is_ongoing": false,
  "measures_taken": [],
  "category_hint": "lost_property"
}
```

`data` 包含 `category`、`priority`、`responsible_role`、`immediate_actions`、`prohibited_actions`、`reply_template`、`dispatch_status`、`sent`、`missing_fields`、`rule_version`、`safety_signals`。输出永远只是草稿，`sent=false`；医疗、走失或混合高风险描述会返回 `escalated`，普通规划必须立即停止并转人工。

### 5.6 运行复盘 `operations-review`

`POST /api/v1/skills/operations-review`

请求体只有 `records`，最多 1000 条。每条允许的元数据包括：

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `record_id` | `req_` 开头 | 原 Skill 的 request ID |
| `skill` | 六 Skill 名称之一 | 被复盘的 Skill |
| `status` | 统一业务状态 | 原业务状态 |
| `rule_refs` / `source_refs` | string[] | 规则和来源 ID |
| `demo_data` | boolean | 是否演示数据 |
| `incident_category` / `priority` | 可选 | 仅事件 Skill 可带 |

```json
{
  "records": [{
    "record_id": "req_demo1",
    "skill": "visitor-policy-check",
    "status": "ok",
    "rule_refs": ["rule_reservation_required"],
    "source_refs": ["source_base_visitor_service"],
    "demo_data": true
  }]
}
```

`data` 返回调用量、状态/Skill/规则计数、事件计数、描述性观察和候选规则。它不接收原始事件描述、游客身份或任意业务结果，不作因果推断，不能把先前的 `escalated` 或 `rejected` 改成 `ok`。

## 6. 总控接口

`POST /api/v1/demo/run`

请求字段：

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| `visit_date` | `YYYY-MM-DD` | 必填参观日期 |
| `temperature_celsius` | -50–60 或 null | 合成天气模式使用 |
| `weather_mode` | `synthetic` / `live_current` | 默认 `synthetic` |
| `crowd_level` | `low` / `medium` / `high` | 演示客流等级 |
| `must_see` | string[] | 默认熊猫幼儿园与科普馆 |
| `incident` | IncidentRequest 或 null | 可选事件；优先于普通规划 |
| `knowledge` | KnowledgeRequest 或 null | 可选知识请求 |

```json
{
  "visit_date": "2026-09-20",
  "temperature_celsius": 33,
  "weather_mode": "synthetic",
  "crowd_level": "high",
  "must_see": ["panda_nursery", "bamboo_grove"]
}
```

正常流程：入园核验 → 初始路线 → 天气解析 → 福利风险 → 必要时重规划 → 可选知识问答 → 元数据复盘。若传入进行中的走失/医疗等高风险事件，总控先分诊并停止普通路线；若最终路线仍含活动禁行点，则为 `rejected`。`data` 会按已执行步骤返回嵌套 Skill 响应、`execution_records` 与 `review`，未执行的步骤不会伪造成已完成。

## 7. 辅助接口

### `GET /health`

无依赖存活检查。成功为 HTTP 200：`{"status":"ok"}`。

### `GET /ready`

检查九个打包规则资源与四个 Web 静态资源。就绪为 HTTP 200：`{"status":"ready"}`；资源缺失为前述 HTTP 503。

### `GET /api/v1/demo/scenarios`

返回白名单固定场景目录，供 Web Demo 选择；目录中的输入仍须按对应 Pydantic 模型校验。该接口不是用户内容存储或实时园区数据接口。

## 8. WorkHub 字段映射

先用 `visitor-policy-check` 做最小烟测，再扩展到六 Skill 和总控：

| WorkHub 配置项 | PandaFlow 值 |
|---|---|
| Method | `POST`（探活/场景目录除外） |
| URL | `{BASE_URL}` + 本文路径 |
| Header | `Content-Type: application/json`；鉴权字段待登录后真实表单确认 |
| Body | 对应接口请求 JSON；不要把身份证号、手机号、姓名或健康隐私传入 |
| 成功分支 | HTTP 200 且 `status=ok` |
| 补问分支 | HTTP 200 且 `status=needs_input` |
| 降级分支 | HTTP 200 且 `status=degraded`，必须展示 `warnings` |
| 人工分支 | HTTP 200 且 `status=escalated`，停止普通流程 |
| 拒绝分支 | HTTP 200 且 `status=rejected` |
| 技术错误 | HTTP 422/503；按有限重试和人工提示处理，不把技术失败改成业务成功 |
| 追踪字段 | 保存 `request_id`、`skill`、`status`、`source_refs`、`rule_refs`、`demo_data` |

WorkHub 首条验收应至少保存：真实节点配置截图、请求体、HTTP 状态、完整响应、`request_id`、异常分支截图与平台导出样例。平台字段名、鉴权、响应变量表达式和导出 ZIP 结构必须以登录后实际界面为准。

## 9. 隐私、安全与事实边界

- 不存储或要求真实姓名、手机号、身份证/护照号码、精确健康信息。
- 不诊断、不治疗；医疗和走失只生成转人工建议。
- 事件输出是未发送草稿，`sent=false`，不代表已通知任何岗位。
- 路线、客流、动物福利阈值和部分政策为演示规则，使用时保持 `demo_data=true`。
- Open-Meteo 只提供公开天气上下文，不代表动物个体状态或园区实时运营情况。
- `source_refs` 与 `rule_refs` 是审计线索，不是官方合作或现场执行证明。

## 10. 未完成边界

截至 2026-09-14，本地 API、六 Skill、总控和公网 HTTPS 均已验证；公网四场景通过，本次天气为 open_meteo。以下事项仍未完成：

1. 公网地址已就绪，但尚未从 WorkHub 实际发起调用验证平台侧可达性。
2. WorkHub 登录后字段、鉴权方式、变量映射和导出包 schema 尚未取得一手样例。
3. 尚未完成真实平台调用、异常回传、六 Skill 闭环、能力超市上架或审核。
4. 七类精确响应模型已经进入 OpenAPI，但平台变量表达式和字段绑定仍须用 WorkHub 实际界面验收。
5. 本文档不等于平台联调证据，也不等于赛事终版方案书或蒸馏包。

联调完成后应回填 WorkHub 鉴权配置、字段截图/导出证据和最终版本校验值，再冻结终版 PDF。
