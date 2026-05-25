# Medical Article Risk of Bias Assessment

基于LLM的医学文章风险评估系统，使用Cochrane Risk of Bias (RoB 1.0) 标准评估RCT研究的方法学质量。

## 架构设计

**当前推荐评估流程：Direct domain judgement**

最终任务定义为：

```text
input: sr_pico + xml_content + risk_of_bias_domain
output: risk_of_bias_judgement
```

因此当前主线 workflow 不再先做全局 Stage 1 摘要，也不默认跑 post-hoc calibration，而是对每个 domain 直接检索 article/XML 中最相关的 source excerpts，再一次性输出 judgement、support_text、support_context 和简短 audit rationale。

```text
Step 1: Domain-specific retrieval
  Input: xml_content + domain
  Output: 与该 domain 相关的 Methods/Results/Outcome/Attrition/Blinding 片段

Step 2: Direct domain judgement
  Input: sr_pico + domain + domain-specific source excerpts + RoB 1.0 criteria
  Output: Low risk / High risk / Unclear risk
```

`source-grounded calibration` 曾作为 Step 3 默认开启，但在 346 篇 full run 中触发 241 个 domain，最终只有 73 个和 GT 一致（30.3%）。它尤其容易用脆弱关键词误改 `Blinding outcome assessment`，所以现在降级为显式 ablation：默认关闭，只在需要测试后处理/label-prior calibration 时用 `--calibration` 或 `CALIBRATION=1 scripts/run_full_eval.sh` 打开。

我们试过 `targeted` evidence-map、`evidence` 全局证据表、扩大上下文窗口、`audited` guardrail 和 post-hoc calibration。它们都没有稳定超过 `direct`，其中全局 evidence table 明显会压缩掉 blinding/attrition 细节，calibration 则容易把边界规则过拟合成关键词后处理。因此当前代码默认 `--mode direct` 且 calibration off；其它模式保留用于实验和 ablation，不作为主结果。

推荐数据集：

- `rob_article_only_dataset/`：主报告用。它是 XML-only 任务最公平的数据集，排除了 ground truth 明显依赖作者邮件、protocol、registry、review notes 等外部信息的样本。
- `rob_core_dataset/`：补充报告用。它保留所有 schema-clean core RoB 样本，但可能包含 XML 之外证据。
- `rob_cleaned_dataset/`：原始 matched 数据，不建议直接作为最终 benchmark，因为里面混有非目标 domain、`Not applicable`、冲突 judgement、诊断工具 domain 等脏数据。

可选实验模式：

- `--mode hybrid`：先抽方法学摘要，再结合 source excerpts 判断。
- `--mode strict`：严格两阶段，Stage 2 只看 Stage 1 摘要。
- `--mode joint`：一次调用同时判断 5 个 domains。
- `--mode evidence`：先抽全局 evidence table，再判断。当前实测会丢细节，不推荐主用。
- `--mode targeted`：复杂 domain 输出 evidence_map 后直接判断。当前实测过于保守，不推荐主用。
- `--mode audited`：direct 主判断 + evidence_map guardrail。接近 direct，但未稳定超过 direct。

**评估维度（5个domains）：**
1. Random sequence generation（随机序列生成）
2. Allocation concealment（分配隐藏）
3. Blinding of participants and personnel（参与者和人员盲法）
4. Blinding of outcome assessment（结果评估盲法）
5. Incomplete outcome data（不完整结果数据）

## 安装

```bash
cd medical_agent
pip install -r requirements.txt

# API配置已在 .env 文件中
# 使用 OpenAI API (通过 SiliconFlow)
```

## 使用

### 单篇文章评估

```bash
python src/main.py --pmid 32306943
# 默认从 rob_article_only_dataset/ 查找 PMID；如需查 core:
python src/main.py --pmid 32306943 --dataset-dir rob_core_dataset
```

### 与ground truth对比

```bash
python src/main.py --pmid 32306943 --compare
```

### 比较不同评估模式

```bash
# 推荐默认：direct domain judgement
python src/main.py --pmid 32306943 --compare --mode direct

# 严格两阶段：只用 Stage 1 摘要判断，用来诊断信息压缩损失
python src/main.py --pmid 32306943 --compare --mode strict

# 一起打：一次调用同时判断 5 个 domain
python src/main.py --pmid 32306943 --compare --mode joint
```

### 当前推荐批量评估命令

20 篇快速 dev/evolution run：

```bash
python src/batch_eval.py \
  --dataset-dir rob_article_only_dataset \
  --limit 20 \
  --mode direct \
  --model gpt-5-mini \
  --timeout 180 \
  --domain-context-max-chars 8000 \
  --max-tokens 4096 \
  --reasoning-effort minimal \
  --max-retries 1 \
  --concurrency 4 \
  --no-support-filter
```

100 篇 collaborator run：

```bash
python src/batch_eval.py \
  --dataset-dir rob_article_only_dataset \
  --limit 100 \
  --mode direct \
  --model gpt-5-mini \
  --timeout 180 \
  --domain-context-max-chars 8000 \
  --retry-timeout 180 \
  --retry-domain-context-max-chars 4000 \
  --max-tokens 4096 \
  --reasoning-effort minimal \
  --max-retries 1 \
  --concurrency 4 \
  --no-support-filter
```

全量 run 推荐直接用脚本：

```bash
# 默认跑 rob_article_only_dataset 全量，输出到 eval_runs/full_eval/<timestamp>/
scripts/run_full_eval.sh

# 先检查会跑多少篇和实际命令，不发 API 请求
DRY_RUN=1 scripts/run_full_eval.sh

# 跑 schema-clean core 全量作为补充结果
DATASET_DIR=rob_core_dataset scripts/run_full_eval.sh

# 如需先重新清洗数据再跑
CLEAN_FIRST=1 scripts/run_full_eval.sh
```

输出会写入 `eval_runs/<timestamp>/batch_results.json` 和 `eval_runs/<timestamp>/report.md`。`batch_eval.py` 会在每篇文章结束后 checkpoint，所以中途失败也能保留已完成结果。

`--no-support-filter` 在 cleaned dataset 上表示按目录全量取样，不再做 support phrase 预筛选。`--retry-*` 参数用于超时后自动用更短上下文重跑该 study。

输出示例：
```
Direct mode: Judging each domain from PICO + source excerpts...
  Evaluating Random sequence generation...
    → Low risk
  Evaluating Allocation concealment...
    → Unclear risk
  ...

COMPARISON WITH GROUND TRUTH
✓ Random sequence generation
   LLM:          Low risk
   Ground Truth: Low risk
...
Accuracy: 4/5 (80.0%)
```

## 项目结构

```
medical_agent/
├── src/
│   ├── schemas.py      # Pydantic数据模型
│   ├── prompts.py      # prompt模板（direct主线 + experimental modes）
│   ├── evaluator.py    # 评估编排器
│   ├── clean_dataset.py # 数据清洗脚本
│   ├── batch_eval.py   # 批量评估 + audit report
│   └── main.py         # 单篇CLI入口
├── scripts/
│   └── run_full_eval.sh # 全量评估脚本
├── rob_cleaned_dataset/      # 原始 matched 数据
├── rob_core_dataset/         # schema-clean 5-domain benchmark
├── rob_article_only_dataset/ # XML-only 主 benchmark
├── requirements.txt
└── README.md
```

## 后续优化方向

1. **区分 article-only 与 review-context 评估**
   - 目前默认只使用 XML/article text，不把 ground truth 的 `support_text` 喂给模型。
   - GT support 可以用于错误挖掘、few-shot 设计和 workflow evolution，但不能作为 held-out 评估输入，否则会泄漏答案。
   - 一些 GT 来自作者邮件、review notes、protocol、registry 或图表/补充材料；这些应该单独进入 review-context split。

2. **Attrition / CONSORT flow 数字解析**
   - `Incomplete outcome data` 目前最低，主要卡在 randomized/analyzed/missing by arm、dropout reasons、ITT/LOCF/MI/sensitivity 的结构化解析。
   - 单纯更大上下文或全局 evidence table 已验证不稳定；下一步更像是表格/flow 数字抽取问题。

3. **Blinding role / outcome type 解析**
   - `Blinding outcome assessment` 需要区分 participant、clinician、interviewer、coder/adjudicator、statistician。
   - 对 self-report / objective device / blinded central reader 做更强的 evidence retrieval 和 role classification。

4. **批量评估**
   - 固定 train/dev/test split
   - 计算各 domain 的准确率、article-observable 准确率、Kappa 系数
   - 并行处理多篇文章

## 模型配置

默认使用 `.env` 中的 `BASE_MODEL`。也可以通过 CLI 覆盖：

```bash
python src/main.py --json-path rob_cleaned_dataset/32306943.json --compare --model gpt-5-mini
python src/batch_eval.py --limit 20 --model gpt-5-mini
```

或在代码中指定：

```python
evaluator = RoBEvaluator(
    model="gpt-5-mini",
    max_tokens=4096,
)
```

或在 `.env` 文件中修改 `BASE_MODEL`、`REQUEST_TIMEOUT`、`DOMAIN_CONTEXT_MAX_CHARS` 等变量。校准层默认关闭；如需做 ablation，可显式开启：

```bash
python src/batch_eval.py --dataset-dir rob_article_only_dataset --limit 20 --mode direct --model gpt-5-mini --calibration --no-support-filter
CALIBRATION=1 scripts/run_full_eval.sh
```

### 当前基线（204453）

推荐 dev 配置（`scripts/run_full_eval.sh` 默认）：`MODE=direct`，`CALIBRATION=0`，`DOMAIN_CONTEXT_MAX_CHARS=100000`，`gpt-5-mini`，50 篇 `rob_article_only_dataset`。

参考 run `eval_runs/full_eval/20260516_204453`：**146/250 (58.4%)**，article-only scorable **32/56 (57.1%)**。详见 `EBM-Online/experiments/risk-of-bias/README.md` 中的对比表。

注意：2026-05-16 的 346 篇 full run 是在旧默认 calibration on 下跑出的，整体 `973/1730` (`56.2%`)；calibration 触发命中率过低，不再作为默认。

Calibration-off smoke/probe：

- Run: `eval_runs/step3_ablation/20260516_170737`
- `rob_article_only_dataset` first20 overall: `61/100` (`61.0%`)
- 同一批旧 calibration-on full-run slice: `63/100` (`63.0%`)
- 解释：20 篇样本太小，不能证明 calibration off 更准；但 full-run calibration 触发命中率过低，所以 calibration 不再作为默认主流程。

历史参考：

- Run: `eval_runs/20260514_core100_optimized`
- `rob_core_dataset` first100 overall: `294/500` (`58.8%`)
- 同一批中属于 `rob_article_only_dataset` 的 XML-only subset: `247/405` (`61.0%`)

`rob_core_dataset` first100 domain accuracy：

- Random sequence generation: `80/100` (`80.0%`)
- Allocation concealment: `69/100` (`69.0%`)
- Blinding participants/personnel: `57/100` (`57.0%`)
- Blinding outcome assessment: `48/100` (`48.0%`)
- Incomplete outcome data: `40/100` (`40.0%`)

`rob_article_only_dataset` subset domain accuracy：

- Random sequence generation: `65/81` (`80.2%`)
- Allocation concealment: `56/81` (`69.1%`)
- Blinding participants/personnel: `50/81` (`61.7%`)
- Blinding outcome assessment: `39/81` (`48.1%`)
- Incomplete outcome data: `37/81` (`45.7%`)

Workflow evolution 结论见 `eval_runs/20260514_target_domain_workflow_evolution.md`：`targeted`、`evidence`、`audited`、扩大上下文和 self-consistency 在同一批 20 篇上都没有稳定超过 `direct`，所以当前主线保持 `direct`。

## 数据格式

输入 JSON 格式（推荐来自 `rob_article_only_dataset/` 或 `rob_core_dataset/`）：
```json
{
  "pmid": "32306943",
  "study_id": "Leis 2020",
  "xml_content": {
    "sections": [
      {"section": "Background", "text": "..."},
      {"section": "Methods", "text": "..."},
      ...
    ]
  },
  "risk_of_bias": [
    {
      "domain": "Random sequence generation",
      "judgement": "Low risk",
      "support_text": "...",
      "source": "study_json"
    },
    ...
  ]
}
```

输出格式：
```json
{
  "study_id": "Leis 2020",
  "pmid": "32306943",
  "llm_assessment": [
    {
      "domain": "Random sequence generation",
      "judgement": "Low risk",
      "support_text": "...",
      "support_context": [
        {
          "source": "article",
          "quote": "...",
          "relevance": "..."
        }
      ],
      "evidence_map": null,
      "source": "llm_assessment"
    },
    ...
  ],
  "ground_truth": [...]
}
```

`support_text` 是面向 Cochrane 格式的短解释；`support_context` 是模型实际引用的证据片段和来源，用于调试 prompt/workflow。`evidence_map` 只在 `targeted`/`audited` 实验模式中填充，主线 `direct` 通常为 `null`。`source` 常见取值包括 `article`、`methodology`、`evidence_table`、`review_context`、`not_reported`。
