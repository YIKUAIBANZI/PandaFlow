# PandaFlow 技术设计规格

- 状态：待用户书面审阅
- 日期：2026-09-04
- 对应报告：`docs/PandaFlow-项目报告.md`

## 1. 目标

构建一个可独立运行、可测试、可导出且可适配 WorkHub 的 Skills 包。系统必须提供 6 个有效 Skill，并通过一个编排器完成游客行前咨询、路线计划、动态风险调度、现场事件处置和运营复盘。

系统的首要约束顺序为：人身安全 > 动物福利与园区规则 > 无障碍可达性 > 游览偏好。

## 2. 范围

### 2.1 本期包含

- 6 个独立 Skill 的 SKILL.md、Python 实现、资源和测试。
- 统一请求/响应契约、来源追溯和规则版本机制。
- Open-Meteo 天气 API 适配器及离线降级。
- 基于合成园区状态的风险调度与事件工单。
- 多 Skill 总控编排和单一端到端 Demo。
- 本地 Web 演示页、HTTP API、执行日志和证据导出。
- WorkHub 适配边界、映射说明和导出准备。
- 行业应用方案、蒸馏材料、API 文档与演示材料源稿。

### 2.2 本期不包含

- 真实购票、退款、身份认证或票务系统写入。
- 真实客流传感器、真实工单系统或目标机构内部 API。
- 医疗诊断、治疗建议或自动呼叫紧急服务。
- 人脸识别、身份证存储、用户画像追踪。
- 未经官方资料支持的动物实时位置或展示承诺。
- 在缺少官方 WorkHub 样例时伪造平台专属包格式。

## 3. 技术选型

- 运行时：Python 3.11。
- Web/API：FastAPI。
- 模型与校验：Pydantic 2。
- HTTP 客户端：httpx。
- 测试：pytest。
- 数据：版本化 JSON 文件，不引入数据库。
- 前端：原生 HTML、CSS、JavaScript，由 FastAPI 静态托管。
- 外部服务：Open-Meteo `/v1/forecast`。
- 依赖管理：`pyproject.toml` 与锁文件。

选择原则是减少依赖和部署面。核心规则层不得依赖语言模型或外部网络；即使天气服务和 WorkHub 都不可用，6 个 Skill 仍应能使用测试数据独立运行。

## 4. 总体架构

```text
Web Demo / WorkHub Agent
          |
          v
     Orchestrator
          |
  +-------+-------------------------------+
  |       |       |       |       |       |
  v       v       v       v       v       v
Policy  Route  Knowledge  Risk  Incident Review
  |       |       |       |       |       |
  +-------+-------+-------+-------+-------+
                  |
                  v
    Shared Contracts / Rules / Provenance
                  |
          +-------+--------+
          |                |
     Official Data    Weather Adapter
```

## 5. 目录结构

```text
pandaflow/
├── pyproject.toml
├── README.md
├── src/pandaflow/
│   ├── shared/
│   │   ├── contracts.py
│   │   ├── errors.py
│   │   ├── provenance.py
│   │   ├── rules.py
│   │   └── logging.py
│   ├── skills/
│   │   ├── visitor_policy_check/
│   │   ├── accessible_itinerary_planner/
│   │   ├── panda_knowledge_guard/
│   │   ├── welfare_risk_dispatcher/
│   │   ├── incident_triage_dispatch/
│   │   └── operations_review/
│   ├── integrations/
│   │   └── weather.py
│   ├── orchestrator/
│   │   └── service.py
│   └── api/
│       ├── app.py
│       └── static/
├── resources/
│   ├── source_registry.json
│   ├── visitor_rules.json
│   ├── welfare_rules.json
│   ├── incident_rules.json
│   ├── knowledge_cards.json
│   ├── park_graph.json
│   └── demo_scenarios.json
├── adapters/workhub/
│   └── README.md
├── tests/
│   ├── contract/
│   ├── integration/
│   └── e2e/
├── evidence/
└── docs/
```

每个 Skill 子目录还包含自己的 `SKILL.md`、`service.py`、`schemas.py` 和 `tests/`。根目录测试负责跨 Skill 契约与工作流。

## 6. 通用契约

### 6.1 响应包络

```json
{
  "status": "ok",
  "request_id": "req_123",
  "skill": "visitor-policy-check",
  "data": {},
  "source_refs": ["src_ticket_001"],
  "rule_refs": ["rule_ticket_001"],
  "warnings": [],
  "next_actions": [],
  "demo_data": false,
  "generated_at": "2026-09-04T12:00:00+08:00"
}
```

`status` 只允许：

- `ok`：正常完成。
- `needs_input`：缺少必要信息。
- `degraded`：外部服务失败或使用演示数据。
- `escalated`：必须交由人工处理。
- `rejected`：请求越权、危险或不在能力范围内。

### 6.2 来源登记

每个来源包含 `source_id`、标题、发布者、URL、访问日期、内容摘要和适用 Skill。每条业务规则必须引用至少一个 `source_id`，或明确标为 `inferred`/`demo`。

## 7. Skill 详细要求

### 7.1 visitor-policy-check

输入：参观日期、入园时段、游客年龄/身高区间、证件类型、预约状态、语言、辅助需求。禁止输入完整证件号码。

功能要求：

- 根据季节选择开放与清园时间。
- 检查预约状态和特殊人群条件。
- 指出信息不足、时间冲突和来源。
- 不执行购票或承诺入园。

异常：日期缺失返回 `needs_input`；未知证件类型返回人工核验建议；过期规则必须返回警告。

### 7.2 accessible-itinerary-planner

输入：入口、可用分钟、游客组合、必看偏好、行动能力、设施/区域状态。

功能要求：

- 对园区节点图计算可执行路线。
- 安全、无障碍和关闭状态为硬约束。
- 游客偏好为软约束。
- 输出时间段、节点、预计耗时、休息点和备选方案。

异常：无法满足全部偏好时保留硬约束并解释取舍；没有可行路径时返回 `rejected`，不得凭空生成路线。

### 7.3 panda-knowledge-guard

输入：问题、语言、受众年龄、期望长度。

功能要求：

- 仅从登记知识卡中检索答案。
- 每个事实返回来源。
- 支持中文和英文模板表达。
- 对未经支持的传闻、实时状态或医疗问题拒答。

异常：无匹配知识时返回 `needs_input` 或明确无依据；低置信度不得生成确定性说法。

### 7.4 welfare-risk-dispatcher

输入：天气数据、区域状态、合成客流等级、游客计划、游客特征。

功能要求：

- 调用 Open-Meteo 获取温度、体感温度、降水、天气码和风速。
- 将天气与公开动物福利/场馆规则结合。
- 输出风险等级、原因、游客提醒和重规划请求。
- 不推断具体动物健康状态。

异常：接口超时或格式错误时使用固定演示天气并返回 `degraded`；高风险必须优先触发安全动作。

### 7.5 incident-triage-dispatch

输入：事件描述、区域、涉及人群、是否仍在持续、已采取措施。

功能要求：

- 分类医疗、儿童/同伴走失、失物、票务、秩序、设施六类事件。
- 根据规则矩阵分配 P0-P3 优先级。
- 输出负责岗位、立即动作、禁止动作、人工回复模板。
- 不声称真实工单已发送。

异常：医疗和走失相关高风险输入一律 `escalated`；描述不足但可能高风险时按较高等级处理并请求补充。

### 7.6 operations-review

输入：脱敏后的 Skill 执行记录与事件记录。

功能要求：

- 聚合调用量、降级次数、规则命中、事件类型和响应状态。
- 输出高频问题、规则更新候选和操作性建议。
- 所有结论可回溯到记录编号。
- 小样本只报告观察，不宣称因果。

异常：记录不足时返回描述性摘要；存在非法个人字段时拒绝处理并记录安全警告。

## 8. 编排流程

端到端场景按以下顺序运行：

1. `visitor-policy-check` 校验行前条件。
2. 条件允许时调用 `accessible-itinerary-planner`。
3. `welfare-risk-dispatcher` 获取天气并检查动态状态。
4. 如产生重规划请求，再次调用路线 Skill。
5. 游客问答按需调用 `panda-knowledge-guard`。
6. 现场事件调用 `incident-triage-dispatch`，高风险立即终止普通流程并升级人工。
7. 全部脱敏记录进入 `operations-review`。

编排器不得绕过任何 Skill 的 `rejected` 或 `escalated` 状态。

## 9. HTTP API

- `GET /health`
- `GET /api/v1/sources`
- `POST /api/v1/skills/visitor-policy-check`
- `POST /api/v1/skills/accessible-itinerary-planner`
- `POST /api/v1/skills/panda-knowledge-guard`
- `POST /api/v1/skills/welfare-risk-dispatcher`
- `POST /api/v1/skills/incident-triage-dispatch`
- `POST /api/v1/skills/operations-review`
- `POST /api/v1/demo/run`

HTTP 错误与业务状态分离：无效 JSON 使用 4xx；业务缺信息、降级或升级仍返回合法响应包络，由 `status` 表达。

## 10. WorkHub 适配策略

在缺少官方开发文档时，不生成未经验证的平台 manifest。适配层先提供：

- 6 个 Skill 的名称、说明、触发条件、JSON 输入输出与权限清单。
- HTTP 调用示例和本地执行命令。
- 资源文件与测试证据的位置。
- 从平台表单字段映射到本地 API 的说明。

获得官方样例后，只有满足以下条件才标记“WorkHub 可提交”：

1. 6 个 Skill 均可在平台独立触发。
2. 输入、输出和错误状态与本地契约一致。
3. Skill 已通过能力超市审核。
4. 总控智能体可完成端到端联动。
5. 导出 ZIP 能重新导入并复现运行结果。

## 11. 测试策略

### 11.1 单 Skill 测试

每个 Skill 至少包含 5 类用例：正常、边界、缺失输入、规则冲突、依赖失败。6 个 Skill 的单元与契约测试合计不少于 30 个。

### 11.2 集成测试

- 合规核验成功后生成路线。
- 天气风险触发重规划。
- 无证据问题被知识守卫拒答。
- 医疗事件阻断普通流程并升级人工。
- 天气接口失败时端到端流程仍可解释完成。
- 全流程记录可被运营复盘读取。

### 11.3 安全测试

- 请求中出现身份证号、手机号等字段时拒绝或脱敏。
- 日志中不得包含秘密和个人数据。
- 非法 URL、路径和超长文本不得导致文件访问或服务崩溃。
- 依赖锁定并执行已知漏洞检查。

## 12. 性能与可靠性目标

- 不含外部天气请求的本地 Skill，P95 响应时间低于 500 ms。
- 天气请求总超时 3 秒，失败后立即降级。
- 相同输入与相同规则版本产生确定性结果。
- 每次调用均生成 request_id、时间、规则引用和来源引用。
- 本地端到端演示在断网模式下仍可完成。

## 13. 验收标准

项目实现完成需同时满足：

1. 6 个 Skill 均可通过函数与 HTTP 接口独立运行。
2. 每个 Skill 的 SKILL.md、逻辑、资源和测试齐全。
3. 自动化测试全量通过，且生成机器可读与人类可读报告。
4. 端到端 Demo 同时展示正常、动态变化和人工升级。
5. 所有事实型输出均含来源或明确拒答。
6. 所有合成数据都带 `demo_data=true`。
7. 项目报告、蒸馏包、API 文档、封面简介和录屏脚本齐全。
8. WorkHub 平台状态只根据真实联调结果声明，不把本地运行冒充平台运行。

## 14. 设计自检

- 无未定义的第 7 个 Skill；总控只作为编排器。
- 目标机构、公开事实、业务假设和合成数据已分开标记。
- API 失败、来源缺失、路线无解、高风险事件和敏感数据均有明确处理。
- MVP 限定为一个故事线和一套规则数据，不扩展到购票、支付或真实工单。
- WorkHub 不确定性被隔离在适配层，不影响核心开发与测试。
