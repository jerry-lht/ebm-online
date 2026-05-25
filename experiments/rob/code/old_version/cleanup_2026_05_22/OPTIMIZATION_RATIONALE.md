# Domain Criteria Optimization: Theoretical Rationale

## 核心洞察

从实验数据中发现的关键模式：

### 成功案例分析

**Incomplete Outcome Data: 40% → 62.77% (+22.77%)**

成功的关键因素：
1. **"Be reasonably PERMISSIVE"** 指导语（第156行）
2. **多路径判定**：提供5种不同的 Low risk 路径（第161-169行）
3. **明确的 Unclear 边界**：只在"genuinely cannot tell"时使用（第181-191行）

**理论依据**：
- RCT 论文通常会报告 attrition 信息，但格式多样
- 过于严格的标准会导致过度判定 Unclear（老版本的问题）
- 宽松但有原则的判定更符合 Cochrane 实践

**Blinding of Outcome Assessment: 48% → 54.44% (+6.44%)**

成功的关键因素：
1. **客观性考量**：明确区分客观/主观结局（第116-120行）
2. **合理的 Low risk 路径**：客观结局即使未盲也可判 Low（第125-128行）
3. **常见错误指南**：避免误判（第144-149行）

**理论依据**：
- 结局的客观性决定了盲法的重要性
- 实验室检测、死亡率等客观结局即使评估者未盲也难以产生偏倚
- 这符合 Cochrane Handbook 的风险导向原则

### 失败案例分析

**Random Sequence Generation: 80% → 72.04% (-7.96%)**

问题诊断：
1. **过于严格的标准**：第43行 "the word 'randomized' alone is NOT enough"
2. **缺少宽松指导**：没有类似 Incomplete outcome 的 "Be reasonably PERMISSIVE"
3. **忽视上下文线索**：很多论文说 "randomized" + "computer-generated" 或 "block randomization"，这应该足够

**理论依据**：
- 大多数发表的 RCT 确实使用了正确的随机化方法
- "Block randomization" 或 "stratified randomization" 本身就隐含了正确的随机序列生成
- 过于严格会导致大量 False Unclear（实际是 Low risk 但被判为 Unclear）

**Allocation Concealment: 69% → 67.74% (-1.26%)**

问题诊断：
1. **"Default is Unclear"**（第55行）：设置了过于保守的默认值
2. **"Only upgrade to Low if EXPLICIT"**（第56行）：要求过高
3. **忽视合理推断**：某些情况下可以从其他信息推断 concealment

**理论依据**：
- Allocation concealment 确实是很多论文不报告的领域
- 但某些设计（如 central randomization, pharmacy randomization）本身就隐含了 concealment
- 双盲试验中，如果使用相同外观的药物，recruiter 通常无法预见分配

## 优化策略的理论基础

### 1. 领域特异性原则

不同的 RoB 领域需要不同的判定严格程度：

| 领域 | 报告质量 | 判定策略 | 理由 |
|------|----------|----------|------|
| Random sequence | 中等 | **宽松** | 大多数 RCT 使用正确方法，上下文线索可靠 |
| Allocation concealment | 差 | **平衡** | 报告不足，但某些设计隐含 concealment |
| Blinding participants | 好 | 中等 | 通常明确报告 |
| Blinding outcome | 中等 | **客观性导向** | 结局类型比盲法状态更重要 |
| Incomplete outcome | 好 | **宽松** | 通常报告，但格式多样 |

### 2. 多路径判定原则

为每个领域提供多种达到 Low risk 的路径：

**强证据路径**（最可靠）：
- 明确的方法描述
- 例如："sequentially numbered, opaque, sealed envelopes"

**中等证据路径**（可靠）：
- 上下文线索
- 例如："computer-generated randomization" → 暗示正确的随机方法

**弱证据路径**（可接受）：
- 合理推断
- 例如："central randomization" → 隐含 allocation concealment

### 3. 避免过度保守原则

**问题**：过度判定 Unclear 会导致：
- 低估研究质量
- 失去区分度（所有研究都是 Unclear）
- 不符合 Cochrane 实践

**解决方案**：
- 明确 "Be reasonably PERMISSIVE" 指导
- 提供清晰的 Unclear 边界定义
- 只在 "genuinely cannot tell" 时使用 Unclear

### 4. 上下文线索识别原则

很多论文不会详细描述方法，但会提供线索：

**Random Sequence Generation 的线索**：
- "computer-generated" → 正确的随机方法
- "block randomization" → 隐含随机序列
- "stratified randomization" → 隐含随机序列
- "by statistician" → 暗示正确方法

**Allocation Concealment 的线索**：
- "central randomization" → 隐含 concealment
- "pharmacy randomization" → 隐含 concealment
- "double-blind" + "identical appearance" → 隐含 concealment
- "after enrollment" → 时序暗示 concealment

## 优化后的判定流程

### Random Sequence Generation

```
论文描述 → 判定流程
├─ 明确随机方法（RNG, coin toss, etc.） → Low risk
├─ "randomized" + 上下文线索
│  ├─ "computer-generated" → Low risk ✅
│  ├─ "block/stratified randomization" → Low risk ✅
│  ├─ "central/pharmacy randomization" → Low risk ✅
│  └─ "by statistician" → Low risk ✅
├─ 仅 "randomized"，无其他信息 → Unclear risk
└─ 明确非随机方法 → High risk
```

### Allocation Concealment

```
论文描述 → 判定流程
├─ 明确 concealment 机制
│  ├─ Central allocation → Low risk
│  ├─ SNOSE (all 3 features) → Low risk
│  └─ Numbered drug containers → Low risk
├─ 合理推断路径
│  ├─ "central/pharmacy randomization" → Low risk ✅
│  ├─ "by independent person after enrollment" → Low risk ✅
│  └─ "double-blind" + "identical appearance" → Low risk ✅
├─ 无 concealment 信息，无法推断 → Unclear risk
└─ 明确不充分的 concealment → High risk
```

### Incomplete Outcome Data（保持不变）

```
论文描述 → 判定流程
├─ 任一 Low risk 路径
│  ├─ 完整随访 → Low risk
│  ├─ 合理且平衡的 attrition (≤20%) → Low risk ✅
│  ├─ "most completed" + 无失衡信号 → Low risk ✅
│  ├─ 适当的缺失数据方法 → Low risk
│  └─ ITT + 低/平衡 attrition → Low risk
├─ 偏倚证据
│  ├─ 失衡的 attrition + 结局相关 → High risk
│  ├─ 大量 attrition (>20%) + 处理不当 → High risk
│  └─ 不当的简单插补 → High risk
└─ genuinely cannot tell → Unclear risk
```

### Blinding of Outcome Assessment（保持不变）

```
论文描述 → 判定流程
├─ 评估者明确盲法 → Low risk
├─ 评估者未盲 BUT 客观结局
│  ├─ 死亡率（记录） → Low risk ✅
│  ├─ 实验室检测（自动分析） → Low risk ✅
│  └─ 影像学（标准化标准） → Low risk ✅
├─ 评估者未盲 AND 主观结局
│  ├─ 临床评分量表 → High risk
│  ├─ 患者自报（患者未盲） → High risk
│  └─ 需要临床判断的诊断 → High risk
└─ 未报告评估者盲法 → Unclear risk (default)
```

## 预期改进的理论支持

### Random Sequence: 72% → 80% (+8%)

**改进来源**：
- 识别上下文线索（"computer-generated", "block randomization"）
- 减少 False Unclear（实际 Low risk 但被判为 Unclear）

**估算**：
- 假设 72% 中有 ~10% 是 False Unclear
- 通过上下文线索识别，可恢复这 10%
- 预期达到 80%

### Allocation Concealment: 67.74% → 69% (+1.26%)

**改进来源**：
- 合理推断路径（"central randomization" → Low risk）
- 减少过度保守判定

**估算**：
- 这个领域确实很多论文不报告
- 改进空间有限，但可通过合理推断恢复 1-2%
- 预期达到 69%

### 总体: 62.67% → 65%+ (+2.33%+)

**改进来源**：
- Random sequence: +8% × 20% (权重) = +1.6%
- Allocation concealment: +1.26% × 20% = +0.25%
- 其他领域保持不变
- **总计**: +1.85% → 预期 64.52%

**保守估计**: 64.5%
**乐观估计**: 65.5%（如果上下文线索识别效果更好）

## 风险与权衡

### 潜在风险

1. **过度宽松**：可能导致 False Low risk
   - **缓解措施**：保持明确的判定标准，只在有合理依据时判 Low

2. **上下文线索误判**：某些线索可能不可靠
   - **缓解措施**：只使用高可信度的线索（如 "computer-generated", "central randomization"）

3. **领域间不一致**：不同领域使用不同严格程度
   - **缓解措施**：这是有意的设计，符合 Cochrane 的领域特异性原则

### 权衡考虑

| 方面 | 严格标准 | 宽松标准 | 优化方案 |
|------|----------|----------|----------|
| False Unclear | 高 | 低 | **低**（通过上下文线索） |
| False Low risk | 低 | 高 | **中**（保持判定标准） |
| 区分度 | 低 | 高 | **高**（平衡判定） |
| 符合实践 | 中 | 高 | **高**（领域特异性） |

## 验证策略

### 1. 快速验证（20个研究）

目标：快速检查优化方向是否正确

```bash
python quick_test.py
```

预期结果：
- Random sequence 应该提升
- Allocation concealment 应该提升或持平
- Incomplete outcome 和 Blinding outcome 应该保持

### 2. 完整验证（全部研究）

目标：确认优化效果在大数据集上的稳定性

```bash
python run_experiment_optimized.py
python compare_results.py
```

预期结果：
- 总体准确率 ≥ 64.5%
- Random sequence ≥ 78%
- Allocation concealment ≥ 68%

### 3. 错误分析

如果结果不如预期，分析：
- 哪些研究从 Unclear 改为 Low risk？（检查是否合理）
- 哪些研究从 Low risk 改为 Unclear？（检查是否过度宽松）
- 上下文线索的准确率如何？

## 总结

优化的核心原则：

1. **领域特异性**：不同领域需要不同的判定策略
2. **多路径判定**：提供多种达到 Low risk 的合理路径
3. **上下文线索**：识别和利用论文中的隐含信息
4. **避免过度保守**：只在真正无法判断时使用 Unclear
5. **保持成功**：不改动已经优化好的领域

预期效果：
- ✅ 保持 Incomplete outcome 的突破性提升 (62.77%)
- ✅ 保持 Blinding outcome 的改进 (54.44%)
- 🎯 恢复 Random sequence 到 ~80%
- 🎯 恢复 Allocation concealment 到 ~69%
- 🎯 总体提升到 64.5%-65.5%
