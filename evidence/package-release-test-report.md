# PandaFlow 安装与导出验收记录

日期：2026-09-11

环境：macOS arm64、CPython 3.11.14 / 3.13.12、uv 0.10.1、pip-audit 2.10.1

## 结论

- wheel 包含 9 个 JSON 规则/场景资源、6 份 Skill 文档和 4 个 Web 静态文件。
- wheel 安装到源码检出目录之外后，可读取场景资源并加载 FastAPI 应用。
- 临时 wheelhouse 下载完成后，新虚拟环境使用 `--offline --no-index` 成功安装 PandaFlow 及 16 个运行时依赖。
- 离线安装环境内 `/health`、`/demo`、`/api/v1/demo/scenarios` 通过 ASGI 烟测；场景目录为 4 项。
- 逐文件 manifest 白名单源码 ZIP 连续构建两次字节一致，并固定跨系统 ZIP 元数据；它先读取不可变内容快照，拒绝文件或目录符号链接及校验读取竞态，写入失败不会留下部分最终产物。未列入 manifest 的文件不会入包，README 的本地证据链接均有效，且不含 `AGENTS.md`、`mmr.md`、`.env`、`.pyc` 或 `__pycache__`。
- `uv lock --check` 通过。由 `uv.lock` 导出的带哈希运行时 requirements 经 `pip-audit 2.10.1` 检查，16 个依赖中未发现当时数据库记录的已知漏洞；原始 JSON 见 `dependency-audit.json`。

## 自动化验证

```text
.venv/bin/python -m pytest -q
98 passed

CPython 3.11.14 独立环境运行同一测试集
98 passed

node --test tests/web/test_view_model.mjs
5 passed

.venv/bin/python -m compileall -q src
通过

uv lock --check
通过
```

## 边界

离线安装使用的依赖 wheelhouse 是针对本次 macOS arm64 / CPython 3.13 环境临时生成的验收材料，不提交为跨平台分发包。仓库中的可复现 ZIP 是源码白名单包；通用安装仍需按目标平台从锁文件解析兼容 wheel。漏洞审计是 2026-09-11 的时间点结果，不是持续安全担保。
