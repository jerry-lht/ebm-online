# Batch Risk of Bias Eval Report

This report contains an audit trace: explicit extracted evidence, model-provided rationales, and label comparisons. It does not include hidden chain-of-thought.

- Studies: 2
- Domains: 10
- Accuracy: 7/10 (70.0%)
- Article-observable accuracy: 4/5 (80.0%)
- External/review-context GT domains: 0
- Unknown or non-text GT domains: 5

## Summary

| PMID | Study | Correct | Accuracy | Seconds |
|---|---|---:|---:|---:|
| 18779465 | Grant 2008 | 3/5 | 60.0% | 28.50 |
| 22454006 | Strowitzki 2012 | 4/5 | 80.0% | 29.07 |

## Error Types

- figure_table_or_supplement_needed: 1
- over-inferred_from_sparse_reporting: 1
- under-called_due_to_missing_or_underused_evidence: 1

## 18779465 - Grant 2008

- Mode: hybrid
- Review context: none (0 chars)
- Article chars: 23878
- Extraction context chars: 12002
- Total seconds: 28.5

### Methodology Extraction

- `randomization_method`: Practices were grouped in 4 mutually exclusive strata (women's health practices, low-income urban practices, large suburban practices, and smaller suburban practices), and practices within each independent stratum were randomly assigned to 1 of 2 study arms (for 16 possible randomization combinations).
- `allocation_concealment_method`: Not reported
- `blinding_participants`: Patients were unaware of their PHR assignment when consenting to enroll in the study.
- `blinding_personnel`: Not reported
- `blinding_outcome_assessors`: All primary and other clinical outcomes were collected directly from the electronic clinical data repository, and these data were obtained solely as part of usual clinical care.
- `attrition_details`: Participant flow: Figure 1 illustrates the number of primary care practices randomized and the flow of patients with DM in each study arm. Use of the parent PG secure Web portal by patients with DM ranged from 7% to 14% of each practice population. Among patients with active PG accounts, the rate of consent to enroll in the advanced patient portal clinical trial was 39% in the DM PHR intervention arm and 35% in the family history and health maintenance PHR active... (no numerical counts of...
- `study_design`: Cluster randomized trial (randomized at the practice level).
- `additional_notes`: Informed consent was obtained from eligible patients prior to notification of practice randomization status. The intervention was a system-level, practice-randomized PHR module vs an active control PHR module. Outcomes were measured from routinely collected electronic clinical data. Patients newly diagnosed during the study were not included in any analyses.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Unclear risk | Unclear risk | yes | article_absence_or_unclear |  |
| Allocation concealment | Unclear risk | Unclear risk | yes | article_absence_or_unclear |  |
| Blinding of participants and personnel: All outcomes | Low risk | Unclear risk | no | article_absence_or_unclear | over-inferred_from_sparse_reporting |
| Blinding of outcome assessment: All outcomes | Low risk | Low risk | yes | article_absence_or_unclear |  |
| Incomplete outcome data: All outcomes | Unclear risk | Low risk | no | figure_table_or_supplement_reference | figure_table_or_supplement_needed |

### Audit Details

#### Random sequence generation

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The trial reports that practices were randomized within strata but provides no information on how the random sequence was generated (random number table, computer, etc.). Under Cochrane criteria, absence of details about the random component warrants an Unclear risk judgement.
- Model support: Quote: "Practices were grouped in 4 mutually exclusive strata (women's health practices, low-income urban practices, large suburban practices, and smaller suburban practices), and practices within each independent stratum were randomly assigned to 1 of 2 study arms (for 16 possible randomization combinations)." Comment: The report states practices were "randomly assigned" within strata but gives no details of the random sequence generation method (e.g., computer generator, random number table). Probably not reported.
- Model support context: [{"source": "article", "quote": "Practices...were randomly assigned to 1 of 2 study arms (for 16 possible randomization combinations).", "relevance": "States random assignment occurred but does not describe the method used to generate the sequence."}, {"source": "methodology", "quote": "randomization_method: \"Practices were grouped...and practices within each independent stratum were randomly assigned...\" allocation_concealment_method: \"Not reported\"", "relevance": "Confirms stratified cluster randomization but absence of allocation-concealment details and no sequence generation method reported."}]
- GT support: Cluster‐randomisation, stratified block randomisation. It was not described how the random sequence was generated. “Practices were grouped in 4 mutually exclusive strata (women’s health practices, low‐income urban practices, large suburban practices, and smaller suburban practices), and practices within each independent stratum were randomly assigned to 1 of 2 study arms (for 16 possible randomisation combinations)” (p. 1778)
- Evidence row: {}
- Source context preview: ## Randomization Because this was a system-level intervention that involved patients, their physicians, and the clinical support staff at each practice, we randomized at the practice level. Practices were grouped in 4 mutually exclusive strata (women's health practices, low-income urban practices, large suburban practices, and smaller suburban practices), and practices within each independent stratum were randomly assigned to 1 of 2 study arms (for 16 possible randomization combinations). All primary and other clinical outcomes were collected directly from the electronic clinical data repository, and these data were obtained solely as part of usual clinical care. --- ## Intervention After...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: Because the report describes the randomization scheme but provides no details on central allocation, sealed envelopes with safeguards, or other methods preventing foreknowledge, there is insufficient information to judge whether investigators/enrollers could foresee assignments, so risk is unclear.
- Model support: Comment: Allocation concealment not reported. The trial describes stratified cluster randomization of practices but gives no information on how practice assignments were concealed from those enrolling sites or personnel, so it is unclear whether recruiters could foresee allocations.
- Model support context: [{"source": "article", "quote": "practices within each independent stratum were randomly assigned to 1 of 2 study arms", "relevance": "States cluster randomization occurred but gives no detail on concealment process."}, {"source": "methodology", "quote": "allocation_concealment_method: \"Not reported\"", "relevance": "Explicitly indicates no information was provided about allocation concealment."}]
- GT support: It was not reported whether allocation of treatment to clusters was concealed, but it seems that patients had been recruited before randomisation
- Evidence row: {}
- Source context preview: ## Randomization Because this was a system-level intervention that involved patients, their physicians, and the clinical support staff at each practice, we randomized at the practice level. Practices were grouped in 4 mutually exclusive strata (women's health practices, low-income urban practices, large suburban practices, and smaller suburban practices), and practices within each independent stratum were randomly assigned to 1 of 2 study arms (for 16 possible randomization combinations). All primary and other clinical outcomes were collected directly from the electronic clinical data repository, and these data were obtained solely as part of usual clinical care. --- ## Setting and...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: Participants were unaware of assignment at enrollment and both arms received active PHR modules (only content differed). Primary outcomes were routinely collected objective EMR data, so lack of overt blinding is unlikely to have materially biased study outcomes.
- Model support: Quote: "Patients were unaware of their PHR assignment when consenting to enroll in the study." Comment: Participants did not know which module they would receive at consent, and both arms received an active PHR (only content differed), so participants and staff were unlikely to know or infer allocation in a way that would materially influence routinely collected objective clinical outcomes. Probably done.
- Model support context: [{"source": "article", "quote": "Patients were unaware of their PHR assignment when consenting to enroll in the study.", "relevance": "Direct statement that participants did not know assignment at consent, reducing performance bias."}, {"source": "article", "quote": "All primary and other clinical outcomes were collected directly from the electronic clinical data repository, and these data were obtained solely as part of usual clinical care.", "relevance": "Outcomes were objective routine EMR data, unlikely to be affected by participant or personnel expectations."}]
- GT support: Objective outcomes Blinding of physicians not possible, patients were blinded, as the control group also gained access to new components of the patient portal “Patients were unaware of their PHR assignment when consenting to enrol in the study. Because both intervention and control groups used PG and received additional PHR modules, the primary distinction between the 2 study arms was the content of the modules“ (p. 1777) Unclear whether different performance influences HbA1c No further outcomes were reported
- Evidence row: {}
- Source context preview: ## Randomization Because this was a system-level intervention that involved patients, their physicians, and the clinical support staff at each practice, we randomized at the practice level. Practices were grouped in 4 mutually exclusive strata (women's health practices, low-income urban practices, large suburban practices, and smaller suburban practices), and practices within each independent stratum were randomly assigned to 1 of 2 study arms (for 16 possible randomization combinations). All primary and other clinical outcomes were collected directly from the electronic clinical data repository, and these data were obtained solely as part of usual clinical care. --- ## Intervention After...

#### Blinding of outcome assessment: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: Outcome data were objective, routinely recorded EMR and laboratory values obtained as part of usual care, which are unlikely to be influenced by knowledge of allocation; therefore detection bias is unlikely.
- Model support: Quote: "All primary and other clinical outcomes were collected directly from the electronic clinical data repository, and these data were obtained solely as part of usual clinical care." Comment: Outcome assessment was based on objective routinely collected EMR/laboratory data unlikely to be influenced by knowledge of intervention, so blinding of assessors not required. Probably done.
- Model support context: [{"source": "article", "quote": "All primary and other clinical outcomes were collected directly from the electronic clinical data repository, and these data were obtained solely as part of usual clinical care.", "relevance": "Shows outcomes were objective EMR-derived data and not subjective assessments vulnerable to assessor bias."}, {"source": "methodology", "quote": "Outcomes were measured from routinely collected electronic clinical data.", "relevance": "Supports that measurement was automated/record-based and unlikely to be changed by knowledge of allocation."}]
- GT support: Objective outcomes It was not reported whether personnel in the lab were blinded, but this routine lab test has probably a small risk for detection bias. No further outcomes were reported
- Evidence row: {}
- Source context preview: ## Randomization Because this was a system-level intervention that involved patients, their physicians, and the clinical support staff at each practice, we randomized at the practice level. Practices were grouped in 4 mutually exclusive strata (women's health practices, low-income urban practices, large suburban practices, and smaller suburban practices), and practices within each independent stratum were randomly assigned to 1 of 2 study arms (for 16 possible randomization combinations). All primary and other clinical outcomes were collected directly from the electronic clinical data repository, and these data were obtained solely as part of usual clinical care. --- ## Front To address...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: figure_table_or_supplement_reference (article observable: None)
- GT support phrase hits: 
- Model rationale: Key details on numbers missing, balance between arms, reasons for missingness, and handling/imputation are not reported in the available text. Because reporting is insufficient to determine whether missing data could introduce material bias, the appropriate judgement is Unclear risk.
- Model support: Quote: "Figure 1 illustrates the number of primary care practices randomized and the flow of patients with DM in each study arm. Use of the parent PG secure Web portal by patients with DM ranged from 7% to 14% of each practice population. Among patients with active PG accounts, the rate of consent to enroll in the advanced patient portal clinical trial was 39% in the DM PHR intervention arm and 35% in the family history and health maintenance PHR active control arm." Comment: The report describes participation rates and refers to a participant flow figure but does not provide numerical counts of losses to follow-up, exclusions after randomization, reasons for missing outcome data, or methods for handling missing data in the provided text. Therefore there is insufficient information to judge whether missing outcome data could bias results.
- Model support context: [{"source": "article", "quote": "Figure 1 illustrates the number of primary care practices randomized and the flow of patients with DM in each study arm.", "relevance": "Refers to participant flow but no detailed attrition numbers or reasons are provided in text."}, {"source": "methodology", "quote": "no numerical counts of losses to follow-up, exclusions after randomization, reasons, or methods for handling missing data reported", "relevance": "Explicitly notes missing details needed to assess attrition bias."}]
- GT support: Objective outcomes All patients were analysed, but no data show whether follow‐up was equally distributed over the different clusters (p. 1779, Table)
- Evidence row: {}
- Source context preview: ## Participant Flow Figure 1 illustrates the number of primary care practices randomized and the flow of patients with DM in each study arm. Use of the parent PG secure Web portal by patients with DM ranged from 7% to 14% of each practice population. Among patients with active PG accounts, the rate of consent to enroll in the advanced patient portal clinical trial was 39% in the DM PHR intervention arm and 35% in the family history and health maintenance PHR active control arm. Practices were enrolled beginning September 30, 2005, and follow-up ascertainment was completed when the study was formally closed March 22, 2007. --- ## Outcomes The primary outcomes for this study were changes from...


## 22454006 - Strowitzki 2012

- Mode: hybrid
- Review context: none (0 chars)
- Article chars: 24346
- Extraction context chars: 12003
- Total seconds: 29.07

### Methodology Extraction

- `randomization_method`: "Subjects were then randomised 1:1 using a computer-generated randomisation list using randomisation blocks of four. These blocks were assigned to study centres. Within each centre the allocation of a randomisation number was linked in a chronologically ascending manner to the sequence of arrival of the patients at the study centre."
- `allocation_concealment_method`: Not reported
- `blinding_participants`: "open-label" (from Study design: "This was a Phase III, multicentre, open-label, randomised, active-controlled, parallel-group study")
- `blinding_personnel`: Not reported
- `blinding_outcome_assessors`: Not reported
- `attrition_details`: "A total of 223 patients who received study medication were included in the FAS (flexibleMIB regimen, n=115; conventional regimen, n=108) and 210 patients (110 and 100, respectively) completed the study as planned (Figure 1)." No further reasons for withdrawals or handling of missing data are reported.
- `study_design`: "Phase III, multicentre, open-label, randomised, active-controlled, parallel-group study"
- `additional_notes`: "At screening, eligible subjects were sequentially assigned a unique three-digit patient identification number." Rescue medication (ibuprofen) was permitted and documented. The primary efficacy variable was based on daily self-assessed pain recorded in a daily diary.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Low risk | yes | unknown |  |
| Allocation concealment | Unclear risk | Low risk | no | unknown | under-called_due_to_missing_or_underused_evidence |
| Blinding of participants and personnel: All outcomes | High risk | High risk | yes | unknown |  |
| Blinding of outcome assessment: All outcomes | High risk | High risk | yes | unknown |  |
| Incomplete outcome data: All outcomes | Low risk | Low risk | yes | article_absence_or_unclear |  |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: The report explicitly states a computer-generated randomisation list was used (random component), which meets the Cochrane Low risk criteria for random sequence generation.
- Model support: Quote: "Subjects were then randomised 1:1 using a computer-generated randomisation list using randomisation blocks of four. These blocks were assigned to study centres. Within each centre the allocation of a randomisation number was linked in a chronologically ascending manner to the sequence of arrival of the patients at the study centre." Comment: Probably done — a computer-generated randomisation list (with block randomisation) describes a random component in sequence generation, satisfying Low risk criteria.
- Model support context: [{"source": "article", "quote": "Subjects were then randomised 1:1 using a computer-generated randomisation list using randomisation blocks of four.", "relevance": "Direct evidence that sequence generation used a computer random number method and block randomisation."}, {"source": "methodology", "quote": "Within each centre the allocation of a randomisation number was linked in a chronologically ascending manner to the sequence of arrival of the patients at the study centre.", "relevance": "Explains how generated random numbers were assigned to enrolled participants, consistent with randomized sequence use."}]
- GT support: Computer-generated
- Evidence row: {}
- Source context preview: ## Statistical analysis The study sample size was determined on the assumption that for the primary efficacy variable there would be a mean difference between the flexibleMIB and conventional groups of 5 days, with a standard deviation (SD) of 10 days. Based on a standardised effect size of 0.5, a dropout rate of 20%, α of 0.05 (two-sided) and 90% power, a sample size of 108 women per regimen was required to have 86 evaluable women per group. At screening, eligible subjects were sequentially assigned a unique three-digit patient identification number. Subjects were then randomised 1:1 using a computer-generated randomisation list using randomisation blocks of four. These blocks were...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: Although a computer-generated, blocked randomisation scheme is described, there is no information that recruiters/enrollers could not foresee allocations (no central randomisation, sealed envelope safeguards, or independent control reported). Insufficient detail means unclear risk of bias from allocation concealment.
- Model support: Quote: "Subjects were then randomised 1:1 using a computer-generated randomisation list using randomisation blocks of four. These blocks were assigned to study centres. Within each centre the allocation of a randomisation number was linked in a chronologically ascending manner to the sequence of arrival of the patients at the study centre." Comment: The report describes sequence generation and linking of randomisation numbers to arrival order, but does not state how the randomisation list/numbers were held, who controlled allocation, or whether assignments were concealed (e.g. central randomisation or opaque sealed envelopes). Therefore allocation concealment is insufficiently reported — Unclear risk.
- Model support context: [{"source": "article", "quote": "Subjects were then randomised 1:1 using a computer-generated randomisation list using randomisation blocks of four. These blocks were assigned to study centres.", "relevance": "Describes sequence generation and blocking but gives no information on concealment procedures."}, {"source": "methodology", "quote": "allocation_concealment_method: Not reported", "relevance": "Explicitly indicates that the paper did not report the method used to prevent foreknowledge of assignments."}]
- GT support: Computer-generated
- Evidence row: {}
- Source context preview: ## Statistical analysis The study sample size was determined on the assumption that for the primary efficacy variable there would be a mean difference between the flexibleMIB and conventional groups of 5 days, with a standard deviation (SD) of 10 days. Based on a standardised effect size of 0.5, a dropout rate of 20%, α of 0.05 (two-sided) and 90% power, a sample size of 108 women per regimen was required to have 86 evaluable women per group. At screening, eligible subjects were sequentially assigned a unique three-digit patient identification number. Subjects were then randomised 1:1 using a computer-generated randomisation list using randomisation blocks of four. These blocks were...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: High risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: Open-label design with a subjective, self-assessed primary outcome (daily pain diary) creates substantial risk that participant and personnel knowledge of allocation biased outcomes; therefore performance bias is likely and judged High risk.
- Model support: Quote: "This was a Phase III, multicentre, open-label, randomised, active-controlled, parallel-group study" Comment: The trial was explicitly open-label (participants and personnel were aware of assigned regimens). The primary efficacy outcome was daily self-assessed pain recorded in a daily diary (subjective and susceptible to expectation/placebo effects). Probably not done: blinding of participants/personnel was not performed, which is likely to have influenced the subjective pain outcome.
- Model support context: [{"source": "article", "quote": "This was a Phase III, multicentre, open-label, randomised, active-controlled, parallel-group study", "relevance": "Direct statement that the study was open-label, indicating no blinding of participants/personnel."}, {"source": "methodology", "quote": "The primary efficacy variable was based on daily self-assessed pain recorded in a daily diary.", "relevance": "Primary outcome was subjective self-reported pain, which is likely influenced by knowledge of treatment allocation."}]
- GT support: Not blinded
- Evidence row: {}
- Source context preview: ## Study design The study (ClinicalTrials.gov identifier, NCT00569244) was conducted in accordance with the International Conference on Harmonisation–Good Clinical Practice guidelines and Declaration of Helsinki. All participants had to have voluntarily signed an informed consent form before entering the study. --- ## Study design This was a Phase III, multicentre, open-label, randomised, active-controlled, parallel-group study conducted in 26 centres in Germany and three centres in the UK between December 2007 and December 2009. --- ## Statistical analysis The study sample size was determined on the assumption that for the primary efficacy variable there would be a mean difference between...

#### Blinding of outcome assessment: All outcomes

- Prediction: High risk
- Ground truth: High risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: Because the study was open-label, outcome assessors were not reported as blinded, and the primary outcome was subjective self-reported pain, lack of blinding is likely to have influenced outcome assessment, constituting a high risk of detection bias.
- Model support: Quote: "This was a Phase III, multicentre, open-label, randomised, active-controlled, parallel-group study" Comment: The trial was explicitly open-label and there is no reporting that outcome assessors were blinded. The primary efficacy variable was daily self-assessed pain (diary), which is subjective and highly susceptible to bias if participants and/or assessors are unblinded. Probably not done.
- Model support context: [{"source": "article", "quote": "This was a Phase III, multicentre, open-label, randomised, active-controlled, parallel-group study", "relevance": "States the trial was open‑label, indicating participants and personnel were aware of allocations."}, {"source": "methodology", "quote": "The primary efficacy variable was based on daily self-assessed pain recorded in a daily diary.", "relevance": "Outcome is subjective self-reported pain and thus likely biased if participants/assessors not blinded."}]
- GT support: Not blinded
- Evidence row: {}
- Source context preview: ## Study design This was a Phase III, multicentre, open-label, randomised, active-controlled, parallel-group study conducted in 26 centres in Germany and three centres in the UK between December 2007 and December 2009. --- ## Study design The study (ClinicalTrials.gov identifier, NCT00569244) was conducted in accordance with the International Conference on Harmonisation–Good Clinical Practice guidelines and Declaration of Helsinki. All participants had to have voluntarily signed an informed consent form before entering the study. --- ## Statistical analysis The study sample size was determined on the assumption that for the primary efficacy variable there would be a mean difference between...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: Attrition was low (~5.8%) and similar across groups (110/115 vs 100/108 completed); missing data proportion is small relative to study size and planned effect, and therefore unlikely to introduce meaningful bias in the continuous, self-recorded primary outcome.
- Model support: Quote: "A total of 223 patients who received study medication were included in the FAS (flexibleMIB regimen, n=115; conventional regimen, n=108) and 210 patients (110 and 100, respectively) completed the study as planned (Figure 1)." Comment: Missing outcome data were small and balanced between groups (5/115 vs 8/108 did not complete). Reasons for withdrawal are not detailed but overall attrition (~5.8%) is well below planned 20% and unlikely to bias the continuous, diary-based primary outcome. Probably not materially related to outcome.
- Model support context: [{"source": "article", "quote": "A total of 223 patients who received study medication were included in the FAS ... and 210 patients (110 and 100, respectively) completed the study as planned (Figure 1).", "relevance": "Shows number randomized/treated and completed by group, demonstrating low and balanced attrition."}, {"source": "methodology", "quote": "The primary efficacy variable was the number of days with dysmenorrhoeic pain over 140 days ... recorded in a daily diary.", "relevance": "Primary outcome is continuous and diary-based; small, balanced missingness unlikely to materially bias effect estimate."}]
- GT support: Number of withdrawals not reported
- Evidence row: {}
- Source context preview: ## Results A total of 223 patients who received study medication were included in the FAS (flexibleMIB regimen, n=115; conventional regimen, n=108) and 210 patients (110 and 100, respectively) completed the study as planned (Figure 1). Baseline characteristics were similar for the two regimens and are outlined in Table 1. --- ## Statistical analysis The study sample size was determined on the assumption that for the primary efficacy variable there would be a mean difference between the flexibleMIB and conventional groups of 5 days, with a standard deviation (SD) of 10 days. Based on a standardised effect size of 0.5, a dropout rate of 20%, α of 0.05 (two-sided) and 90% power, a sample size...

## Workflow Evolution Notes

- Inspect mismatches where prediction is `Unclear risk` but GT is `Low risk`: these usually mean retrieval or Stage 1 extraction missed a concrete methodological phrase.
- Inspect mismatches where prediction is `Low risk` or `High risk` but GT is `Unclear risk`: these usually mean the prompt is allowing too much inference from generic trial language.
- For blinding mismatches, add outcome-type cues to the prompt: self-report outcomes, objective outcomes, assessor-administered outcomes, and whether lack of blinding can materially affect the outcome.
- For allocation concealment mismatches, require the model to distinguish sequence generation from concealment before assignment.