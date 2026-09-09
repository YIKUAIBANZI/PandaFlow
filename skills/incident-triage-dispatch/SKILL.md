---
name: incident-triage-dispatch
description: Classify a reported venue incident into a synthetic priority and produce an unsent human-routing draft.
---

# Incident Triage Dispatch

用于医疗、儿童/同伴走失、失物、票务、秩序或设施事件。优先级仅为合成演示规则，不能用于临床判断或代替园区正式处置规程。

调用 `POST /api/v1/skills/incident-triage-dispatch`：

```json
{"description":"儿童走失","area":"north_gate","involved_groups":["child"],"is_ongoing":true,"measures_taken":[]}
```

Python 入口：`triage_incident(IncidentRequest(...))`，位于 `pandaflow.skills.incident_triage_dispatch.service` 与 `.schemas`。

输入：`description` 最多 2000 字，`area` 最多 100 字；`involved_groups` 允许 child/elder/adult/mobility_impaired；`is_ongoing` 为布尔或未知；`measures_taken` 最多 10 条、每条 300 字。可选 `category_hint` 允许 medical/missing_person/lost_property/ticketing/order/facility。不要提交姓名、手机号、证件号或其他个人数据；服务不回显事件原文。

输出沿用统一 SkillResponse。`data` 包含 category、priority、responsible_role、immediate_actions、prohibited_actions、reply_template、missing_fields、rule_version，且 `dispatch_status=draft`、`sent=false`。所有结果 `demo_data=true`。负责岗位是建议角色，尚未向任何人员发消息。

医疗、走失和疑似危险返回 `escalated`；危急关键词先于普通分类提示。缺少位置不会阻止升级，声称事件已处理也不会替代人工确认。无足够分类依据返回 `needs_input`。规则不可用时保守升级，不伪造规则命中。

关键词匹配是有限的演示能力，不提供完整自然语言理解；未识别的表达需要人工补充确认。资源：`resources/incident_rules.json`；测试：`tests/api/test_incident_endpoint.py`。
