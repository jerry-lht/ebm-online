# Q2PICO Benchmark

本 benchmark 评估 Q2PICO 模块：把临床问题转换为 question-level `P/I/C/O` slots。

评估单位是一条 clinical question。runner 会把 method 输出的 `question_pico` 和 gold `P/I/C/O` 对齐，计算 slot-level、micro 和 macro precision / recall / F1。

## 1. 数据来源

完整 dataset builder 从 Hugging Face mirror 下载：

```text
somewordstoolate/Q2CRBench-3 / Clinical_Questions
```

构建命令：

```bash
PYTHONPATH=backend/src:. python benchmark/online_pipeline/benchmark.py build \
  --module q2pico \
  --source q2crbench3 \
  --dataset-name q2crbench3 \
  --seed 42
```

builder 会在 `datasets/q2crbench3/` 下写入完整 `instances.jsonl` 和 `gold.jsonl`，并生成可复现的 `splits/dev`、`splits/test` 和 `splits/smoke`。Q2PICO 使用 seed `42` 做 4:6 dev/test split，并从 dev 中采样 smoke split。

`--limit` 只限制推理和评估数量，不截断已构建 dataset。

## 2. 当前数据分布

<table>
  <thead>
    <tr>
      <th>Dataset</th>
      <th>All</th>
      <th>Smoke</th>
      <th>Dev</th>
      <th>Test</th>
      <th>Schema</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>q2crbench3</code></td>
      <td>99</td>
      <td>10</td>
      <td>40</td>
      <td>59</td>
      <td><a href="datasets/q2crbench3/schema.md">schema.md</a></td>
    </tr>
  </tbody>
</table>

## 3. 数据契约

<table>
  <thead>
    <tr>
      <th>Item</th>
      <th>Fields</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>输入</td>
      <td><code>instance_id</code>, <code>question_text</code>, <code>metadata</code>, <code>source</code></td>
    </tr>
    <tr>
      <td>Gold</td>
      <td><code>P</code>, <code>I</code>, <code>C</code>, <code>O</code></td>
    </tr>
    <tr>
      <td>预测目标</td>
      <td>workflow <code>question_pico</code>，内部字段为 <code>P/I/C/O</code></td>
    </tr>
    <tr>
      <td>指标</td>
      <td><code>micro_f1</code>, <code>macro_f1</code>, per-slot precision / recall / F1</td>
    </tr>
  </tbody>
</table>

## 4. 运行示例

```bash
PYTHONPATH=backend/src:. python benchmark/online_pipeline/benchmark.py run \
  --module q2pico \
  --dataset-name q2crbench3 \
  --split smoke \
  --method gold \
  --run-id q2pico-smoke \
  --judge-mode llm \
  --llm-config llm.local.json \
  --limit 3 \
  --resume \
  --workers 4
```

`--judge-mode normalized` 可用于本地快速确定性检查。LLM judge 模式会在每个 instance 完成后写入 `judge_matches.jsonl`；设置 `--resume` 时会跳过已完成记录。

运行产物写入：

```text
benchmark/online_pipeline/q2pico/runs/<run_id>/
```

跨 run 对比表：

```text
benchmark/online_pipeline/q2pico/runs/metrics_index.csv
```
