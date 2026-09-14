# PandaFlow 作品简介与演示脚本验收记录

验收日期：2026-09-13（Asia/Shanghai）

## 产物

- 材料稿：`docs/competition-presentation-kit.md`
- 内容：提交框简介、一句话定位、封面文字结构、4 分 40 秒完整旁白、逐镜拍摄表、证据位、风险词替换和成片验收清单

## 自动化检查

`tests/package/test_competition_presentation_kit.py` 对以下条件进行回归：

1. 简介去除空白后为 151 字符，位于 120–200 字符范围，并包含六 Skill、安全、动物福利和原型/演示边界。
2. 八段时间轴从 `00:00` 连续衔接到 `04:40`，总长 280 秒，不超过 5 分钟。
3. 六个独立 Skill 名称、四个固定场景 ID、`source_refs`、`rule_refs`、`sent=false` 和真实性标签均出现。
4. 材料明确写明 WorkHub 尚未完成真实联调，并拒绝“已接入 WorkHub”“已上架能力超市”“平台验收通过”等无证据声明。

本里程碑把全量 Python 测试提升为 `133 passed`；前端 Node 测试为 `8 passed`。`compileall`、`uv lock --check` 与 `git diff --check` 同时通过。

## 证据边界

本文档是可直接排练的材料稿，不是已经录制的 MP4，也不是平台提交或锁定证据。正式录制仍需使用当次真实界面、网络结果、测试数字和提交 SHA；WorkHub 画面只有在真实联调完成并脱敏后才能加入成片。
