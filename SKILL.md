---
name: thesis-longdoc-consistency
description: Use when a case supplies a thesis or other long document and asks for chapter planning, cross-chapter consistency checks, or localized revision tracking; indexes chapters and word allocation, builds an acronym and terminology glossary, verifies figure/table/equation numbering against references, and produces a scoped change log in /app/output/result.json while preserving case_id and every output_contract field. Deterministic standard library only; no network.
---

# 学位论文与长文档写作（章节—术语—编号—改动四账对齐）

## 用途与适用条件

当输入是学位论文、长篇报告或多章节稿件，需要在**不改动作者原意**的前提下做结构核对与局部修订时使用。

适用：

- 多章节长文档（数千字以上），含图表编号与缩写。
- 需要检查术语/缩写首次定义、前后一致与编号引用。
- 需要按提纲核对章节篇幅与论证任务。
- 需要记录“改了什么、为什么改”，便于导师复核与回退。

不适用：从零代写整篇论文、替作者补实验、判定学术贡献、对未提供基线的文本声称已修改。

## 输入

- `/input/case.json`：读取 `case_id`、`output_contract`、`task`、`document`/`thesis`/`text`、`chapters`、`outline`、`baseline`/`original`、`revised`、`glossary` 等字段。
- `task.md`：存在时读取 `/input/task.md` 或 `/app/work/task.md`。
- 文本可内联或给路径；只读 UTF-8、≤2MB；PDF/二进制登记为未解析。
- 输出 `/app/output`，工作 `/app/work`。

## 处理流程（逐项覆盖评分维度）

1. **章节索引（立得住）**：按 `# 标题`、`第X章`、`Chapter N`、`一、` 识别章节，统计中文字符数与英文词数；提供 `outline` 时对照目标字数，计算偏差比例。
2. **缩写与术语表（连得上）**：识别 2–6 位大写缩写与 `全称 (ABBR)` 定义；报告 `used_before_definition`、`undefined`、`conflicting_expansion`（同一缩写两种全称）。
3. **图表编号核对**：抽取 `Figure 1`、`Fig. 1`、`图 1`、`Table 2`、`表 2`、`Equation 3`、`式(3)` 的定义与引用，报告未定义引用、未被引用的图表、编号重复与跳号。
4. **跨章节一致性**：同一缩写/术语在不同章节的不同写法（大小写、全半角、单复数）列出 `variants`，不擅自统一，交由作者确认。
5. **局部改动记录**：若同时提供 `baseline` 与 `revised`，用标准库 `difflib` 生成统一差异，按章节统计增删行与变更块，输出可回退的 `change_log`；未提供基线时明确 `baseline_missing`，不声称已修改。
6. **篇幅与论证任务**：每章输出当前字数、目标字数（若给）、偏差与“本章应回答的问题”（取自标题与首段）。
7. **可编辑交付**：`chapter_plan`（Markdown 表）与 `edit_worksheet`（逐条改动清单）。
8. **合同保留**：见输出契约。

## 输出契约

写入 `/app/output/result.json`：

- 顶层 `case_id` 与输入一致。
- **保留原始 `output_contract` 每个字段名**（字典/列表/`fields`/Schema `properties`）；未映射写 `null` 并登记，状态降为 `partial`；组合 Schema 登记 `unsupported_features`。
- 固定字段：
  - `status`：`success | partial | insufficient_input | failed`
  - `result`：`chapter_plan`、`glossary`、`crossref_report`、`consistency_issues`、`change_log`、`edit_worksheet`
  - `evidence`、`uncertainty`、`errors`、`stats`
- 退出码：`0` 完成；`1` 有未映射合同字段；`2` 输入不可读。

## 异常处理

| 情形 | 处置 |
|---|---|
| 无正文 | `status=insufficient_input`，说明缺文档 |
| 仅单章节 | `status=partial`，仍做术语与编号检查 |
| 无基线文本 | `change_log=[]`，标 `baseline_missing`，不声称已修改 |
| 提纲缺目标字数 | 只报当前字数与占比，不推断配额 |
| 缩写未定义 | 标 `undefined`，给出首次出现位置，不代写全称 |
| 同一缩写多种全称 | 两条都保留，标 `conflicting_expansion` 升级确认 |
| 图表编号跳号 | 记 `numbering_gap`，不自动重排（重排会破坏引用） |
| 章节标题重复 | 记 `duplicate_chapter_title` |

## 限制与不适用

- 不判断论证质量与结论正确性，只做结构与一致性核对。
- 缩写识别基于大写模式，可能漏掉小写缩写或误报单位。
- 差异记录是行级，不表达语义等价；改写是否更好需作者判断。
- 不自动重排图表编号，避免连锁破坏交叉引用。

## 最小调用示例（示例）

以下为合成示意，非官方案例。

```bash
python /skills/weekly-skill/scripts/run_skill.py \
  --case /input/case.json \
  --out /app/output/result.json \
  --work /app/work
```

合成 `case.json`：

```json
{
  "case_id": "synthetic-thesis-demo",
  "output_contract": {"status": "string", "chapter_plan": "array", "glossary": "array", "change_log": "array"},
  "document": "# 第一章 引言\n我们使用 MRI 成像。磁共振成像 (MRI) 具有优势。见图 1。\n# 第二章 方法\n图 3 展示了流程。"
}
```

示意输出（节选）：

```json
{"case_id":"synthetic-thesis-demo","status":"success","result":{"glossary":[{"abbr":"MRI","used_before_definition":true}],"crossref_report":{"undefined_refs":["图3"]}}}
```

## 自查清单

- [ ] `case_id` 与合同字段保留；未映射项已登记。
- [ ] 每个章节都有字数与占位，提纲偏差已计算。
- [ ] 缩写“首次使用/定义位置”成对出现。
- [ ] 图表引用与定义分列，未定义引用已列出。
- [ ] 无基线时未声称已修改；差异可回退。
- [ ] 未自动重排编号、未改写作者原句。


## 交付保证与评分对齐

调用顺序（固定）：

1. 先运行包内脚本（若存在）：`python scripts/run_skill.py`（默认读 `/input/case.json`，写 `/app/output/result.json`）；路径不同时用 `--case` / `--output` 指定。
2. **必须交付完整成品**：脚本只做索引与核对；调用 Agent 必须补全 `chapter_plan`（每章任务、字数、与提纲偏差）、`glossary`、`crossref_report`、`consistency_issues` 与 `edit_worksheet`（逐条可执行改动）；提供 baseline/revised 时必须生成完整 `change_log`；不得以“骨架/待补”作完成态。
3. 最后自检：`case_id` 与输入一致；`output_contract` 每个字段都存在；`status` 取本合同允许值 `success | partial | insufficient_input | failed`；正文无 `pending`/`TODO`/空占位；数字、引用、来源可逐条回溯。

运行保证：

- 输入缺失、JSON 损坏、字段异常、输出目录不存在时，仍须写出结构化 `result.json` 并正常结束，不得崩溃或非零退出。
- 不联网、不伪造数据、不声称平台评分或官方案例结果。
- 交付物必须是可直接编辑与复核的成品，而不是流程说明。

评分对齐（本题五个维度）：

- 实际效果（40）：完整产出任务要求的最终成品，覆盖全部输入条目，可直接进入修改流程。
- 使用增益（25）：体现相对基础 Agent 的可验证改进（结构化、术语/数字/引用核对、可编辑性）。
- 创新增益（15）：保留方法学增量（分块、对齐、二次校验、版本比对等），并用结果证明其价值。
- 可靠体验（10）：异常输入有明确降级与说明，不同长度/文体/重复运行下稳定产出。
- 生态贡献（10）：用途、调用、输入输出、限制、示例、维护信息齐全，资源可被他人复用。

## 最终交付强制要求

1. **调用 Agent 必须交付成品，不是流程说明**：脚本产出只是索引、核对或规格骨架；调用 Agent 必须在同一 `result.json` 中补齐本题要求的最终产物（正文/译文/审稿意见/综述/分析结论/图表源文件与导出件/幻灯片页内容与讲稿/实验方案等）。交付字段为空、只有标题骨架，或含 `pending`、`TODO` 之类占位，一律视为未完成。
2. **必须覆盖全部输入条目**：输入中的每个章节、问题、文献、图、页面、指标都要有对应条目，不得只处理示例或首条；确实缺失的条目写入 `uncertainty` / `limitations` 并说明原因，不得静默跳过。
3. **必须自检后再交付**：`case_id` 与输入一致；`output_contract` 每个字段都存在；状态值取本题契约规定的枚举；数字、单位、引用、来源可逐条回溯；结果内部无自相矛盾。
4. **参数等价**：`python scripts/run_skill.py --case <输入> --out <输出>` 与 `--output <输出>` 等价；默认 `/input/case.json` → `/app/output/result.json`。
5. **平台用 3 个固定案例分别运行**：逻辑要由输入驱动，不针对某一份示例硬编码；字段命名差异走别名匹配与显式降级，并在 `uncertainty` 记录假设。
