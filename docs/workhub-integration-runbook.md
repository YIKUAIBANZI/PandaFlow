# PandaFlow WorkHub 接入运行手册

更新：2026-09-14

## 1. 已确认的赛事口径

PandaFlow 选择 B 赛道 **SP-A 协同调度中枢**。赛事官方报名平台将该方向描述为意图拆解、长程规划、多 Agent 编排、博弈推演、群体涌现、协同压测和状态监控；PandaFlow 当前覆盖其中的意图拆解、长程规划、多 Skill 编排、异常分支和状态/证据记录，不声称已覆盖博弈推演、群体涌现或协同压测。

官方平台同时说明：Skill 以可视化工作流编排为核心，也允许开发者自行对接 API，再通过 API 调用节点调用已有服务。因此接入采用“WorkHub 可视化编排与展示 + PandaFlow HTTPS API 确定性执行”的薄适配，不重写规则核心。

赛事来源：

- [2026 全球智能体大赛官方报名平台](https://di.workbrain.cn/webapp/r3vh7NpFy9qm64ke/17/releases/)
- [Assumption University 东盟赛区活动页](https://www.au.edu/event/1010-digital-human-festival-ai-agent-challenge/)
- [明途 OPC 智能体开发者社区](https://opc.workbrain.cn/)

## 2. 已确认与未确认边界

已确认：

- 每个有效 Skill 需要 `SKILL.md`、脚本或逻辑、测试用例和资源，并可独立触发、输出正确，不能是纯模板套壳。
- B 赛道需要至少 6 个有效 Skill；推荐同时提交在线链接和 WorkHub 导出 ZIP。
- 演示载体必须绑定 Skills 包并支持在线运行/触发；API 接口文档 PDF 是必填项。
- 一等奖候选除 Cx、蒸馏和 Live Demo 达标外，还要求包内至少 6 个有效 Skill 全部上架能力超市。
- Cx 第五项要求与 WorkHub、智能体或空间形成非平凡业务闭环。

尚未确认：

- 登录后 Skill 创建表单的准确字段名、字段长度和枚举。
- API 节点的鉴权字段、超时、重试、响应映射和错误分支格式。
- WorkHub 导出 ZIP 的目录结构、manifest 文件名和版本兼容规则。
- 能力超市上架审核字段、审核周期和公开链接格式。

因此仓库不提供自称官方的 WorkHub manifest，也不把本地源码 ZIP 伪装成 WorkHub 导出 ZIP。真实字段只能以登录后的当前界面、培训材料或平台实际导出样例为准。

## 3. 推荐接入拓扑

```text
WorkHub 智能体 / 空间
  ├─ 正常游览链路
  │   ├─ visitor-policy-check
  │   ├─ accessible-itinerary-planner
  │   ├─ welfare-risk-dispatcher
  │   └─ 必要时再次调用 accessible-itinerary-planner
  ├─ 知识问答支路：panda-knowledge-guard
  ├─ 高风险中断：incident-triage-dispatch
  └─ 脱敏记录复盘：operations-review
             ↓
        PandaFlow HTTPS API
```

优先级保持：人身安全 > 动物福利与园区规则 > 无障碍 > 游览偏好。WorkHub 编排不得把 `rejected` 或 `escalated` 改写为普通成功，也不得在医疗、走失等高风险事件后继续输出可执行游览路线。

## 4. 六个 API 节点映射

`{BASE_URL}` 现为 `https://pandeflow.yikuaibanz.cn`，2026-09-14 公网烟测通过，平台侧可达性待实际调用。请求头使用 `Content-Type: application/json`；本次公开 Demo 无需鉴权。平台节点的鉴权选项、响应变量和导出格式仍以真实界面为准。

| WorkHub Skill | HTTP 调用 | 编排职责 | 必须检查的返回值 |
|---|---|---|---|
| `visitor-policy-check` | `POST {BASE_URL}/api/v1/skills/visitor-policy-check` | 日期、入园时段、预约状态和证件类型完整性 | `status`、`data.eligible`、`warnings` |
| `accessible-itinerary-planner` | `POST {BASE_URL}/api/v1/skills/accessible-itinerary-planner` | 在时长、偏好、无障碍和关闭节点约束下生成路线 | `status`、`data.itinerary`、`data.omitted_preferences` |
| `welfare-risk-dispatcher` | `POST {BASE_URL}/api/v1/skills/welfare-risk-dispatcher` | 合并天气、拥挤度与关闭节点风险，决定是否重规划 | `status`、`data.replan_required`、`data.active_avoid_nodes` |
| `panda-knowledge-guard` | `POST {BASE_URL}/api/v1/skills/panda-knowledge-guard` | 只回答有登记来源支持的知识问题 | `status`、`data.answer`、`source_refs` |
| `incident-triage-dispatch` | `POST {BASE_URL}/api/v1/skills/incident-triage-dispatch` | 高风险事件优先分诊并生成未发送的人工升级草稿 | `status`、`data.priority`、`data.sent` |
| `operations-review` | `POST {BASE_URL}/api/v1/skills/operations-review` | 只复盘白名单元数据，不处理原始事件文本 | `status`、`data.observations`、`data.causal_claims` |

总控演示入口 `POST {BASE_URL}/api/v1/demo/run` 可用于整链路验收，但不能替代 6 个 Skill 的独立触发证据。当前 OpenAPI 已为六 Skill 与总控提供七类精确响应模型；完整字段、示例和错误响应以部署实例的 `{BASE_URL}/docs` 为准。

## 5. 第一条联调链路

本地正常、缺时段和 HTTP 校验失败的真实请求/响应样例见 [workhub-smoke/README.md](workhub-smoke/README.md)。它们是 ASGITransport 本地证据，不是平台调用记录；联调时更新请求日期。

先用正常、非敏感的 `visitor-policy-check` 验证 API 节点：

```json
{
  "visit_date": "2026-09-12",
  "entry_slot": "morning",
  "reservation_status": "confirmed",
  "document_type": "passport",
  "language": "zh",
  "accessibility_needs": ["wheelchair"]
}
```

验收时必须保存以下证据：

1. WorkHub 节点配置页，能看到真实请求 URL、方法和输入映射，但遮盖密钥。
2. 节点测试的请求与响应；响应应保留统一 `status`、`data`、`rule_refs`、`source_refs`、`warnings` 和 `demo_data`。
3. 缺少 `entry_slot` 的异常样例，确认 WorkHub 不把 `needs_input` 当成成功。
4. Skill 独立触发链接或运行记录。
5. 平台导出 ZIP 后，在新项目中重新导入并重复以上测试。

第一条通过后，再按正常链路接路线与福利风险；最后接高风险事件中断和复盘。这样能把平台映射问题与 PandaFlow 业务问题分开定位。

## 6. 登录后字段采集表

首次进入 WorkHub 后先记录事实，不立即批量创建 6 个 Skill：

| 待采集项 | 证据形式 | 当前状态 |
|---|---|---|
| WorkHub 真实入口与版本 | URL + 页面截图 | 待采集 |
| Skill 创建字段与限制 | 字段名、必填、长度、枚举截图 | 待采集 |
| API 节点请求配置 | 方法、URL、headers、body、变量语法截图 | 待采集 |
| 响应映射与分支条件 | `status` 映射和异常分支截图 | 待采集 |
| 发布/上架流程 | 审核字段、状态、公开 URL 截图 | 待采集 |
| 导出/导入格式 | 平台实际导出的原始 ZIP + 导入结果 | 待采集 |

不得把账号、手机号、身份证、Token、Cookie 或 API 密钥写入仓库、截图或日志。平台对真实身份的要求与 PandaFlow 运行时数据边界分开处理。

## 7. 完成定义

只有以下证据全部存在，Cx-5 才能从“未完成”改为“通过”：

1. 6 个 Skill 均能在平台独立触发，正常和异常状态映射正确。
2. WorkHub 智能体或空间能完成正常路线、风险改线和高风险中断三条真实链路。
3. 平台回传保留来源、规则、演示数据和未发送状态，不扩大能力声明。
4. WorkHub 导出 ZIP 可在干净项目中重新导入并复现。
5. 保存实际运行链接、时间戳、脱敏截图和平台状态；若冲一等奖，6 个 Skill 还须全部上架能力超市。

当前仓库只完成了接入映射与本地 API 基线，尚未完成上述平台验收。
