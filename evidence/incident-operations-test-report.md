# 事件分诊与运营复盘验收

日期：2026-09-06。范围：第五、第六个独立 Skill，以及六 Skill 演示编排；不代表整个参赛包验收完成。

## 自动化结果

原有 22 项基线通过。本轮增加六类分诊、高风险优先、缺失输入、依赖失败、复盘白名单与重复编号、事件中断、真实调用计数和审查回归用例。

最终 `python -m pytest -q --junitxml=evidence/incident-operations-tests.xml`：**60 passed**。`python -m compileall -q src`、`git diff --check` 均通过。

独立审查发现并修复：高风险文字出现在 area/measures_taken 时漏拦；HTTP 422 回显非法输入值/字段名。两项均先用失败测试复现，再修复，审查复验相关 40 项通过。

## 真实运行

可编辑安装构建完成。发现 macOS 隐藏工作树的 `.pth` 路径文件带 UF_HIDDEN 标记会被 Python 3.13 跳过；采用显式源路径验证：函数运行 `PYTHONPATH=src`，Uvicorn 启动 `--app-dir src`。

实际启动 Uvicorn 于本机 `127.0.0.1:8767`，使用 HTTP 客户端验证 `/health` 及以下三项 `/api/v1/demo/run`，均 HTTP 200，服务在检查后正常关闭。

| 场景 | 业务状态 | 复盘统计调用数（不含复盘自身） |
|---|---|---|
| normal_all_skills | ok | 5，六个 Skill 均参与（含复盘） |
| heat_replan | ok | 4，包含两次独立路线调用 |
| human_escalation | escalated | 1，普通规划未执行 |

`incident-operations-demo.json` 保存三个场景的函数实际执行结果，含请求编号、时间、规则/来源引用及脱敏调用元数据；已验证所有顶层来源引用存在于来源登记表。

## 限制

规则、场景与统计均为合成演示。没有真实派单、实时天气读取或 WorkHub 联调。完整自然语言分诊、知识守卫来源覆盖、导出包资源可安装性、前端和正式提交材料仍待后续里程碑。当前测试证明本轮明确行为，不是对全量自然语言输入的安全承诺。
