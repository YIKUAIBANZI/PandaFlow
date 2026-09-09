---
name: operations-review
description: Review allowlisted execution metadata and return descriptive counts with traceable evidence IDs.
---

# Operations Review

用于复盘已脱敏的 Skill 调用元数据。调用 `POST /api/v1/skills/operations-review`：

```json
{"records":[{"record_id":"req_demo1","skill":"incident-triage-dispatch","status":"escalated","rule_refs":["incident_missing_person"],"source_refs":["source_demo_incident_rules"],"demo_data":true,"incident_category":"missing_person","priority":"P1"}]}
```

Python 入口：`review_operations(ReviewRequest(records=[...]))`，位于 `pandaflow.skills.operations_review.service` 与 `.schemas`。

每批最多 1000 条。白名单仅含 record_id、skill、status、rule_refs、source_refs、demo_data、incident_category、priority。编号以 `req_` 开头；其余引用为字母开头的 ASCII 字母、数字、下划线或连字符。skill 必须是项目六个 Skill 之一，status 必须符合统一契约。只有事件 Skill 可携带 incident_category 与 priority。

禁止传原始事件描述、响应 data、联系人、手机号或其他个人字段。白名单是结构校验，调用方仍须确保 ID/引用中未编码个人信息。发现额外字段、无效元数据或重复记录编号时，整批 `rejected` 且不回显输入。空批次 `needs_input`，复盘资源不可用 `degraded` 且不生成统计。

正常输出包含调用总量、按 Skill/状态/事件分类计数、降级次数、规则命中次数、observations 与 rule_update_candidates。每条观察和候选均带 record_ids；同一规则在同一记录中只计一次。候选只供人工审阅，不会自动修改规则。小样本只作描述，`causal_claims=false`，不宣称效率、处置成效或已通知工作人员。

资源：`resources/review_rules.json`；来源登记：`resources/source_registry.json`；测试：`tests/api/test_review_endpoint.py`。演示编排器返回 `execution_records` 可直接作为 records 输入，复盘自己的调用不递归计入该批次。
