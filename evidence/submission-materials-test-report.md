# 参赛材料与知识卡验收记录

日期：2026-09-14。版本基线：知识卡里程碑 8543e25，后续材料提交见 git 历史。本记录仅证明本地结果。

## 行为验证

新增主张前执行 tests/unit/test_panda_knowledge_guard.py：4 failed / 11 passed，失败均为新中英文主题没有登记证据。新增两张卡后专项单元/API 为 17 passed；全量 Python 为 146 passed。逐卡遍历全部中英文检索词，检查来源登记、公开 URL、返回答案与 source_refs。

原有实时状态、医疗拒答与无依据答案行为继续通过；新主题同样先执行拒答门禁。有限关键词无法证明自然语言全覆盖，未扩展为真实动物状态判断。

2026-09-14 12:55 执行原开发审查 reproduce.py，F01-F07 全部 issue_detected=false；156 组限定高温偏好中的 unsafe_ok_cases=0。node --test tests/web/test_view_model.mjs 为 8 passed，compileall 通过。没有复用旧绿灯替代本轮回归，也没有把离线脚本结果说成浏览器或平台实测。

## PDF 产物

生成命令：使用含 reportlab 的 Python 运行 scripts/build_submission_pdfs.py。渲染使用 pdftoppm，文本重解析使用 pypdf。

| 文件 | 页数与状态 | SHA-256 |
|---|---|---|
| output/pdf/PandaFlow-行业应用方案书.pdf | 6 页 A4，未加密，本地初稿 | ef3f18e5c2fbd809a9f1804c7189255da2700ca4e97dc4f222c7ed3f446ae42c |
| output/pdf/PandaFlow-公开资料蒸馏包.pdf | 6 页 A4，未加密，本地初稿 | c0fb3d9dd75be427e0efdc428bb83ea2fb420a38e22c194da98bf4c14b5db0c6 |

所有页面已渲染检查，并对六 Skill 表、技术边界表、知识卡表及来源转化表放大检查；没有文字重叠、表格越界或缺字黑框。每页可提取文字并保留“本地初稿”标记；封面、页码、来源链接与未完成边界已检查。长 Skill 名在窄表格中允许跨行显示，源文件保留完整标识。

## 已交付与仍未完成

已完成：三张中英文来源绑定卡；六项公开来源复核及映射；行业应用方案书与公开资料蒸馏包 Markdown/PDF 本地初稿；可重复运行的生成脚本。

未完成：真实 WorkHub 字段及鉴权、六 Skill 独立触发、三条平台调用链、平台导出/重新导入、公网 HTTPS、能力超市上架、最终 MP4 和正式提交。公开资料蒸馏包没有专家访谈或内部 SOP，不宣称蒸馏深度已获评审认可。

## 首个 Skill 的本地联调样例

`docs/workhub-smoke/` 保存 2026-09-14 通过 ASGITransport 实際请求产生的三组 JSON：正常为 HTTP 200/ok，缺时段为 HTTP 200/needs_input，非法时段为 HTTP 422 且错误不回显原输入。三组均执行状态与关键字段断言。样例不等于 WorkHub 或公网访问证据。

## 作品封面

内置 imagegen 已生成并保存 `output/imagegen/PandaFlow-作品封面-v1.png`（1672×941，RGB）。标题、副标题、角标、底部边界与六节点插画已目检，生成记录与 SHA-256 见 `docs/cover-generation-record.md`。仍待平台真实尺寸/文件大小字段验证和用户审美反馈。

## 白名单交付验证

逐文件 manifest 导出包含 110 个文件；连续构建两次字节一致。扫描文本条目未命中本机用户绝对路径、常见私钥/Token 模式，且无 .git 历史、AGENTS.md 或 mmr.md。检查证明本轮白名单包的内容边界，不代表远端仓库已更新。

## 2026-09-14 HTTPS 回填版本

方案书与蒸馏包均回填公网 Demo 状态，重新生成后各 6 页；全部页面经 Poppler 渲染、目检和 pypdf 重解析，无截断或越界，域名与 WorkHub 边界可检索。以下哈希覆盖本记录的历史产物哈希：

- PandaFlow-行业应用方案书：`5b95449a760aac86d6b079ca3565fb1f7a10086988671fb9e781e8d3b345a59f`
- PandaFlow-公开资料蒸馏包：`80b92c2b60071d564db496ff225d93c2016566677e0bac714be43e32e04f9234`
