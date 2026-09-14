# PandaFlow API 文档 PDF 验收记录

验收时间：2026-09-13 21:38 CST（UTC+08:00）

## 产物

- 源文档：`docs/PandaFlow-API接口文档.md`
- 生成器：`scripts/build_api_pdf.py`
- 提交用初版：`output/pdf/PandaFlow-API接口文档.pdf`
- PDF SHA-256：`cedde3bff162d70271098e58b09c581dc83937dd1f3213c705716b8fbd3ead1e`

## 内容门禁

API 文档门禁从当前 FastAPI `app.openapi()` 枚举全部方法与路径，要求 Markdown 同步覆盖；新增的精确响应门禁检查六个独立 Skill 与总控各自引用独立 200 响应组件、`data` 字段拒绝未声明属性，并用真实 API 调用证明响应序列化没有改变既有 JSON wire contract。文档同时锁定 WorkHub 路线字段为实际的 `data.itinerary`。全量结果：`137 passed`。

## 文件与视觉门禁

1. 使用项目外置的 Codex 文档运行时和 ReportLab 4.4.9，从 Markdown 生成 PDF。
2. `pdfinfo` 验证产物为未加密 A4、PDF 1.4，共 8 页，无 JavaScript。
3. `pdftoppm -png -r 110` 渲染全部 8 页并逐页目检：中文、表格、代码、标题、页眉和页码清晰；未见截断、重叠、越界或乱码。
4. 使用 pypdf 6.10.0 重新打开并提取 9310 个字符；`PandaFlow`、六个 Skill 名称、`WorkHub`、`七类精确响应模型`、`data.itinerary` 与“未完成边界”均可检索。
5. 公开白名单 ZIP 构建测试通过，ZIP 内包含 Markdown、PDF 和生成器；README 本地链接检查通过。

## 全量回归

- Python：`137 passed`
- JavaScript：`8 passed`
- `python -m compileall -q src scripts`：通过
- `uv lock --check`：通过
- 9 个 `resources/*.json`：解析通过
- `git diff --check`：通过

## 证据边界

本验收证明 API PDF 本地初版内容完整、可读取且可重复生成，不证明 WorkHub 已联调或平台已接受该文件。PDF 中 `{BASE_URL}`、鉴权、平台变量映射和导出 schema 必须在真实平台恢复并完成联调后回填，再重新生成最终冻结版。

## 2026-09-14 公网部署回填

本节覆盖前述历史产物哈希和“公网地址待回填”状态。已回填 https://pandeflow.yikuaibanz.cn、公开 Demo 无鉴权边界及 WorkHub 待联调状态；API PDF 重新生成后仍为 8 页，全部页面渲染并目检，封面单独更新复验。全量 146 Python、8 JavaScript 通过。当前 PDF SHA-256：`7803c2f1966bdfc3a6ad2bc9a836c0072e17ce269567c344dd377dbebf564481`。公网证据见 docs/https-deployment.md，平台字段仍待实际调用。
