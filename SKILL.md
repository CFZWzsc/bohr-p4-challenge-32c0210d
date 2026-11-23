---
name: thesis-longdoc-consistency
description: Use when a case supplies a thesis or other long document and asks for chapter planning, cross-chapter consistency checks, or localized revision tracking; drafts the requested sections from supplied material, builds chapter/word allocation, acronym and terminology glossary, verifies figure/table/equation numbering, and records per-claim sources plus a scoped change log in /app/output/result.json while preserving case_id and every output_contract field. Deterministic standard library only; no network.
---

# 学位论文与长文档写作（章节—术语—编号—改动四账对齐）

## 用途与适用条件

当输入是学位论文、长篇报告或多章节稿件，需要按提纲产出指定章节，并在**不改动作者原意**的前提下做结构核对与局部修订时使用。

适用：

- 按提纲/任务写指定章节，篇幅与论证任务可对照。
- 多章节长文档（数千字以上），含图表编号与缩写。
- 需要检查术语/缩写首次定义、前后一致与编号引用。
- 需要记录“改了什么、为什么改”，便于导师复核与回退。

不适用：替作者补实验或编造材料外结果；判定学术贡献；在无材料时凭空代写。

## 输入

- `/input/case.json`：读取 `case_id`、`output_contract`、`task`、`document`/`thesis`/`text`、`chapters`、`outline`、`baseline`/`original`、`revised`、`glossary`。
- `task.md`：存在时读取 `/input/task.md` 或 `/app/work/task.md`。
- 文本可内联或给路径；只读 UTF-8、≤2MB；PDF/二进制登记为未解析。
- 输出 `/app/output`，工作 `/app/work`。

## 处理流程

1. **章节索引**：按 `# 标题`、`第X章`、`Chapter N`、`一、` 切章，统计中英文字数；提供 `outline` 时计算目标字数偏差。
2. **章节成品**：按提纲/任务为每章写出可用正文 `deliverables.draft`，只依据输入材料；缺材料处登记 `needs_human_confirmation`，不虚构。
3. **缩写与术语**：识别 2–6 位大写缩写与 `全称 (ABBR)` 定义；报告 `used_before_definition`、`undefined`、`conflicting_expansion`。
4. **图表编号**：抽取 `Figure/Fig./图/Table/表/Equation/式` 的定义与引用，报告未定义引用、未被引用的图表、编号重复与跳号。
5. **跨章节一致性**：同一缩写/术语在不同章节的写法变体列入 `variants`，不擅自统一。
6. **局部改动**：有 `baseline`+`revised` 时用 `difflib` 出差异；无基线时逐条登记本次改动（`before`/`after`/`reason`/`locator`）。
7. **来源映射**：每条论断、数字、引用给出 `locator`（`文件#行区间` 或 `章节 行`）与来源，供逐条回溯。
8. **可编辑交付**：`chapter_plan`、`edit_worksheet`、`needs_human_confirmation`，并保留合同。

## 输出契约

写入 `/app/output/result.json`。脚本产出 `chapter_plan/glossary/crossref_report/consistency_issues/change_log/edit_worksheet/document_text/sources/evidence/stats`；调用 Agent 在同一文件补齐 `deliverables`、`claim_sources`、`needs_human_confirmation`。

| 字段 | 类型 | 含义 | 示例（合成） |
|---|---|---|---|
| `case_id` | string | 与输入一致，不被合同字段覆盖 | `"case-x"` |
| `status` | enum | `success/partial/insufficient_input/failed` | `"success"` |
| `result.deliverables` | array | 每章成品：`section/title/target_words/draft/basis`，`draft` 是正文而非提纲 | `{"section":"2.1","title":"方法","draft":"…","basis":["case.json#L40-L88"]}` |
| `result.claim_sources` | array | 论断/数字/引用→定位与来源；`locator` 不得为空 | `{"claim":"样本 120 例","locator":"document L57","source":"case.json"}` |
| `result.chapter_plan` | array | 字数、目标字数、偏差、本章应回答的问题 | `{"chapter":1,"words":820,"target_words":900,"deviation":-0.09}` |
| `result.glossary` | array | 缩写定义、首次使用、冲突全称 | `{"abbr":"MRI","defined":true,"conflicting_expansion":false}` |
| `result.crossref_report` | object | 图表/公式的定义、引用、未定义引用、跳号 | `{"figure":{"undefined_refs":[3]}}` |
| `result.consistency_issues` | array | 每条含 `type`、`locator`（章节+行）、`detail` | `{"type":"numbering_gap","locator":"2.1 L12","detail":"图3未定义"}` |
| `result.change_log` | array | 有基线时为行级差异；无基线时逐条登记本次改动 | `{"locator":"2.1 L8","before":"…","after":"…","reason":"统一缩写"}` |
| `result.edit_worksheet` | string(Markdown) | 章节—字数—偏差表 + 问题清单 | `"# Edit Worksheet …"` |
| `result.needs_human_confirmation` | array | 材料缺口、结论冲突、需作者确认处 | `{"item":"结论冲突","locator":"3.2 L44","reason":"与 2.3 相反"}` |
| 顶层 `evidence` | array | 章节级证据（脚本已给 `snippet`），补 `locator` 与原文 `quote` | `{"locator":"2.1 L8-L12","quote":"…"}` |
| `uncertainty/errors/stats` | array/object | 不确定、异常、统计 | — |
| `output_contract` 各字段 | 保留 | 每个字段名都存在；未映射写 `null` 并记 `contract_status.unmapped_fields` | — |

## 异常处理

| 情形 | 处置 |
|---|---|
| 无正文 | `status=insufficient_input`，说明缺文档 |
| 仅单章节 | `status=partial`，仍做术语与编号检查 |
| 无基线文本 | `change_log` 记本次改动；未改动则写空数组，不声称已修改 |
| 提纲缺目标字数 | 只报当前字数与占比，不推断配额 |
| 缩写未定义/多种全称 | 标 `undefined` 或 `conflicting_expansion`，给出首次出现位置，不代写全称 |
| 图表编号跳号 | 记 `numbering_gap`，不自动重排（重排会破坏引用） |
| 材料缺口/结论冲突 | 写入 `needs_human_confirmation`，不静默跳过 |

## 限制与不适用

- 不判断论证质量与结论正确性，只做结构、一致性与写作交付。
- 缩写识别基于大写模式，可能漏掉小写缩写或误报单位。
- 差异记录是行级，不表达语义等价；改写是否更好需作者判断。
- 不自动重排图表编号，避免连锁破坏交叉引用。

## 最小调用示例（示例，非官方结果）

```bash
python /skills/weekly-skill/scripts/run_skill.py --case /input/case.json --out /app/output/result.json --work /app/work
```

```json
{"case_id":"synthetic-demo","output_contract":{"status":"string","chapter_plan":"array"},
 "document":"# 第一章 引言\n我们使用 MRI 成像。磁共振成像 (MRI) 具有优势。见图 1。\n# 第二章 方法\n图 3 展示了流程。"}
```

示意：`status=partial`，`glossary` 标出 `MRI` 未定义，`crossref_report.figure.undefined_refs` 含 `3`，`deliverables` 按章给出正文。

## 交付与自检

1. 先执行 `python scripts/run_skill.py`（默认 `/input/case.json` → `/app/output/result.json`；`--case`、`--out`、`--output` 等价）。
2. 脚本只做索引与核对；`deliverables.draft` 必须是可编辑成品正文，不得为空、`pending`、`TODO` 或只有标题骨架。
3. 输入缺失、JSON 损坏、输出目录不存在时仍写出结构化 `result.json`；脚本正常结束时退出码恒为 0，失败类别只看 `status`。
4. 自检：`case_id` 一致；`output_contract` 每字段存在；`claim_sources` 每条有 `locator`；`needs_human_confirmation` 覆盖材料缺口与冲突；未自动重排编号、未改写未授权原句。
