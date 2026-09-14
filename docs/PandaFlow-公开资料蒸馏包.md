# 熊猫守望 PandaFlow 公开资料蒸馏包

> 2026-09-14 本地初稿 · 资料汇总、逻辑转化说明、来源清单 · 无专家访谈或内部 SOP

## 01 蒸馏范围与证据等级

本包记录公开资料如何进入六个独立 Skill，供评审沿来源、卡片/规则、执行结果和测试逐项追溯。项目不将机构名称当作“蒸馏完成”的证明，也不声称访谈过园区专家或取得企业内部操作文件。

**verified：** 一条具体陈述受到本次读取的公开来源支持。例如进食文章中的主食、握竹结构与进食时间相关事实。它只描述该主张的证据状态，不表示园区认证了 PandaFlow。

**inferred：** 根据公开场景提出的产品设计，例如把路线限制与风险状态合并，或把结构化记录用于复核。推断需要实验验证，不能作为经营成效。

**demo：** 为固定故事构造的园区图、温度阈值、区域关闭、事件分级和复盘规则。即使设计灵感来自官方网页，合成规则仍需保留 demo_data=true。

## 资料汇总

| 资料 | 提炼内容 | 本包不作的外推 |
|---|---|---|
| 官方票务与开放时间 | 预约/时段/证件有条件，开放受季节影响 | 不把演示字段核验等同全部入园资格 |
| 官方游客须知 | 区域开放可能受保育、维护和天气影响 | 不据此编造实时关闭、温度阈值或内部 SOP |
| 官方科普：进食 | 主食、伪拇指握竹、进食与消化利用关系 | 不判断具体动物当前在哪、吃多少或是否健康 |
| Open-Meteo 文档与条款 | 天气字段、时间和来源解释 | 不把模型天气当园区传感器或动物状态 |
| 本地设计与测试 | 约束合并、人工升级、可追溯记录 | 不声称已获企业采纳或产生实测业务收益 |

<!-- pagebreak -->

## 02 从事实到知识卡

本轮复核的是基地官方“进食”文章。第一段支持竹类主食及伪拇指握竹结构，第三段支持消化利用与较长进食时间的关系。没有复制图片或全文，中文答案为短句转述，英文答案为项目翻译，均绑定 source_panda_base_diet。

| 卡片 | 典型问题 | 输出主张 |
|---|---|---|
| card_diet | 大熊猫主要吃什么？ / What do giant pandas eat? | 主食为高纤维竹类 |
| card_pseudo_thumb | 大熊猫为什么有伪拇指？ / How do giant pandas grip bamboo? | 伪拇指与其他趾协同握竹 |
| card_feeding_time | 大熊猫为什么花那么长时间进食？ / Why do pandas spend so much time eating? | 竹类消化利用率低，需要较多进食以获取能量 |

## 实际转换步骤

1. 在 resources/source_registry.json 登记来源 ID、精确文章 URL、标题、发布者、访问日期和适用 Skill。
2. 在 resources/knowledge_cards.json 写入原子主题、中文与英文检索短语、简短答案和 source_ref。每个主题只输出来源支持的物种事实。
3. 先检查医疗与实时状态意图，再检索卡片；没有匹配证据返回 needs_input，答案为空；医疗问题返回 rejected。
4. HTTP 包络保留来源与状态，调用者不得把拒答转换成自行生成的科普结论。

## 一条可复核记录

输入 How do giant pandas grip bamboo?，language=en。知识 Skill 返回 ok、包含 pseudo-thumb 的解释、source_panda_base_diet，以及 rule_registered_knowledge_only。单独的公开知识事实可返回 demo_data=false；这不改变使用合成路线的总控演示边界。

对同一问题增加 right now 时，实时意图先被拦截，返回 needs_input 且 answer=null、source_refs=[]。对带 treatment 的医疗问题则拒绝诊断。这里只证明列明输入的规则行为，不声称有限关键词覆盖所有自然语言变体。

<!-- pagebreak -->

## 03 从场景到业务规则

六个 Skill 并非都有可直接照抄的官方算法。下表明确区分公开事实与项目自行设计的执行机制，避免将“有参考来源”误写为“官方规则已落地”。

| Skill | 来源或设计依据 | 当前执行机制与证据 |
|---|---|---|
| visitor-policy-check | 官方票务背景；demo 规则 | 缺失时段返回 needs_input；检查演示预约状态及证件类型。tests/unit/test_visitor_policy_check.py |
| accessible-itinerary-planner | 合成园区图；公开辅助游览背景 | 预算、无台阶标记、禁行集合和偏好约束；tests/unit/test_accessible_itinerary_planner.py |
| welfare-risk-dispatcher | 官方关闭/防暑背景；demo 阈值 | 合并全部有效禁行节点再复验最终路线；tests/unit/test_welfare_risk_dispatcher.py |
| panda-knowledge-guard | 已核验进食科普文章 | 三张双语登记卡、医疗/实时拒答优先；tests/unit/test_panda_knowledge_guard.py |
| incident-triage-dispatch | 项目合成六类分诊矩阵 | 高风险信号优先，人工升级且 sent=false；tests/api/test_incident_endpoint.py |
| operations-review | 项目元数据聚合规则 | 拒绝未知字段、重复编号，只形成有证据编号的观察；tests/api/test_review_endpoint.py |

## 调用链里的约束传递

总控保留初始请求、有效约束和执行记录。风险 Skill 的完整 active_avoid_nodes 传给路线规划，最终返回前再次检查交集；只要仍包含禁行节点就不能作为可执行成功路线。

事件入口先于普通路线与天气调用执行。高风险升级不能被票务语义、复盘成功或天气降级覆盖。复盘只反映本次调用的元数据，既不建立因果，也不声称现场事件已经解决。

这两条是项目实施并测试的确定性不变量。其正确性证据来自本地代码和用例，不能替代真实岗位流程、道路和现场安全验收。

<!-- pagebreak -->

## 04 验证、来源更新与缺口

新增伪拇指与进食时间主题之前，四条中英文事实用例均失败；增加资源卡后通过。测试还遍历每张卡片的中英文登记检索词，检查答案、来源 ID 及公开来源登记，防止新增卡片无法检索或引用悬空。

来源测试验证结构与绑定，**不会自动证明网页内容支持答案**。语义依据仍需回到本包第 02 节的段落定位和公开文章进行复核。新增网页时，应先读取全文相关段落，再提炼单一主张和双语转述。

## 更新流程

公开网页变化后，先记录旧主张、新主张、访问日期和差异，不静默覆盖已发布材料。若事实依据消失，暂停对应知识卡或改为拒答；若仅入口改变，核实新页面身份与正文后再更新 URL。修改答案、触发条件或规则行为时补充失败用例，随后执行专项与全量回归。

合成规则的变更必须注明设计原因和验证范围。温度阈值、关闭节点或分诊优先级不能因为 source_ref 指向官方网站，就自动升级为 verified。用户输入也不能改变规则来源的证据等级。

## 尚未完成的行业蒸馏深度

目前证据来自公开服务说明与科普文章，没有专家经验访谈、企业 SOP 授权或真实业务日志。三张科普卡来自同一篇文章，主题覆盖有限；其扩充提高可追溯性，但不等于已经达到评委对“深度蒸馏”的要求。

若继续真实试点，应请有授权的机构人员核对规则与边界，采集场馆开放变更、真实道路可达性、人工分诊岗位流程和人工服务案例。实际访谈、授权和实测完成前，相关部分保持待验证，不补写虚构姓名、访谈摘录或成效数字。

## 本地验证与平台分界

146 项 Python 回归是本地工程证据。2026-09-14 公网 Demo（https://pandeflow.yikuaibanz.cn/demo）四场景验收通过；公开演示接口无需登录，不执行真实工单。平台导出、重新导入、六 Skill 独立触发、三条真实调用链和能力超市条目仍需实际证据。本 PDF 是公开资料蒸馏说明的本地初稿，不能充当 WorkHub 导出包或平台认可证明。

<!-- pagebreak -->

## 05 领域知识来源清单

以下页面于 2026-09-14 核验。只列已用于本包主张或设计背景的一手来源，未使用园区图片、官网长篇原文或用户私人资料。

- S1 [官方英文票务信息](https://www.panda.org.cn/en/service/ticket/)。登记 ID：source_base_ticket_en。位置：Online Real-Name Reservation 与 Ticket Types。用途：识别当前原型没有覆盖全部例外。
- S2 [官方游客须知](https://m.panda.org.cn/cn/service/notice/)。登记 ID：source_base_visitor_notice。位置：参观须知第一条、温馨提示。用途：关闭与防暑的多因素背景。
- S3 [官方开放时间](https://www.panda.org.cn/cn/service/opentime/)。登记 ID：source_base_opening_hours。位置：基地开园时间、熊猫塔参观须知。用途：明确季节与设施边界尚未实现。
- S4 [官方科普：进食](https://www.panda.org.cn/yd/education/database/kpzs/2025-06-05/8786.html)。登记 ID：source_panda_base_diet。位置：正文第一、三段。用途：三张中英文科普卡。
- S5 [Open-Meteo API 文档](https://open-meteo.com/en/docs)。登记 ID：source_open_meteo_forecast。用途：天气字段、单位与时间解释。
- S6 [Open-Meteo 使用条款](https://open-meteo.com/en/terms)。登记 ID：source_open_meteo_license。用途：服务条款与天气来源署名。商业使用需另核实适用方案。

## 来源附件与复现索引

resources/source_registry.json：来源元数据。resources/knowledge_cards.json：检索词与双语答案。resources/visitor_rules.json、park_graph.json、welfare_rules.json、incident_rules.json、review_rules.json、weather_config.json：演示规则和资源。

evidence/source-review-2026-09-14.md：本轮主张映射及平台观察时间。evidence/submission-materials-test-report.md：本轮回归与 PDF 验收。docs/workhub-integration-runbook.md：平台尚缺字段与验收定义。

## 提交声明

本包按“公开资料汇总、知识转换说明、来源清单”组织。没有编造专家、合作或内部材料；项目译文与设计推断均不冒充官方文本。最终提交前需统一代码、PDF、公开 Demo 与视频版本，并按真实平台状态回填交付信息。
