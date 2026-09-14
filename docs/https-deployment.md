# PandaFlow HTTPS 部署

目标域名：pandeflow.yikuaibanz.cn（按用户提供的拼写）。本次授权：将现有原型部署到用户指定服务器并开放 HTTPS Demo 与六 Skill API。

## 部署设计

复用服务器现有 Caddy，增加独立域名站点；保留已有站点。独立 systemd 账户 pandaflow 运行 Uvicorn，监听 127.0.0.1:8010，由 Caddy 代理并自动管理证书。应用无真实工单写入、无数据库、无付费模型调用，作为公开演示服务无需账号登录。64KB 请求体、32 个并发和 512MB 服务内存限制用于约束演示资源消耗；不代表完整流量防护。

只上传构建 wheel、锁定依赖清单与必要服务配置，不上传内部项目记录或本地 git 历史。安装路径为 /opt/pandaflow/releases/<版本>/venv；/opt/pandaflow/current 链接指向当前版本。配置文件为 deploy/pandaflow.service 与 deploy/pandaflow.caddy。

## 发布与回滚

上传后核对 SHA-256，使用 pip --require-hashes 安装锁定运行依赖，再 --no-deps 安装项目 wheel。服务账户不可写安装目录。先通过服务本机 /ready 与三组请求验收，再备份当前 Caddyfile、追加站点，验证成功后 reload。

若应用发布失败，恢复 current 指向上一已验证版本并重启 pandaflow；首次部署没有上一版时停止该服务。若 Caddy 修改失败，保留原配置；reload 后异常时恢复本次备份并校验后 reload。不执行整机重启，不覆盖其他站点。

## 验收与边界

检查有效 TLS 证书、HTTP 到 HTTPS 跳转、/demo、/ready、OpenAPI、三个预约样例及四个演示场景。实际天气失败时允许标明 fixed_fallback 的 degraded，不能视为实时成功。

公网服务可访问与 WorkHub 平台验收分开：登录后字段、鉴权支持、独立 Skill 触发、编排回传、导出重导入和上架仍需平台证据。

官方配置依据：[Caddy reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)、[Automatic HTTPS](https://caddyserver.com/docs/automatic-https)。

## 2026-09-14 实际部署结果

公开 Demo：https://pandeflow.yikuaibanz.cn/demo；交互文档：https://pandeflow.yikuaibanz.cn/docs；Base URL：https://pandeflow.yikuaibanz.cn。演示接口匿名开放，仅接收演示输入。

部署应用代码版本 `cb48982`，Python 3.12，wheel SHA-256：`c12731650cd4e8d41cf511e363a897b93eea2a919b9961ee4e39af51c87cec34`。锁定依赖清单 SHA-256：`24d66c56be35c741aba8cd3464e33eaa792375532e0ba2bddc49c8298e708ccd`。后续文档与运维脚本提交不会改变本次 wheel 的应用代码。

证书由 Let's Encrypt 签发，TLS 1.3 且主机名验证通过；证书有效期为 2026-09-14 至 2026-12-13（UTC）。HTTP 返回 308 到 HTTPS，站点根路径返回 302 到 /demo。原有 Caddy 配置内容逐字节保留，已有站点响应正常。systemd 开机启动已启用，当前 active/running、NRestarts=0；应用仅监听 127.0.0.1:8010。超过 64KB 的测试请求返回 413。

公网测试记录见 `evidence/https-deployment-2026-09-14/public-smoke.json`：三组预约请求与四个场景通过。本次实时天气为 `open_meteo`，观测时间 2026-09-14 14:00 +08:00，抓取时间 14:05 +08:00；不代表后续每次都会联网成功。

Chromium 浏览器实际点击四场景，均收到 HTTP 200；实时场景显示 Open-Meteo 及观测/抓取时间。1440px 与 375px 无横向溢出，控制台 0 error / 0 warning。截图同目录。API 文档、方案书、蒸馏包已回填公网状态，但仍是平台待验的材料初稿。

复验命令（运行时需 httpx，日期按 Asia/Shanghai 更新）：

```bash
python scripts/verify_public_demo.py https://pandeflow.yikuaibanz.cn --output evidence/public-smoke.json
```

构建与发布所需的运行依赖可由 `uv export --frozen --no-dev --no-emit-project --output-file requirements.txt` 导出，再用 `uv build --wheel` 生成应用包。公网可达并不证明 WorkHub 已调用成功；下一步是在真实平台里使用上述 Base URL 完成字段映射和回传。
