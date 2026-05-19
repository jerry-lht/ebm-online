# PI Prompt Ablation Report

日期：2026-05-16

## 1. 目的

本实验比较 Question-to-PICO 中 `P` 和 `I` 两个 slot 的抽取策略，重点验证两个变量：

- few-shot 数量：`3-shot` vs `5-shot`
- I/C 边界规则：`baseline`、`official_only`、`official_plus_order_heuristic`

需要特别说明：`official_plus_order_heuristic` 不是标准 PICO 定义的一部分。它只是为了贴合当前数据集 gold 标注习惯而加入的 dataset-alignment heuristic。它可以作为 benchmark 对齐方案或 ablation 条件，但不应被写成通用、原则化的 PICO 规则。

## 2. Prompt 路线

### 2.1 baseline

当前短 prompt。它只要求抽取 intervention，不额外明确 I/C 边界。

定位：

- 优点：简单，改动少。
- 缺点：I/C 边界不稳定，尤其在 `A or B`、`A versus B`、`A compared with B` 结构中容易抽多、抽少或混入 comparator。

### 2.2 official_only

基于更标准的 PICO 定义：

- I 是被评估的 treatment/intervention/exposure/test/management strategy。
- C 是 alternative/control/comparator。
- 多个选项出现时，不按词序强制判断。
- 不把 comparator、population、outcome、study design 放进 I。

定位：

- 更原则化，更适合写进方法学说明。
- 更符合 PICO 语义边界。
- 不依赖数据集的标注习惯，因此泛化风险更低。
- 但在当前数据集上，硬匹配 F1 不一定最高，因为 gold 标注可能带有固定的“第一个选项作为 I”的偏好。

### 2.3 official_plus_order_heuristic

在 `official_only` 的基础上加入数据集对齐启发式：

- 当问题结构是 `A compared with B` / `A versus B` / `A or B`，且没有其它更明确的语义标记时，优先把第一个临床选项作为 I，后续选项留给 C。

定位：

- 这不是官方 PICO 定义。
- 这是 dataset-alignment heuristic，有一定 trick 成分。
- 它能提高当前 Q2CRBench gold 的匹配度，但可能降低对其它数据集或真实使用场景的原则性。
- 报告时建议把它称为 benchmark-aligned variant，而不是 primary semantic definition。

建议文档表达：

- `official_only`：principled semantic prompt。
- `official_plus_order_heuristic`：benchmark-aligned ablation prompt。

## 3. 实验设置

| 项目 | 设置 |
|---|---|
| 模型 | `gpt-5.4-mini` |
| labels | `P,I` |
| dev split | `results/data/questions.dev20.examples.jsonl` |
| test split | `results/data/questions.test59.examples.jsonl` |
| few-shot 文件 | `results/data/questions.pi_fewshot5.examples.jsonl` |
| 3-shot | few-shot 文件前 3 条 |
| 5-shot | few-shot 文件前 5 条 |
| dev 配置数 | 6 |
| test 配置数 | 6 |

few-shot 示例顺序：

1. `2020 EAN Dementia::1`
2. `2021 ACR RA::61`
3. `2021 ACR RA::17b`
4. `2021 ACR RA::21b`
5. `2024 KDIGO CKD::b6`

## 4. 指标解释

| 指标 | 含义 | 越高/低越好 |
|---|---|---|
| `PI micro F1` | 把 P 和 I 的预测合并后计算 normalized micro F1。主硬匹配指标。 | 越高越好 |
| `P F1` | 只看 population/participants 的 normalized F1。 | 越高越好 |
| `I F1` | 只看 intervention 的 normalized F1。I/C 边界问题主要看它。 | 越高越好 |
| `PI complete` | 单个问题中 P 和 I 的 gold 值是否都完整命中。比 F1 更严格。 | 越高越好 |
| `P complete` | P slot 是否完整命中 gold。 | 越高越好 |
| `I complete` | I slot 是否完整命中 gold。 | 越高越好 |
| `judge accuracy` | LLM judge 判断抽取内容是否语义正确。 | 越高越好 |
| `judge completeness` | LLM judge 判断是否覆盖了应抽取内容。低时表示漏抽或只抽到一部分。 | 越高越好 |
| `judge granularity` | LLM judge 判断抽取边界是否合适。`too broad` 表示抽多，`too narrow` 表示抽少或边界过窄。 | `appropriate` 越高越好 |
| `judge noise` | LLM judge 判断是否夹带无关内容。 | `low noise` 越高越好 |
| `judge strong` | LLM judge 的综合 strong 比例。 | 越高越好 |
| `invalid JSON` | 输出不是合法 JSON 的比例。 | 越低越好 |
| `schema invalid` | JSON 合法但不符合 schema 的比例。 | 越低越好 |
| `empty` | 输出空字符串 value 的比例。 | 越低越好 |
| `duplicate` | 输出重复 value 的比例。 | 越低越好 |

## 5. Dev20 结果

### 5.1 Dev20 主表

| 方法 | shot | PI micro F1 | P F1 | I F1 | PI complete | P complete | I complete | P judge strong | I judge strong | overall judge strong |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| official + heuristic | 5 | **0.3750** | **0.4000** | **0.3500** | 0.0500 | 0.4000 | 0.3500 | 0.9000 | **0.6000** | 0.5500 |
| baseline | 5 | 0.3333 | **0.4000** | 0.2727 | 0.0500 | 0.4000 | 0.3000 | 0.9000 | 0.4000 | 0.4000 |
| official + heuristic | 3 | 0.3250 | 0.3000 | **0.3500** | 0.0500 | 0.3000 | 0.3500 | **0.9500** | **0.6000** | **0.6000** |
| official only | 5 | 0.3210 | **0.4000** | 0.2439 | 0.0500 | 0.4000 | 0.2500 | 0.9000 | 0.5500 | 0.4500 |
| official only | 3 | 0.3171 | 0.3500 | 0.2857 | 0.0500 | 0.3500 | 0.3000 | 0.9000 | 0.5500 | 0.5000 |
| baseline | 3 | 0.2989 | 0.3000 | 0.2979 | 0.0000 | 0.3000 | 0.3500 | 0.9000 | 0.4000 | 0.3500 |

所有 dev20 配置的质量错误均为 0：

| 指标 | 结果 |
|---|---:|
| invalid JSON | 0 |
| schema invalid | 0 |
| empty value | 0 |
| duplicate value | 0 |

### 5.2 Dev20 观察

dev20 上按主指标排序，`official_plus_order_heuristic + 5-shot` 最好：

- `PI micro F1 = 0.3750`
- `I F1 = 0.3500`
- `P F1 = 0.4000`
- `I judge strong = 0.6000`

但这个结果不能直接说明 heuristic 是更好的 PICO 定义。更准确的解释是：

- heuristic 更贴合当前 benchmark 的 gold 标注。
- official_only 更原则化，但和当前数据集的字面 gold 对齐较差。
- baseline 缺少明确 I/C 边界，judge 对 I 的评价最低。

## 6. Test59 结果

最初按 dev 选择规则只跑了 `official_plus_order_heuristic + 5-shot`。随后为了做 test sensitivity，对其它 5 个配置也补跑了 test59。以下 test 结果不应用来继续调 prompt，只用于分析稳定性。

### 6.1 Test59 主表

| 方法 | shot | PI micro F1 | P F1 | I F1 | PI complete | P complete | I complete | P judge strong | I judge strong | overall judge strong |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| official + heuristic | 5 | **0.4237** | 0.3051 | **0.5424** | 0.1356 | 0.3051 | **0.5424** | 0.8983 | **0.8305** | **0.7627** |
| official only | 3 | 0.3730 | 0.3051 | 0.4328 | 0.1186 | 0.3051 | 0.4915 | **0.9492** | 0.5932 | 0.5593 |
| official + heuristic | 3 | 0.3697 | 0.2881 | 0.4500 | 0.1186 | 0.2881 | 0.4576 | 0.9153 | 0.7966 | 0.7119 |
| baseline | 5 | 0.3665 | 0.2712 | 0.4511 | 0.1186 | 0.2712 | 0.5085 | 0.9322 | 0.6271 | 0.5424 |
| baseline | 3 | 0.3569 | **0.3220** | 0.3841 | **0.1695** | **0.3220** | 0.4915 | 0.8983 | 0.5254 | 0.4407 |
| official only | 5 | 0.3548 | 0.2881 | 0.4154 | 0.1186 | 0.2881 | 0.4576 | **0.9492** | 0.6441 | 0.5932 |

所有 test59 配置的质量错误均为 0：

| 指标 | 结果 |
|---|---:|
| invalid JSON | 0 |
| schema invalid | 0 |
| empty value | 0 |
| duplicate value | 0 |

### 6.2 Test59 Judge 细分：P

| 方法 | shot | accurate | complete | partial | appropriate | too broad | too narrow | low noise | strong |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 3 | **1.0000** | 0.8983 | 0.1017 | **0.9661** | 0.0339 | 0.0000 | **1.0000** | 0.8983 |
| baseline | 5 | **1.0000** | 0.9153 | 0.0847 | **0.9661** | 0.0339 | 0.0000 | **1.0000** | 0.9322 |
| official only | 3 | **1.0000** | **0.9492** | 0.0508 | 0.9492 | 0.0339 | 0.0169 | 0.9831 | **0.9492** |
| official only | 5 | **1.0000** | 0.9322 | 0.0678 | **0.9661** | 0.0339 | 0.0000 | 0.9661 | **0.9492** |
| official + heuristic | 3 | 0.9831 | 0.9153 | 0.0847 | 0.9322 | 0.0508 | 0.0169 | 0.9661 | 0.9153 |
| official + heuristic | 5 | 0.9661 | 0.8983 | 0.1017 | 0.9492 | 0.0339 | 0.0169 | 0.9831 | 0.8983 |

P 的主要结论：

- P judge 整体都较好，说明 P 抽取语义大多可接受。
- P 的硬匹配 F1 不高，主要是 phrase 表述和 gold 不完全一致。
- official_only 在 P judge strong 上略好，但这不是本实验主要矛盾。

### 6.3 Test59 Judge 细分：I

| 方法 | shot | accurate | incorrect | complete | partial | missing | appropriate | too broad | too narrow | low noise | strong |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 3 | 0.5424 | 0.0169 | 0.7119 | 0.2712 | 0.0169 | 0.5593 | 0.1356 | 0.0169 | 0.6102 | 0.5254 |
| baseline | 5 | 0.6780 | 0.0339 | 0.7627 | 0.2034 | 0.0339 | 0.6949 | 0.0678 | 0.0678 | 0.7966 | 0.6271 |
| official only | 3 | 0.6610 | 0.0169 | 0.6610 | 0.3220 | 0.0169 | 0.6441 | 0.0678 | 0.1186 | 0.8136 | 0.5932 |
| official only | 5 | 0.6949 | 0.0000 | 0.7119 | 0.2881 | 0.0000 | 0.7288 | 0.0847 | 0.0339 | 0.8136 | 0.6441 |
| official + heuristic | 3 | 0.8475 | 0.0000 | 0.8136 | 0.1864 | 0.0000 | 0.8136 | 0.0508 | 0.0847 | 0.9661 | 0.7966 |
| official + heuristic | 5 | **0.9322** | **0.0000** | **0.8305** | **0.1695** | **0.0000** | **0.8814** | 0.0678 | 0.0508 | **0.9831** | **0.8305** |

I 的主要结论：

- baseline 的 I/C 边界最弱，尤其 3-shot：
  - `accurate = 0.5424`
  - `appropriate = 0.5593`
  - `low noise = 0.6102`
- official_only 比 baseline 更干净，但硬匹配和 I judge 不如 heuristic。
- heuristic 在当前 test59 上明显更贴合 gold：
  - `I F1 = 0.5424`
  - `I accurate = 0.9322`
  - `I complete = 0.8305`
  - `I appropriate = 0.8814`
  - `I strong = 0.8305`

## 7. 如何解读 heuristic

虽然 heuristic 在 dev20 和 test59 上都表现最好，但不建议把它表述为“更正确的 PICO 定义”。

更合适的解释：

- 当前 Q2CRBench gold 对 `A or B` / `A versus B` / `A compared with B` 结构可能存在第一个选项更常作为 I 的标注习惯。
- heuristic 捕捉了这个标注习惯，所以硬匹配和 judge 都提升。
- 但这是一种 benchmark-alignment，不一定能泛化到其它临床问题数据集。

因此建议保留两个方案：

### 7.1 原则化推荐：official_only

用于真实系统、方法学描述、泛化优先场景。

推荐理由：

- 符合标准 PICO 边界。
- 不依赖词序。
- 可解释性更强。
- 不把数据集 gold 的潜在偏差固化成规则。

限制：

- 当前 benchmark 硬匹配不如 heuristic。
- 对 gold 中隐含的 first-option 标注习惯不敏感。

### 7.2 Benchmark 对齐方案：official_plus_order_heuristic

用于当前数据集报告、benchmark 分数、ablation 对照。

推荐理由：

- dev20 和 test59 上都是最高硬匹配。
- I judge 也明显更高，说明不是纯格式投机。
- 对当前数据集的 I/C 边界更贴合。

限制：

- 有 trick 成分。
- 不应宣称为官方 PICO 规则。
- 对其它数据集可能过拟合。

## 8. 最终建议

建议在报告中同时落两条线：

1. `official_only` 作为 principled semantic prompt。
2. `official_plus_order_heuristic` 作为 benchmark-aligned ablation prompt。

如果目标是严谨方法学和真实部署，优先采用 `official_only`，并接受它在当前 benchmark 上的硬匹配损失。

如果目标是当前 Q2CRBench 的结果对齐和排行榜式评估，可以报告 `official_plus_order_heuristic + 5-shot`，但必须明确说明它使用了 dataset-alignment heuristic，不能把它包装成通用 PICO 定义。

本轮实验的技术结论是：

- `official_plus_order_heuristic + 5-shot` 在 dev20 和 test59 上均为最高分配置。
- `official_only` 更原则化，但当前数据集上的 gold-alignment 较弱。
- 后续如果继续优化，建议优先做 P phrase normalization 和更稳定的 I/C 边界标注解释，而不是继续增加词序 heuristic。

