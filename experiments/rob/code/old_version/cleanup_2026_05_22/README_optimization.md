# RoB Domain Criteria Optimization

## 背景

基于之前的实验结果对比，发现新版本在某些领域有显著提升，但在其他领域有所下降：

### 新版本 vs 老版本性能对比

| 领域 | 老版本 | 新版本 | 变化 |
|------|--------|--------|------|
| Random sequence generation | 80.0% | 72.04% | **-7.96%** ⚠️ |
| Allocation concealment | 69.0% | 67.74% | -1.26% |
| Blinding of participants | 57.0% | 55.0% | -2.0% |
| Blinding of outcome assessment | 48.0% | 54.44% | **+6.44%** ✅ |
| Incomplete outcome data | 40.0% | 62.77% | **+22.77%** 🎯 |
| **Overall** | **58.8%** | **62.67%** | **+3.87%** |

## 优化目标

**保持成功的改进，同时恢复下降的性能：**

1. ✅ **保持** Incomplete outcome data 的突破性提升 (62.77%)
2. ✅ **保持** Blinding of outcome assessment 的改进 (54.44%)
3. 🎯 **恢复** Random sequence generation 到 ~80%
4. 🎯 **恢复** Allocation concealment 到 ~69%
5. 🎯 **总体目标**: 从 62.67% 提升到 65%+

## 优化策略

### 1. Random Sequence Generation (目标: 80%)

**问题诊断**：
- 原prompt过于严格，要求明确的随机方法描述
- "randomized" 一词单独出现被判定为 Unclear
- 很多论文会说 "randomized" + 上下文线索（如 "computer-generated", "block randomization"），这应该足够判定为 Low risk

**优化方案**：
```python
# 添加宽松指导
"Be reasonably PERMISSIVE for Low risk: if the paper describes randomization
with sufficient detail to suggest a proper random method was used, Low risk
is appropriate even without exhaustive methodological detail."

# 扩展 Low risk 判定路径
- "Randomized" + context clues → Low risk
  例如: "computer-generated", "block randomization", "stratified randomization",
       "central randomization", "pharmacy randomization"
```

**关键改进**：
- ✅ "computer-generated randomization" → Low risk (不再是 Unclear)
- ✅ "block randomization" → Low risk (隐含了正确的随机序列)
- ✅ "randomization by statistician" → Low risk (暗示了正确方法)

### 2. Allocation Concealment (目标: 69%)

**问题诊断**：
- 原prompt设置 "Default is Unclear"，过于保守
- 要求 "EXPLICIT description"，标准过高
- 很多论文不直接描述concealment，但可以从其他信息合理推断

**优化方案**：
```python
# 从 "Default is Unclear" 改为平衡判断
"Be BALANCED in your judgement: Unclear is common for this domain (many papers
don't describe concealment), but when there are reasonable clues that concealment
was likely adequate, Low risk is appropriate."

# 添加合理推断路径
- "Central randomization" / "pharmacy randomization" → Low risk
  (这些设计本身就隐含了隐藏分配)
- "Randomization by independent person after enrollment" → Low risk
- "Double-blind placebo-controlled with identical appearance" → Low risk
  (盲法隐含了隐藏)
```

**关键改进**：
- ✅ "central randomization" → Low risk (不再是 Unclear)
- ✅ "pharmacy randomization" → Low risk (设计隐含concealment)
- ✅ 双盲 + 相同外观 → Low risk (可合理推断)

### 3. 保持成功的改进

**Incomplete Outcome Data** (保持 62.77%):
- ✅ 保持 "Be reasonably PERMISSIVE" 指导
- ✅ 保持多路径判定 Low risk
- ✅ 保持避免过度判定 Unclear 的指导

**Blinding of Outcome Assessment** (保持 54.44%):
- ✅ 保持客观性考量指导
- ✅ 保持 "objective outcomes → Low risk even if unblinded"
- ✅ 保持常见错误避免指南

## 文件说明

### 核心文件

1. **`domain_specs_optimized.py`** - 优化后的领域标准
   - 改进了 Random sequence generation 和 Allocation concealment 的判定标准
   - 保持了 Incomplete outcome 和 Blinding outcome 的成功改进
   - 详细的注释说明了每个改动的原理

2. **`run_experiment_optimized.py`** - 优化版实验运行脚本
   - 使用 `domain_specs_optimized.py` 中的标准
   - 其他逻辑与 `run_experiment.py` 完全相同
   - 输出到 `results/predictions_optimized/` 目录

3. **`compare_results.py`** - 结果对比工具
   - 对比 baseline 和 optimized 版本的性能
   - 生成详细的对比表格
   - 显示每个领域的改进/下降情况

4. **`quick_test.py`** - 快速测试脚本
   - 在前20个研究上快速验证优化效果
   - 自动运行 baseline → optimized → compare 流程
   - 适合快速迭代和验证

### 原始文件（保留作为对比）

- `domain_specs.py` - 原始领域标准（v5 hybrid）
- `run_experiment.py` - 原始实验脚本

## 使用方法

### 方法 1: 快速测试（推荐先运行）

```bash
# 在前20个研究上快速验证优化效果
python quick_test.py
```

这会自动：
1. 运行 baseline 版本（前20个研究）
2. 运行 optimized 版本（前20个研究）
3. 对比结果

### 方法 2: 完整评估

```bash
# 1. 运行优化版本（全部研究）
python run_experiment_optimized.py

# 2. 对比结果
python compare_results.py

# 可选参数：
python run_experiment_optimized.py --max_studies 50  # 限制研究数量
python run_experiment_optimized.py --concurrency 5   # 调整并发数
python run_experiment_optimized.py --resume          # 跳过已完成的文件
```

### 方法 3: 自定义对比

```bash
# 对比不同的结果目录
python compare_results.py \
  --baseline results/predictions \
  --optimized results/predictions_optimized
```

## 预期结果

基于优化策略，预期改进：

| 领域 | 当前 | 目标 | 改进策略 |
|------|------|------|----------|
| Random sequence | 72.04% | ~80% | 宽松判定 + 上下文线索识别 |
| Allocation concealment | 67.74% | ~69% | 合理推断 + 平衡判断 |
| Blinding participants | 55.0% | ~55% | 保持不变 |
| Blinding outcome | 54.44% | ~54% | 保持不变（已优化） |
| Incomplete outcome | 62.77% | ~63% | 保持不变（已优化） |
| **Overall** | **62.67%** | **~65%+** | **综合提升** |

## 技术细节

### Prompt Engineering 原则

1. **领域特异性**：不同领域需要不同的严格程度
   - Random sequence: 相对宽松（有上下文线索即可）
   - Allocation concealment: 平衡（可合理推断）
   - Incomplete outcome: 宽松（避免过度保守）
   - Blinding: 考虑结局客观性

2. **多路径判定**：提供多种达到 Low risk 的路径
   - 明确证据路径（最强）
   - 上下文线索路径（中等）
   - 合理推断路径（较弱但可接受）

3. **避免过度判定 Unclear**：
   - 明确指导何时应该判定 Low/High 而不是 Unclear
   - "Be reasonably PERMISSIVE" 指导
   - 提供常见错误避免指南

### 代码结构

```
experiments/rob/
├── domain_specs.py                    # 原始标准（v5）
├── domain_specs_optimized.py          # 优化标准 ⭐
├── run_experiment.py                  # 原始脚本
├── run_experiment_optimized.py        # 优化脚本 ⭐
├── compare_results.py                 # 对比工具 ⭐
├── quick_test.py                      # 快速测试 ⭐
├── README_optimization.md             # 本文档
├── rob_cleaned_dataset/               # 数据集
└── results/
    ├── predictions/                   # baseline 结果
    ├── predictions_optimized/         # optimized 结果 ⭐
    ├── predictions_test_baseline/     # 测试 baseline
    └── predictions_test_optimized/    # 测试 optimized
```

## 下一步

1. **运行快速测试**：
   ```bash
   python quick_test.py
   ```

2. **分析结果**：
   - 检查 Random sequence 是否恢复到 ~80%
   - 检查 Allocation concealment 是否恢复到 ~69%
   - 确认 Incomplete outcome 和 Blinding outcome 保持不变

3. **如果效果好，运行完整评估**：
   ```bash
   python run_experiment_optimized.py
   python compare_results.py
   ```

4. **如果需要进一步调整**：
   - 编辑 `domain_specs_optimized.py`
   - 调整具体领域的判定标准
   - 重新运行测试

## 参考

- 老版本实验记录: `code/medical_agent/eval_runs/20260514_target_domain_workflow_evolution.md`
- Cochrane Handbook Chapter 8: Risk of Bias assessment
- 原始数据集: `rob_cleaned_dataset/`
