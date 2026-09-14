# PandaFlow 四场景 Web Demo 验收

## 2026-09-12 审查修复复验

在 `codex/audit-remediation` 上使用真实 Chromium 重新逐个运行 A–D 四场景。常规场景显示 `演示规则检查通过`、75 分钟路线、P3 未发送失物草稿和登记知识卡；合成高温场景从 77 分钟改为 47 分钟且最终路线避开竹林；走失场景只显示有限关键词事件门禁，明确未执行入园、路线或天气检查；实时场景成功显示 Open-Meteo 的上海时区观测和独立抓取时间。

1440×1000 与 375×812 视口均满足 `scrollWidth == clientWidth`，无横向溢出；控制台 0 error / 0 warning。截图为 `evidence/development-audit-2026-09-11/remediation-desktop.png` 和 `remediation-mobile.png`。本次 fresh gate 为 128 项 Python 与 8 项 JavaScript 测试全绿；以下内容保留 2026-09-10 初版页面的历史验收记录。

日期：2026-09-10
实现分支：`codex/web-demo`
最后一个浏览器修复提交：`acbbd1a`

## 验收范围

本报告覆盖由 FastAPI 同进程托管的原生 HTML、CSS、JavaScript 演示页，以及四个固定场景的浏览器交互。它证明本地评委演示流可用，不代表 WorkHub 已联调、平台已验收或最终参赛材料已经完成。

演示页入口：`GET /demo`。场景目录：`GET /api/v1/demo/scenarios`。每个场景仍调用既有 `POST /api/v1/demo/run`，页面没有复制安全、天气或路线规则。

## 自动化验证

```text
.venv/bin/python -m pytest -q
85 passed

node --test tests/web/test_view_model.mjs
5 passed, 0 failed

.venv/bin/python -m compileall -q src
exit 0

git diff --check
exit 0
```

Python 新增测试覆盖页面与静态资源、四场景目录、上海时区当天日期规范化、资源故障脱敏、语义区和真实性标签、不安全 DOM/浏览器存储禁用，以及响应式状态样式。JavaScript 测试覆盖高温改线、人工升级、固定回退、未知状态和缺失可选字段。

## 浏览器黑盒结果

浏览器在 `http://127.0.0.1:8765/demo` 依次运行四个场景：

1. **常规六 Skill：** 显示 `ok / 安全完成`，路线保持不变；失物处置明确为 `draft`、`sent=false`；知识回答与五次实际 Skill 调用的运营复盘可见。
2. **合成高温改线：** 初始路线包含“竹林步道”，最终路线不含该节点，并明确显示“竹林步道：已避开”；路线 Skill 在调用链中出现两次。
3. **走失转人工：** 显示 `escalated / 需要人工介入`、P1、`sent=false`；普通天气与路线区不出现；预设请求中的“儿童走失”原文未出现在 DOM。
4. **实时天气：** 本次联网验收成功读取 Open-Meteo，显示 18.6°C、体感 20.1°C、3 km/h、带 `+08:00` 的观测时间及可见署名链接。既有自动化测试另行证明联网失败时会返回固定高温快照并保持 `degraded`。

浏览器控制台最终为 **0 error / 0 warning**。页面无外部字体、图片、地图 SDK 或前端构建依赖；图标使用内嵌 SVG，不产生 `/favicon.ico` 404。

## 响应式与键盘

- 390×844 视口下 `scrollWidth=390`、`innerWidth=390`，无横向溢出；场景、结果、证据和边界声明均保留。
- Tab 顺序依次到达跳转链接、“开始演示”、四个场景按钮和运行按钮。
- Enter 与 Space 均可选择场景，`aria-pressed` 正确更新；运行区域使用 `aria-busy`，结果区域使用 `aria-live`，升级状态使用 `role=alert`。
- 焦点有可见轮廓；状态同时使用中文、英文码、符号和颜色；减少动态效果偏好受到尊重。

## 截图证据

- `evidence/web-demo/normal.png`
- `evidence/web-demo/heat-replan.png`
- `evidence/web-demo/human-escalation.png`
- `evidence/web-demo/live-or-degraded.png`
- `evidence/web-demo/mobile-live.png`

## 真实性边界

页面持续显示 `Prototype`、`Demo Data`、`No Real Dispatch`。园区图、规则、客流和回退天气均为合成演示；实时天气是模型生成的网格条件，不代表场馆运营或动物健康状态。页面不收集或存储姓名、手机号、证件号，不发送工单，不诊断，不确认事件已解决，也不声称与成都大熊猫繁育研究基地合作。

WorkHub 官方导入样例、平台上架和平台验收仍未获得证据；PDF、MP4、封面与最终提交包仍是后续里程碑。
