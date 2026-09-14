# 首个 Skill 的 WorkHub 联调样例

生成日期：2026-09-14。来源：本地 FastAPI ASGITransport 实际调用；未从 WorkHub 发出，未证明公网 HTTP 可达。请求日期为生成当天，联调时请改为计划演示日期。

目标：POST {BASE_URL}/api/v1/skills/visitor-policy-check，Content-Type: application/json。

| 请求文件 | 预期 HTTP | 预期业务状态 | 平台需要验证的分支 |
|---|---|---|---|
| normal.request.json | 200 | ok | data.eligible=true，保留 demo_data=true、规则与来源 |
| missing-entry-slot.request.json | 200 | needs_input | data.eligible=null、missing_fields 包含 entry_slot；走补充信息分支，不是成功分支 |
| invalid-entry-slot.request.json | 422 | 无业务包络 | HTTP 校验失败，不映射为 ok，不继续下游路线 |

同名 response.json 为本地响应记录，外层 http_status 和 body 仅用于样例文档；API 实际返回的是 body 内部对象。request_id 和 generated_at 每次调用变化，平台不应绑定样例中的固定值。

## 接入顺序

2026-09-14 已另行在 `https://pandeflow.yikuaibanz.cn` 通过这三组请求的公网测试，证据见 `evidence/https-deployment-2026-09-14/public-smoke.json`；本目录响应仍保留原始本地记录。公开 Demo 无需鉴权。先记录平台真实字段和可接受的鉴权方式。把已有服务的 HTTPS 地址填入 API 节点；不存在地址时不要使用 localhost、合成 URL 或本地样例冒充在线调用。额外鉴权、超时与重试以登录后界面为准。

将三个 request.json 的内容分别粘贴到请求体测试，保存实际请求、返回状态与分支结果。截图需隐藏账号和密钥。确认 needs_input 和 HTTP 422 均不会触发普通游览链路。

首个 Skill 验证通过后再扩展到六个独立 Skill，检查三条完整调用链，最后用平台实际导出文件重新导入并复现。目录中的 JSON 是请求/响应样例，不是 WorkHub manifest 或平台导出包。

## 服务侧自查命令

仅在已经配置好授权部署地址的终端中设置 PANDAFLOW_BASE_URL；不要在共享命令或日志中放密钥。

```bash
curl --fail-with-body --max-time 20 "$PANDAFLOW_BASE_URL/ready"
curl --fail-with-body --max-time 20 \
  -H 'Content-Type: application/json' \
  --data-binary @docs/workhub-smoke/normal.request.json \
  "$PANDAFLOW_BASE_URL/api/v1/skills/visitor-policy-check"
```

这只是服务侧检查。WorkHub 节点成功、返回字段映射、导出和上架仍需在平台单独验收。
