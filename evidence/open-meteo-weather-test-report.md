# Open-Meteo 天气适配验收

日期：2026-09-08。范围：Open-Meteo 当前天气适配、固定演示回退及其与既有福利风险/路线编排的集成；天气适配器不是第七个 Skill。

## 官方接口核验

实施前重新核对 Open-Meteo 官方 Forecast API、Licence 和 Terms：`/v1/forecast` 接受经纬度及 `current` 变量；当前条件可返回 2 米温度、体感温度、降水、天气码和 10 米风速；API 错误使用 HTTP 400 JSON；数据采用 CC BY 4.0 并要求在展示数据旁提供 Open-Meteo 链接。免费开放端点限非商业使用，商业部署需使用对应付费方案。

本实现只访问固定 `https://api.open-meteo.com/v1/forecast`，请求上述五个字段、摄氏度、km/h、mm 和 `Asia/Shanghai` 时区。一个 3.0 秒总 deadline 覆盖连接和全部分块读取，响应最多读取 64 KiB；错误、截断响应、异常体积、非法 JSON、缺字段、错误单位、错误时区/时间和非有限数均拒绝进入规则核心。

## 自动化结果

基线 60 项。本轮新增适配器 URL/参数/总 deadline、完整解析、截断响应、非法单位、非有限数、缺字段、响应上限、上海日历日期与时间元数据、合成输入、固定回退、来源防伪/登记、实时高温改线、断网降级和紧急事件优先等用例。

独立代码审查提出的总超时、截断响应、主机时区和来源防伪问题均已有回归测试并完成修复。修复后 `.venv/bin/python -m pytest -q`：**78 passed**；`.venv/bin/python -m compileall -q src`、全部资源 JSON 解析和 `git diff --check` 通过。

## 断网 HTTP 验收

在 FastAPI ASGI 路径中强制让天气依赖抛出安全适配异常，再调用 `POST /api/v1/demo/run`。结果：HTTP 200、业务状态 `degraded`、`weather.source=fixed_fallback`、`replanned=true`；底层异常文本未进入响应。

固定回退为显式合成数据：33°C、体感 36°C、降水 0 mm、WMO 码 1、风速 8 km/h。它触发现有演示高温规则并避开室外节点，不冒充实时观测或官方场馆规则。

## 真实网络烟测

在获准联网的本地进程中调用固定 Open-Meteo 端点成功。审查加固后的 2026-09-08 13:11（`Asia/Shanghai`）复验解析到：温度 26.0°C、体感 28.4°C、降水 0 mm、天气码 3、风速 12.3 km/h、观测时间 `2026-09-08T13:00:00+08:00`；输出包含 `Weather data by Open-Meteo.com` 和 `https://open-meteo.com/`。该数值只证明调用当时的响应契约，不是可长期复用的天气结论，也不作为自动化测试前置条件。

## 边界

实时模式只用于访问上海日历当天的 current 条件；其他日期立即使用固定回退并标记 `degraded`，避免把当前观测错配到未来行程。独立福利 Skill 只把收到的数值标记为 `caller_supplied`，不接受调用方自称 Open-Meteo 来源；可信来源、地点、观测时间和署名只由编排器拥有的天气边界输出。当前福利决策仍只对已批准的演示温度阈值采取动作；体感、降水、天气码和风速先作为可追踪证据保留，未在缺少规则来源时擅自增加决策阈值。客流、园区图、福利阈值和回退天气仍是合成演示数据。
