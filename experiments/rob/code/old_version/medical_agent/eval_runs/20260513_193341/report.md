# Batch Risk of Bias Eval Report

This report contains an audit trace: explicit extracted evidence, model-provided rationales, and label comparisons. It does not include hidden chain-of-thought.

- Studies: 6
- Domains: 30
- Accuracy: 22/30 (73.3%)
- Article-observable accuracy: 11/14 (78.6%)
- External/review-context GT domains: 0
- Unknown or non-text GT domains: 7

## Summary

| PMID | Study | Correct | Accuracy | Seconds |
|---|---|---:|---:|---:|
| 23886027 | Ghanizadeh 2013 | 4/5 | 80.0% | 72.54 |
| 23915113 | Gobbi 2013 | 3/5 | 60.0% | 60.97 |
| 26251065 | Reme 2015 | 4/5 | 80.0% | 52.45 |
| 27007650 | Moosanejad 2016 | 3/5 | 60.0% | 54.17 |
| 27022338 | Amirkhanlou 2016 | 4/5 | 80.0% | 50.90 |
| 27463536 | Gordon 2017 | 4/5 | 80.0% | 60.57 |

## Error Types

- gt_support_not_found_in_article_text: 4
- over-inferred_from_sparse_reporting: 2
- under-called_due_to_missing_or_underused_evidence: 2

## 23886027 - Ghanizadeh 2013

- Mode: hybrid
- Review context: none (0 chars)
- Article chars: 14273
- Extraction context chars: 12003
- Total seconds: 72.54

### Methodology Extraction

- `randomization_method`: "The patients were randomly allocated into one of the two groups using a random number generator."
- `allocation_concealment_method`: Not reported
- `blinding_participants`: "The patients, parents, and independent assessor were blind to the allocation of patients."
- `blinding_personnel`: Not reported
- `blinding_outcome_assessors`: "The patients, parents, and independent assessor were blind to the allocation of patients."
- `attrition_details`: "Out of 47 children who were screened, 40 patients were randomized into one of two groups. The reasons for the drop of patients in the two groups are displayed in Figure 1." Additionally: "Only one patient withdrew due to adverse effect in the NAC group." Missing data handling: "Intent-to-Treat (ITT) using Last Observed Carried Forward (LOCF) with at least one post-treatment evaluation was used to handle missing data [45]."
- `study_design`: "an eight week randomized double-blind placebo-controlled clinical trial with two parallel groups."
- `additional_notes`: Both NAC and placebo tablets were administered in the form of effervescent. "The shape, size, taste, and color of NAC and placebo were identical." All patients in both groups received risperidone; risperidone dose was titrated and not fixed. Assessments were performed by a resident of psychiatry trained to use the questionnaire and checklist. Trial registration: IRCT201106103930N6. Ethics approval and parental written informed consent obtained.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Low risk | yes | article_text_match |  |
| Allocation concealment | Unclear risk | Unclear risk | yes | article_absence_or_unclear |  |
| Blinding of participants and personnel: All outcomes | Low risk | Low risk | yes | article_text_match |  |
| Blinding of outcome assessment: All outcomes | Low risk | Low risk | yes | no_support_phrase_match |  |
| Incomplete outcome data: All outcomes | Low risk | Unclear risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: patients were randomly allocated into one of the two groups using a random number generator | were randomly allocated into
- Model rationale: The report explicitly states allocation used a random number generator, which is an acceptable random method per Cochrane criteria, so risk of bias from sequence generation is low.
- Model support: Quote: "The patients were randomly allocated into one of the two groups using a random number generator." Comment: Probably done — a random component (computer/number generator) is explicitly reported, which meets the RoB criterion for low risk of bias in sequence generation.
- Model support context: [{"source": "article", "quote": "The patients were randomly allocated into one of the two groups using a random number generator.", "relevance": "Explicit statement of a random component in sequence generation supports low risk."}, {"source": "methodology", "quote": "\"The patients were randomly allocated into one of the two groups using a random number generator.\"", "relevance": "Matches extracted methods indicating use of a random number generator for allocation."}]
- GT support: Quote: "patients were randomly allocated into one of the two groups using a random number generator"
- Evidence row: {}
- Source context preview: ## Methods This study was an eight week randomized double-blind placebo-controlled clinical trial with two parallel groups. The patients, parents, and independent assessor were blind to the allocation of patients. The patients were randomly allocated into one of the two groups using a random number generator. --- ## Methods The patients were free from any concomitant medication. Otherwise, the dose of medication should not be markedly changed during two weeks prior entering into this study. The dose of concomitant medication was not markedly changed during this trial. --- ## Methods The changes of Irritability subscale score was considered as the main outcome of the current trial. --- ##...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The report states a random number generator was used but provides no details on central allocation, sealed envelopes, or other concealment procedures. Without information that assignments could not be foreseen, risk of selection bias remains unclear.
- Model support: Quote: "The patients were randomly allocated into one of the two groups using a random number generator." Comment: Allocation concealment method not reported. Random sequence was generated but there is no information that recruiters/enrollers could not foresee assignments, so concealment is unclear.
- Model support context: [{"source": "article", "quote": "The patients were randomly allocated into one of the two groups using a random number generator.", "relevance": "Shows random sequence generation but gives no information on how allocation was concealed from recruiters/enrollers."}, {"source": "methodology", "quote": "allocation_concealment_method: Not reported", "relevance": "Explicitly states that the report does not describe the method used to conceal allocations prior to assignment."}]
- GT support: Not described
- Evidence row: {}
- Source context preview: ## Methods This study was an eight week randomized double-blind placebo-controlled clinical trial with two parallel groups. The patients, parents, and independent assessor were blind to the allocation of patients. The patients were randomly allocated into one of the two groups using a random number generator. --- ## Methods The participants were a convenient sample of outpatients children aged between 3.5 to 16 years old from both genders. The sample was recruited from the Child and Adolescent Psychiatriy Clinics affiliated with Shiraz University of Medical Sciences, Iran. --- ## Methods The patients were free from any concomitant medication. Otherwise, the dose of medication should not be...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: the patients, parents, and independent assessor were blind to the allocation of patients | independent assessor were blind
- Model rationale: The report explicitly states double-blinding of patients, parents and an independent assessor, and placebo tablets were matched to active drug, making it unlikely that knowledge of allocation biased performance; thus risk of performance bias is low.
- Model support: Quote: "This study was an eight week randomized double-blind placebo-controlled clinical trial with two parallel groups. The patients, parents, and independent assessor were blind to the allocation of patients." Comment: Blinding of participants, parents (caregivers) and the independent assessor was performed; placebo matched NAC for shape, size, taste and color. Probably done — blinding appears adequate and outcomes (ABC irritability) could be influenced by expectancy, but blinding of patients/parents and assessor reduces performance bias.
- Model support context: [{"source": "article", "quote": "The patients, parents, and independent assessor were blind to the allocation of patients.", "relevance": "Direct statement that participants, caregivers and assessor were blinded, which addresses performance bias."}, {"source": "article", "quote": "Both NAC and placebo tablets... The shape, size, taste, and color of NAC and placebo were identical.", "relevance": "Matching of placebo supports credibility of blinding for participants and personnel administering medication."}]
- GT support: Quote: "The patients, parents, and independent assessor were blind to the allocation of patients"
- Evidence row: {}
- Source context preview: ## Methods This study was an eight week randomized double-blind placebo-controlled clinical trial with two parallel groups. The patients, parents, and independent assessor were blind to the allocation of patients. The patients were randomly allocated into one of the two groups using a random number generator. --- ## Methods The participants were a convenient sample of outpatients children aged between 3.5 to 16 years old from both genders. The sample was recruited from the Child and Adolescent Psychiatriy Clinics affiliated with Shiraz University of Medical Sciences, Iran. --- ## Methods The patients were free from any concomitant medication. Otherwise, the dose of medication should not be...

#### Blinding of outcome assessment: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states that an independent assessor, patients, and parents were blind to allocation. Given blinding of the outcome assessor and that outcomes were assessed by blinded parties, detection bias is unlikely.
- Model support: Quote: "The patients, parents, and independent assessor were blind to the allocation of patients." Comment: Blinding of outcome assessment was explicitly reported (independent assessor blind). Outcome measures (ABC caregiver-rated and assessor-administered checklists) were therefore unlikely to be influenced by assessor knowledge. Probably done.
- Model support context: [{"source": "article", "quote": "The patients, parents, and independent assessor were blind to the allocation of patients.", "relevance": "Direct statement that outcome assessor and participants were blinded, reducing detection bias."}, {"source": "article", "quote": "The primary outcome measure was Aberrant Behavior Checklist", "relevance": "Primary outcome is a standard checklist assessed with blinded assessor/parents, so blinding is relevant to outcome measurement."}]
- GT support: Quote: "the independant assessor was blind to the allocation of patients"
- Evidence row: {}
- Source context preview: ## Methods This study was an eight week randomized double-blind placebo-controlled clinical trial with two parallel groups. The patients, parents, and independent assessor were blind to the allocation of patients. The patients were randomly allocated into one of the two groups using a random number generator. --- ## Methods The diagnosis of autism was made using DSM-IV-TR criteria. The diagnosis was in accordance with Autism Diagnostic Interview-Revised (ADI-R) [41]. All the interviews were conducted by an expert child and adolescent psychiatrist (A.G.). Assessments were performed by a resident of psychiatry trained to use the questionnaire and checklist. The level of intelligence was not...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Attrition was minimal (one withdrawal) with a reported reason unlikely to materially bias results, missing data were handled with ITT/LOCF, and no imbalance in missingness across groups was identified, meeting criteria for low risk.
- Model support: Quote: "Out of 47 children who were screened, 40 patients were randomized into one of two groups. The reasons for the drop of patients in the two groups are displayed in Figure 1." Additionally: "Only one patient withdrew due to adverse effect in the NAC group." Comment: Attrition was small and balanced (only one withdrawal reported for adverse effect); ITT with LOCF was used. Given low and similar missingness and reported reasons, risk of bias from incomplete data is likely low.
- Model support context: [{"source": "article", "quote": "Only one patient withdrew due to adverse effect in the NAC group.", "relevance": "Specifies the small amount and reason for missing outcome data."}, {"source": "methodology", "quote": "Intent-to-Treat (ITT) using Last Observed Carried Forward (LOCF) with at least one post-treatment evaluation was used to handle missing data.", "relevance": "Describes how missing data were handled, supporting robustness of analysis."}]
- GT support: Data analysed for 17/20 in NAC group and 14/20 in placebo group
- Evidence row: {}
- Source context preview: ## Results Out of 47 children who were screened, 40 patients were randomized into one of two groups. The reasons for the drop of patients in the two groups are displayed in Figure 1. The number of boys in the NAC and placebo groups was 13 and 12, respectively. There was no statistically significant difference between the two groups regarding gender ratio (X2=.4, df=1, P=0.5). In addition, the mean of age was not different between the two groups (t=0.4, df=29, P=0.4). The mean age of children in the NAC and placebo group was 8.8(3.1) and 7.9(2.4) years, respectively. The list of concomitant medications is presented in Table 1. The mean (SD) dose of risperidone in the NAC+risperidone and...


## 23915113 - Gobbi 2013

- Mode: hybrid
- Review context: none (0 chars)
- Article chars: 16482
- Extraction context chars: 12005
- Total seconds: 60.97

### Methodology Extraction

- `randomization_method`: A monitoring agency prepared the randomization list and provided sealed envelopes for treatment allocation.
- `allocation_concealment_method`: A monitoring agency prepared the randomization list and provided sealed envelopes for treatment allocation.
- `blinding_participants`: Not reported
- `blinding_personnel`: Not reported
- `blinding_outcome_assessors`: EDSS and relapses assessment was performed by an examining neurologist blinded to treatment. MRI disease activity was assessed via subtraction MRI (sMRI) and via count of Gd+L by an expert who was blinded to clinical data.
- `attrition_details`: A total of 39 patients were screened, 25 fulfilled the inclusion and exclusion criteria and were offered to participate. Six patients refused their consent, 19 patients were included (NTZ n=10; IFNB n=9). 17/19 patients completed the study: one IFNB-patient withdrew consent (day 34) because she could not comply with study procedures; one NTZ-patient opted for an oral treatment (day 139). One IFNB-patient (#9) switched to rescue treatment at day 69 due to systemic side effects. Analysis was...
- `study_design`: 1-year, prospective, controlled, randomized, rater blinded, parallel-group, monocentric pilot study
- `additional_notes`: INFB was started within 30 days after the last NTZ infusion. Patients intolerant to INFB were allowed to switch to daily s.c. glatiramer acetate (GA) 20 mg (rescue therapy). The sample size was set to 20 patients, i.e. 10 patients per group and was based on clinical and practical considerations. Statistical analyses... Analysis was based on intention to treat.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Unclear risk | no | unknown | over-inferred_from_sparse_reporting |
| Allocation concealment | Unclear risk | Unclear risk | yes | unknown |  |
| Blinding of participants and personnel: All outcomes | Unclear risk | High risk | no | article_text_match | under-called_due_to_missing_or_underused_evidence |
| Blinding of outcome assessment: All outcomes | Low risk | Low risk | yes | article_text_match |  |
| Incomplete outcome data: All outcomes | Low risk | Low risk | yes | unknown |  |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: The report explicitly states an independent monitoring agency prepared the randomization list, which implies use of a proper random process (random component) for sequence generation. This satisfies the Cochrane criterion for low risk for random sequence generation.
- Model support: Quote: "A monitoring agency prepared the randomization list and provided sealed envelopes for treatment allocation." Comment: Probably done — a monitoring agency generated the randomization list (random component implied) and provided allocation envelopes, indicating a randomized sequence generation by an independent body.
- Model support context: [{"source": "article", "quote": "A monitoring agency prepared the randomization list and provided sealed envelopes for treatment allocation.", "relevance": "Describes independent preparation of the randomization list, indicating a random sequence generation process."}, {"source": "methodology", "quote": "Included patients were randomly assigned in a 1:1 ratio to continue monthly intravenous NTZ 300 mg or to de-escalate to every other day s.c. INFB 250 ug.", "relevance": "States random assignment in a 1:1 ratio, supporting that a randomized sequence was used."}]
- GT support: No information provided
- Evidence row: {}
- Source context preview: ## Methods Patients were consecutively recruited at the Neurocenter of Southern Switzerland, from 2010 to 2011. A monitoring agency prepared the randomization list and provided sealed envelopes for treatment allocation. --- ## Methods This is a 1-year, prospective, controlled, randomized, rater blinded, parallel-group, monocentric pilot study (ClinicalTrial.gov ID: NCT01144052). Included patients were females or males with RR-MS according to 2005 McDonald’s criteria, aged between 18 and 60 years, who were on NTZ and feared or were at significant risk for PML. Risk for PML was defined significant in case of NTZ treatment duration equal to or greater than 12 months. Patients had to be free of...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: Although an external monitoring agency generated the list and sealed envelopes were used, the report lacks details that confirm envelopes were opaque, sequentially numbered, tamper-proof, or independently controlled; per Cochrane criteria this incomplete information yields Unclear risk.
- Model support: Quote: "A monitoring agency prepared the randomization list and provided sealed envelopes for treatment allocation." Comment: Sealed envelopes were used and an external agency prepared the list, which suggests concealment; however the report does not state whether envelopes were opaque, sequentially numbered, sealed in a way preventing tampering, or under independent control, so concealment cannot be confirmed. Probably done, but insufficient detail.
- Model support context: [{"source": "article", "quote": "A monitoring agency prepared the randomization list and provided sealed envelopes for treatment allocation.", "relevance": "Describes who prepared list and that sealed envelopes were used, relevant to allocation concealment but missing key safeguards."}, {"source": "methodology", "quote": "A monitoring agency prepared the randomization list and provided sealed envelopes for treatment allocation.", "relevance": "Reiterates same detail from methods; lack of description about envelope safeguards leaves uncertainty."}]
- GT support: No information provided
- Evidence row: {}
- Source context preview: ## Methods Patients were consecutively recruited at the Neurocenter of Southern Switzerland, from 2010 to 2011. A monitoring agency prepared the randomization list and provided sealed envelopes for treatment allocation. --- ## Methods This is a 1-year, prospective, controlled, randomized, rater blinded, parallel-group, monocentric pilot study (ClinicalTrial.gov ID: NCT01144052). Included patients were females or males with RR-MS according to 2005 McDonald’s criteria, aged between 18 and 60 years, who were on NTZ and feared or were at significant risk for PML. Risk for PML was defined significant in case of NTZ treatment duration equal to or greater than 12 months. Patients had to be free of...

#### Blinding of participants and personnel: All outcomes

- Prediction: Unclear risk
- Ground truth: High risk
- Match: False
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: prospective, controlled, randomized, rater blinded, parallel-group, monocentric pilot study
- Model rationale: There is explicit reporting that outcome assessors (neurologist and MRI reader) were blinded, but no information on whether participants or treating personnel were blinded. Primary outcome (relapse) involves patient-reported symptoms and clinician confirmation, so lack of reported participant/personnel blinding could materially bias results; insufficient information prevents clear Low or High risk judgement.
- Model support: Quote: "rater blinded"; "EDSS and relapses assessment was performed by an examining neurologist blinded to treatment. ... MRI disease activity was assessed ... by an expert who was blinded to clinical data." Comment: Participants and treating personnel blinding is not reported. Key outcome assessors were blinded (probably done), but because participants and staff may have known allocation and primary outcomes include relapses (partly patient/clinician-reported) it is unclear whether lack of participant/personnel blinding could have influenced outcomes.
- Model support context: [{"source": "article", "quote": "This is a 1-year, prospective, controlled, randomized, rater blinded, parallel-group, monocentric pilot study.", "relevance": "States that raters were blinded but does not state participant or personnel blinding."}, {"source": "article", "quote": "EDSS and relapses assessment was performed by an examining neurologist blinded to treatment.", "relevance": "Shows outcome assessment was blinded, but says nothing about participant or treating staff blinding."}]
- GT support: Quote: "prospective, controlled, randomized, rater blinded, parallel-group, monocentric pilot study"
- Evidence row: {}
- Source context preview: ## Methods This is a 1-year, prospective, controlled, randomized, rater blinded, parallel-group, monocentric pilot study (ClinicalTrial.gov ID: NCT01144052). Included patients were females or males with RR-MS according to 2005 McDonald’s criteria, aged between 18 and 60 years, who were on NTZ and feared or were at significant risk for PML. Risk for PML was defined significant in case of NTZ treatment duration equal to or greater than 12 months. Patients had to be free of disease activity while on NTZ (free from relapses and disability progression for at least 6 months and no gadolinium enhancing lesions [Gd+L] on baseline [BL] MRI). Main exclusion criteria were pregnancy and breastfeeding;...

#### Blinding of outcome assessment: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: prospective, controlled, randomized, rater blinded, parallel-group, monocentric pilot study
- Model rationale: The report explicitly states that the examiner assessing EDSS and relapses was blinded and MRI reads were done by an expert blinded to clinical data; therefore outcome assessment was blinded and unlikely to be influenced by knowledge of allocation, supporting Low risk.
- Model support: Quote: "EDSS and relapses assessment was performed by an examining neurologist blinded to treatment. ... MRI disease activity was assessed via subtraction MRI (sMRI) and via count of Gd+L by an expert who was blinded to clinical data." Comment: Blinded outcome assessment was performed for the key clinical (EDSS, relapses) and MRI outcomes, so detection bias is unlikely. Probably done.
- Model support context: [{"source": "article", "quote": "EDSS and relapses assessment was performed by an examining neurologist blinded to treatment.", "relevance": "Shows clinical outcomes were assessed by a rater blinded to allocation, reducing detection bias."}, {"source": "article", "quote": "MRI disease activity ... by an expert who was blinded to clinical data.", "relevance": "Indicates MRI outcomes were read by a blinded expert, minimizing measurement bias for objective imaging outcomes."}]
- GT support: Quote: "prospective, controlled, randomized, rater blinded, parallel-group, monocentric pilot study"
- Evidence row: {}
- Source context preview: ## Methods This is a 1-year, prospective, controlled, randomized, rater blinded, parallel-group, monocentric pilot study (ClinicalTrial.gov ID: NCT01144052). Included patients were females or males with RR-MS according to 2005 McDonald’s criteria, aged between 18 and 60 years, who were on NTZ and feared or were at significant risk for PML. Risk for PML was defined significant in case of NTZ treatment duration equal to or greater than 12 months. Patients had to be free of disease activity while on NTZ (free from relapses and disability progression for at least 6 months and no gadolinium enhancing lesions [Gd+L] on baseline [BL] MRI). Main exclusion criteria were pregnancy and breastfeeding;...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: Attrition was low (2/19 completed not in assigned treatment and one switched to rescue) and reasons were unrelated to outcome measurement; losses were small and reasonably balanced and ITT analysis was used, so risk of bias from incomplete outcome data is low.
- Model support: Quote: "17/19 patients completed the study: one IFNB-patient withdrew consent (day 34) because she could not comply with study procedures; one NTZ-patient opted for an oral treatment (day 139). One IFNB-patient (#9) switched to rescue treatment at day 69 due to systemic side effects." Comment: Missing outcome data were small (2 withdrawals, 1 switching to rescue therapy) balanced across groups, reasons appear unrelated to outcome measurement for primary endpoints and analysis was by intention-to-treat. Probably done: appropriate handling of incomplete data (ITT) with low and non-differential attrition.
- Model support context: [{"source": "article", "quote": "17/19 patients completed the study: one IFNB-patient withdrew consent (day 34)... one NTZ-patient opted for an oral treatment (day 139). One IFNB-patient (#9) switched to rescue treatment at day 69", "relevance": "Gives numbers, reasons, and timing of missing data across arms."}, {"source": "methodology", "quote": "Analysis was based on intention to treat.", "relevance": "Indicates that all randomized participants were included in the primary analysis mitigating attrition bias."}]
- GT support: No dropouts from the study
- Evidence row: {}
- Source context preview: ## Clinical findings 17/19 patients completed the study: one IFNB-patient withdrew consent (day 34) because she could not comply with study procedures; one NTZ-patient opted for an oral treatment (day 139). One IFNB-patient (#9) switched to rescue treatment at day 69 due to systemic side effects. --- ## Methods Statistical analyses were performed using non-parametric tests for continuous variables and ordinal scores, and considered significant at the level α=0.05. Analysis was based on intention to treat. This pilot study was conducted to generate first data and hypotheses for the planning of further clinical trials. The sample size was set to 20 patients, i.e. 10 patients per group and was...


## 26251065 - Reme 2015

- Mode: hybrid
- Review context: none (0 chars)
- Article chars: 32203
- Extraction context chars: 12003
- Total seconds: 52.45

### Methodology Extraction

- `randomization_method`: "The participants were randomised with a computer-generated randomisation list stratified by centre."
- `allocation_concealment_method`: "At each centre, the person responsible for inclusion emailed the research unit, presented the participant’s project ID number, name and gender before treatment allocation was disclosed. The allocation code, including details of block size (10), was not revealed to the researchers or the clinicians until recruitment and data collection were complete."
- `blinding_participants`: Not reported
- `blinding_personnel`: Not reported
- `blinding_outcome_assessors`: "The authors in charge of the data analysis were blinded for intervention assignment."
- `attrition_details`: "Data on the main outcome measure, work participation, were complete for all participants. However, for secondary outcomes based on self-report, 740 (62%) participants at 6 months follow-up and 636 (52%) participants at..."
- `study_design`: Pragmatic randomised controlled multicentre trial (RCT)
- `additional_notes`: Randomisation used a computer-generated list stratified by centre with block size reported as 10; initial unbalanced 2:1 allocation in first 5 months is stated: "The unbalanced allocation (a 2:1 randomisation ratio in the first 5 months of recruitment) ensured that the centres could run according to maximal capacity." Intention-to-treat principle applied: "Analyses adhered to the ‘intention-to-treat’ principle." For secondary outcomes analyses used inverse probability weights to account for...

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Low risk | yes | article_text_match |  |
| Allocation concealment | Low risk | Low risk | yes | no_support_phrase_match |  |
| Blinding of participants and personnel: All outcomes | High risk | Low risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Blinding of outcome assessment: All outcomes | High risk | High risk / Low risk | yes | no_support_phrase_match |  |
| Incomplete outcome data: All outcomes | Low risk | Low risk | yes | article_text_match |  |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: generated randomisation list strati
- Model rationale: The trial explicitly reports a computer-generated randomisation list stratified by centre, which constitutes an adequate random component per Cochrane criteria, so risk of bias from sequence generation is low.
- Model support: Quote: "The participants were randomised with a computer-generated randomisation list stratified by centre." Comment: Probably done — a computer-generated random sequence (stratified by centre) is described, which meets the criteria for adequate random sequence generation.
- Model support context: [{"source": "article", "quote": "The participants were randomised with a computer-generated randomisation list stratified by centre.", "relevance": "Describes use of a computer random number generator, an adequate random component for sequence generation."}, {"source": "methodology", "quote": "\"Randomisation used a computer-generated list stratified by centre with block size reported as 10; initial unbalanced 2:1 allocation in first 5 months\"", "relevance": "Confirms computer generation and stratification; block size/ratio details do not invalidate randomness."}]
- GT support: Quote: "computer‐generated randomisation list stratiﬁed by centre."
- Evidence row: {}
- Source context preview: ## Randomisation The participants were randomised with a computer-generated randomisation list stratified by centre. At each centre, the person responsible for inclusion emailed the research unit, presented the participant’s project ID number, name and gender before treatment allocation was disclosed. The allocation code, including details of block size (10), was not revealed to the researchers or the clinicians until recruitment and data collection were complete. --- ## Procedure 1416 potential participants were referred and considered for inclusion (6/1/2010–2/1/2012). Of these, 197 did not fulfil the inclusion criteria, 17 did not consent to participate, and 9 withdrew their consent and...

#### Allocation concealment

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Allocation was performed centrally by a research unit after centres emailed participant details; the allocation code and block size were not revealed to site staff, so recruiters could not foresee assignments, meeting criteria for low risk.
- Model support: Quote: "At each centre, the person responsible for inclusion emailed the research unit, presented the participant’s project ID number, name and gender before treatment allocation was disclosed. The allocation code, including details of block size (10), was not revealed to the researchers or the clinicians until recruitment and data collection were complete." Comment: Probably done — centralised allocation via the research unit prevented recruiters/enrollers at centres from foreseeing or manipulating assignments.
- Model support context: [{"source": "article", "quote": "At each centre, the person responsible for inclusion emailed the research unit... before treatment allocation was disclosed.", "relevance": "Describes centralised allocation process that prevents local foreseeability of assignments."}, {"source": "methodology", "quote": "\"The participants were randomised with a computer-generated randomisation list stratified by centre.\"", "relevance": "Shows independent computer-generated sequence held centrally, supporting concealment."}]
- GT support: Quote: "The allocation code, including details of block size (10), was not revealed to the researchers or the clinicians until recruitment and data collection were complete."
- Evidence row: {}
- Source context preview: ## Randomisation The participants were randomised with a computer-generated randomisation list stratified by centre. At each centre, the person responsible for inclusion emailed the research unit, presented the participant’s project ID number, name and gender before treatment allocation was disclosed. The allocation code, including details of block size (10), was not revealed to the researchers or the clinicians until recruitment and data collection were complete. --- ## Procedure 1416 potential participants were referred and considered for inclusion (6/1/2010–2/1/2012). Of these, 197 did not fulfil the inclusion criteria, 17 did not consent to participate, and 9 withdrew their consent and...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: There is no report of participant or personnel blinding and participants were explicitly informed of allocation; secondary outcomes are self-reported and therefore likely to be influenced by knowledge of group assignment, meeting criteria for high risk of performance bias.
- Model support: Quote: "After random allocation, participants were informed about the outcome, and the intervention group was given a date for its first session." Comment: Participants and local personnel were apparently informed of allocation after randomisation and no participant or personnel blinding is reported; outcomes include self-reported mental-health secondary measures susceptible to performance effects. Probably not done.
- Model support context: [{"source": "article", "quote": "After random allocation, participants were informed about the outcome, and the intervention group was given a date for its first session.", "relevance": "Shows participants were notified of their group and therefore not blinded."}, {"source": "methodology", "quote": "blinding_participants: Not reported; blinding_personnel: Not reported; data on main outcome obtained from registers with 'no loss to follow-up'.", "relevance": "No evidence of participant/personnel blinding and several outcomes were self-reported and likely influenced by lack of blinding."}]
- GT support: Sick Leave Comment: Unblinded but unlikely that this will have led to different behaviour
- Evidence row: {}
- Source context preview: ## Procedure 1416 potential participants were referred and considered for inclusion (6/1/2010–2/1/2012). Of these, 197 did not fulfil the inclusion criteria, 17 did not consent to participate, and 9 withdrew their consent and required data deletion (see online supplementary figure). In total, 1193 participants entered the trial and were randomised, 52.8% (n=630) to the intervention group and 47.2% (n=563) to the control group. The unbalanced allocation (a 2:1 randomisation ratio in the first 5 months of recruitment) ensured that the centres could run according to maximal capacity. The randomisation procedure strictly adhered to the formal requirements of adequate randomisation at all times...

#### Blinding of outcome assessment: All outcomes

- Prediction: High risk
- Ground truth: High risk / Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Primary outcomes were objective registry-derived data with complete follow-up and data analysts were blinded; thus outcome measurement was unlikely to be influenced by knowledge of allocation, supporting Low risk of detection bias. Calibration: outcomes were self-reported and participants could know allocation, so participants acted as unmasked outcome assessors.
- Model support: Quote: "Data on the main outcome measure, work participation, were complete for all participants." Comment: Outcome assessment for the primary outcome was obtained from registers (objective, administrative data) with no loss to follow-up; data analysts were blinded. Probably done: outcome measurement was unlikely to be influenced by assessor knowledge. Comment: Calibration: outcomes were self-reported and participants could know allocation, so participants acted as unmasked outcome assessors.
- Model support context: [{"source": "article", "quote": "bility, a clinical psychologist assessed the presence of common mental disorders. This assessment was based on informal self-reports of symptoms and symptoms consistent with anxiety and/or depression. This included the subthreshold...", "relevance": "Calibration: outcomes were self-reported and participants could know allocation, so participants acted as unmasked outcome assessors."}, {"source": "methodology", "quote": "Data on the main outcome measure, work participation, were complete for all participants.", "relevance": "Shows primary outcome came from complete register data, objective and unlikely to be biased by assessor knowledge."}]
- GT support: Sick Leave Comment: Participants could not be blinded but outcome objective register‐based | Depressive symptoms Comment: Unblinded and self‐report
- Evidence row: {}
- Source context preview: ## Procedure Potential participants were informed about the project and screened for inclusion and exclusion criteria at the centres by a clinical psychologist. Eligible and willing participants signed the informed consent and completed the baseline questionnaire. After random allocation, participants were informed about the outcome, and the intervention group was given a date for its first session. --- ## Statistical methods For the main effect analysis, we observed crude rates of participants with increased work participation in the two groups. The effects of treatment were further examined by logistic and multinomial logistic regression analyses when adjusting for minor by-chance...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: formed analyses with inverse probability weights
- Model rationale: The primary outcome was obtained from national registers with no loss to follow-up, satisfying criteria for low risk of attrition bias for main outcomes; secondary outcomes had higher missingness but were addressed with inverse probability weighting and ITT, so overall attrition is unlikely to materially bias the primary findings.
- Model support: Quote: "Data on the main outcome measure, work participation, were complete for all participants." Comment: Primary outcome had no loss to follow-up (registry-based). Secondary self-report outcomes had substantial missingness but authors used inverse probability weighting and ITT; primary outcome risk of attrition bias is therefore low and unlikely to materially bias main trial conclusions.
- Model support context: [{"source": "methodology", "quote": "\"Data on the main outcome measure, work participation, were complete for all participants.\"", "relevance": "Shows no missing data for the primary outcome from registry sources, eliminating attrition bias for main effect."}, {"source": "article", "quote": "For the secondary outcomes (mental health), we performed analyses with inverse probability weights22 to account for possible attrition bias.", "relevance": "Indicates appropriate methods were used to handle missing secondary outcome data, reducing bias concerns for those analyses."}]
- GT support: Depressive symptoms Quote: For the secondary outcomes (mental health), we per‐ formed analyses with inverse probability weights 22 to account for possible attrition bias. Analyses adhered to the ‘intention‐to‐treat’ principle. | Sick Leave Comment: Data on the main outcome measure, work participation, were complete for all participants.
- Evidence row: {}
- Source context preview: ## Implications for research and practice Our main recommendation for future research is thus to run more trials of this kind to rapidly improve our evidence base on this vital topic. We recommend using registry-based outcomes where available, with long-term follow-up whenever possible, and also further trials and replications where combinations of CBT and job support are offered. Our results, and the rapidly growing IPS literature for severe mental disorders, suggest that this might be a viable route to reduced workforce dropout from mental disorders. --- ## Outcomes Using data from the national social insurance register and the national employee register, we could (with no loss to...


## 27007650 - Moosanejad 2016

- Mode: hybrid
- Review context: none (0 chars)
- Article chars: 15083
- Extraction context chars: 12003
- Total seconds: 54.17

### Methodology Extraction

- `randomization_method`: After matching the patients in terms of age, gender, and underlying disease, they were randomized into two groups (Figure 1).
- `allocation_concealment_method`: Not reported
- `blinding_participants`: Not reported
- `blinding_personnel`: Not reported
- `blinding_outcome_assessors`: Not reported
- `attrition_details`: Eighty-four patients were enrolled in this study. In the totally tubeless PCNL group, "in any patients with residual stones, rupture, or major bleeding, a nephrostomy catheter was inserted and the patients were excluded from the study." No numbers of exclusions or losses to follow-up per group are reported elsewhere. No information on handling of missing data is reported.
- `study_design`: Randomized, clinical trial
- `additional_notes`: The trial registration number is provided: IRCT: 201407256803N8. Sample size calculation stated: "Based on a study by Crook et al. (12) with a power of 80% and a significance level of 0.05, a sample size of 80 patients was required (n=80). Therefore, 113 patients were enrolled and divided into two groups (Figure 1)." Actual analyzed sample reported as 84 patients. Randomization was after matching for age, gender, and underlying disease. Operations and postoperative care procedures are described...

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Unclear risk | Unclear risk | yes | unknown |  |
| Allocation concealment | Unclear risk | Unclear risk | yes | unknown |  |
| Blinding of participants and personnel: All outcomes | Unclear risk | High risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Blinding of outcome assessment: All outcomes | Unclear risk | High risk / Low risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Incomplete outcome data: All outcomes | High risk | High risk / Low risk | yes | article_text_match |  |

### Audit Details

#### Random sequence generation

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: The paper asserts randomization but provides no information on how the random sequence was generated. Under Cochrane criteria, absence of a described random component requires rating as Unclear risk rather than Low or High.
- Model support: Quote: "After matching the patients in terms of age, gender, and underlying disease, they were randomized into two groups (Figure 1)." Comment: The report states patients were "randomized" but gives no details about the method used to generate the random sequence (e.g. computer, random numbers, coin toss). Therefore sequence generation is unclear.
- Model support context: [{"source": "article", "quote": "After matching the patients in terms of age, gender, and underlying disease, they were randomized into two groups (Figure 1).", "relevance": "States randomization occurred but gives no description of the random sequence generation method."}, {"source": "methodology", "quote": "Randomization after matching for age, gender, and underlying disease; allocation concealment not reported.", "relevance": "Confirms matching then randomization and absence of allocation-concealment details, leaving sequence generation unspecified."}]
- GT support: No information on sequence generation
- Evidence row: {}
- Source context preview: ## Methods of operations After matching the patients in terms of age, gender, and underlying disease, they were randomized into two groups (Figure 1): 44 patients (24 men; mean age 50.40±2.02 years) were in the totally tubeless PCNL group and 40 patients (18 men; mean age 49.95±13.38 years) were in the standard PCNL group. Preoperative tests included measurement of hemoglobin levels, serum creatinine levels, and size and location of stones. Radiological evaluation was performed with ultrasonography, intravenous pyelography, and computed tomography scans. The patients received general anesthesia. The patients were placed in the lithotomy position to insert a ureteral catheter (4F-5F). They...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: Because the trial report does not describe any method to prevent recruiters/enrollers from foreseeing assignments (central randomization, sealed envelopes, etc.), and no safeguards are reported, there is insufficient information to assess the risk of selection bias from allocation concealment.
- Model support: Comment: allocation concealment not reported. The paper states only that after matching patients they "were randomized into two groups (Figure 1)" but gives no details on how assignments were concealed, so insufficient information to judge.
- Model support context: [{"source": "article", "quote": "After matching the patients in terms of age, gender, and underlying disease, they were randomized into two groups (Figure 1).", "relevance": "Describes randomization but gives no information about concealment of allocation prior to enrolment."}, {"source": "methodology", "quote": "allocation_concealment_method: \"Not reported\"", "relevance": "Explicitly notes that the study report provides no details on allocation concealment."}]
- GT support: No information on allocation concealment
- Evidence row: {}
- Source context preview: ## Methods of operations After matching the patients in terms of age, gender, and underlying disease, they were randomized into two groups (Figure 1): 44 patients (24 men; mean age 50.40±2.02 years) were in the totally tubeless PCNL group and 40 patients (18 men; mean age 49.95±13.38 years) were in the standard PCNL group. Preoperative tests included measurement of hemoglobin levels, serum creatinine levels, and size and location of stones. Radiological evaluation was performed with ultrasonography, intravenous pyelography, and computed tomography scans. The patients received general anesthesia. The patients were placed in the lithotomy position to insert a ureteral catheter (4F-5F). They...

#### Blinding of participants and personnel: All outcomes

- Prediction: Unclear risk
- Ground truth: High risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Because the paper does not report any blinding measures for participants or personnel and postoperative pain (a subjective outcome) is a key outcome, there is insufficient information to judge whether lack of blinding could have biased results; therefore the risk is unclear.
- Model support: Comment: The report does not state whether participants or personnel were blinded. No information is provided about attempts to blind surgical teams or patients, and outcomes such as postoperative pain could be influenced by lack of blinding. Given the missing details, risk of performance bias cannot be determined.
- Model support context: [{"source": "methodology", "quote": "blinding_participants: \"Not reported\"; blinding_personnel: \"Not reported\"; blinding_outcome_assessors: \"Not reported\"", "relevance": "Direct statement that blinding of participants, personnel, and assessors is not reported."}, {"source": "article", "quote": "The patients received general anesthesia. ... After 4 or 5 h, the ureteral catheter and Foley catheter were removed in the totally tubeless PCNL group.", "relevance": "Describes surgical/perioperative procedures; indicates subjective outcomes (pain) are likely relevant and could be influenced by knowledge of allocation."}]
- GT support: Judgment Comment: The study design did not include any blinding of participants or personnel. All outcomes seem to be susceptible to performance bias.
- Evidence row: {}
- Source context preview: ## Methods of operations After matching the patients in terms of age, gender, and underlying disease, they were randomized into two groups (Figure 1): 44 patients (24 men; mean age 50.40±2.02 years) were in the totally tubeless PCNL group and 40 patients (18 men; mean age 49.95±13.38 years) were in the standard PCNL group. Preoperative tests included measurement of hemoglobin levels, serum creatinine levels, and size and location of stones. Radiological evaluation was performed with ultrasonography, intravenous pyelography, and computed tomography scans. The patients received general anesthesia. The patients were placed in the lithotomy position to insert a ureteral catheter (4F-5F). They...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: High risk / Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report does not state whether outcome assessors were blinded. While some outcomes are objective, others (pain, complications) are susceptible to detection bias and assessor blinding is unknown, so risk is unclear.
- Model support: Comment: Blinding of outcome assessment not reported. There is insufficient information to determine whether outcome assessors were blinded or whether measurement was likely affected by lack of blinding.
- Model support context: [{"source": "methodology", "quote": "blinding_outcome_assessors: \"Not reported\"", "relevance": "Direct statement that outcome assessor blinding was not reported, leaving uncertainty about detection bias."}, {"source": "article", "quote": "Preoperative tests included measurement of hemoglobin levels, serum creatinine levels, and size and location of stones.", "relevance": "Some outcomes are objective lab/imaging measures (less likely biased), but many clinical outcomes (pain, complications) are subjective and assessor blinding is..."}]
- GT support: Objective outcomes Judgment Comment: The study design did not include any blinding. However, the risk of bias for objective outcomes seems to be low. | Subjective outcomes Judgment Comment: There was no blinding, making subjective outcomes susceptible to detection bias.
- Evidence row: {}
- Source context preview: ## Methods of operations After matching the patients in terms of age, gender, and underlying disease, they were randomized into two groups (Figure 1): 44 patients (24 men; mean age 50.40±2.02 years) were in the totally tubeless PCNL group and 40 patients (18 men; mean age 49.95±13.38 years) were in the standard PCNL group. Preoperative tests included measurement of hemoglobin levels, serum creatinine levels, and size and location of stones. Radiological evaluation was performed with ultrasonography, intravenous pyelography, and computed tomography scans. The patients received general anesthesia. The patients were placed in the lithotomy position to insert a ureteral catheter (4F-5F). They...

#### Incomplete outcome data: All outcomes

- Prediction: High risk
- Ground truth: High risk / Low risk
- Match: True
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: a sample size of 80 patients was required (n=80). therefore, 113 patients were enrolled
- Model rationale: Patients were excluded for reasons directly related to outcomes (residual stones, rupture, bleeding) and the manuscript fails to report how many were excluded per group or how missing data were handled, a scenario likely to introduce biased effect estimates.
- Model support: Quote: "Among this group, in any patients with residual stones, rupture, or major bleeding, a nephrostomy catheter was inserted and the patients were excluded from the study." Comment: The report states that patients meeting intraoperative complications were excluded from the study, but no numbers of exclusions or losses to follow-up per group are reported and there is no information on handling or imputation of missing outcome data. This suggests outcome-related exclusions likely biased results (Probably not handled appropriately).
- Model support context: [{"source": "article", "quote": "Among this group, in any patients with residual stones, rupture, or major bleeding, a nephrostomy catheter was inserted and the patients were excluded from the study.", "relevance": "Shows exclusion based on intraoperative outcomes likely related to the study outcomes, introducing attrition bias."}, {"source": "methodology", "quote": "No numbers of exclusions or losses to follow-up per group are reported elsewhere. No information on handling of missing data is reported.", "relevance": "Confirms missing data amounts and handling are not reported, preventing assessment and suggesting high risk."}]
- GT support: All other outcomes Judgment Comment: In total, 5/45 participants (standard PNL) and 1/45 participants (totally tubeless PNL) were lost to follow‐up. The authors present these outcomes as if no patients were excluded from the analyses (see Figure 1). "... a sample size of 80 patients was required (n=80). Therefore, 113 patients were enrolled ...". Reasons for the lost participants are not reported. | Operative time and length of hospital stay Judgment Comment: In total, 5/45 participants (standard PNL) and 1/45 participants (totally tubeless PNL) were lost to follow‐up. The authors present this outcome as if no patients were excluded from the analyses (see Figure 1). "... a sample size of 80 patients was required (n=80). Therefore, 113 patients were enrolled ...". Reasons for the lost participants are not reported. | Postoperative pain Judgment Comment: In total, 5/45 participants...
- Evidence row: {}
- Source context preview: ## Methods of operations After matching the patients in terms of age, gender, and underlying disease, they were randomized into two groups (Figure 1): 44 patients (24 men; mean age 50.40±2.02 years) were in the totally tubeless PCNL group and 40 patients (18 men; mean age 49.95±13.38 years) were in the standard PCNL group. Preoperative tests included measurement of hemoglobin levels, serum creatinine levels, and size and location of stones. Radiological evaluation was performed with ultrasonography, intravenous pyelography, and computed tomography scans. The patients received general anesthesia. The patients were placed in the lithotomy position to insert a ureteral catheter (4F-5F). They...


## 27022338 - Amirkhanlou 2016

- Mode: hybrid
- Review context: none (0 chars)
- Article chars: 11249
- Extraction context chars: 11249
- Total seconds: 50.9

### Methodology Extraction

- `randomization_method`: Patients were randomly assigned to two groups of 26 subjects (groups G and K).
- `allocation_concealment_method`: Not reported
- `blinding_participants`: "The patients and drug distributors were not aware of the prescribed medications."
- `blinding_personnel`: "The patients and drug distributors were not aware of the prescribed medications."
- `blinding_outcome_assessors`: Not reported
- `attrition_details`: A total of 52 hemodialysis patients with uremic pruritus in two groups were treated with gabapentin and ketotifen. No losses to follow-up, exclusions, or reasons for missing data are reported. Handling of missing data is Not reported.
- `study_design`: Double-blind randomized clinical trial
- `additional_notes`: Interventions: gabapentin capsules 100 mg daily for 2 weeks (Group G) and ketotifen 1 mg twice daily for 2 weeks (Group K). Baseline matching: "before beginning the study, serum calcium, phosphorus and hemoglobin were reached to above 8 mg/dL, less than 5 mg/dL and about 11 to 12 gr/dL, respectively, and the patient were controlled about anemia and hyperparathyroidism." Outcome measure: pruritus severity based on Shiratori’s severity scores. Data analyzed with SPSS-21 using chi-square, t tests,...

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Unclear risk | Unclear risk | yes | article_text_match |  |
| Allocation concealment | Unclear risk | Low risk | no | article_text_match | under-called_due_to_missing_or_underused_evidence |
| Blinding of participants and personnel: All outcomes | Low risk | Low risk | yes | article_text_match |  |
| Blinding of outcome assessment: All outcomes | Unclear risk | Unclear risk | yes | unknown |  |
| Incomplete outcome data: All outcomes | Low risk | Low risk | yes | unknown |  |

### Audit Details

#### Random sequence generation

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: patients were randomly assigned
- Model rationale: The paper only reports that patients were "randomly assigned" but does not describe the procedure used to generate the allocation sequence; therefore there is insufficient information to judge whether the sequence was truly random.
- Model support: Quote: "Patients were randomly assigned to two groups of 26 subjects (groups G and K)." Comment: The report states that patients were "randomly assigned" but gives no details of the random sequence generation method (e.g. computer, table, coin). Insufficient information to determine whether a truly random process was used — Unclear risk.
- Model support context: [{"source": "article", "quote": "Patients were randomly assigned to two groups of 26 subjects (groups G and K).", "relevance": "States random assignment but provides no method for sequence generation."}, {"source": "methodology", "quote": "randomization_method: \"Patients were randomly assigned to two groups of 26 subjects (groups G and K).\"", "relevance": "Extracted methods reiterate random assignment without describing the randomization procedure."}]
- GT support: QUOTE: "Patients were randomly assigned".
- Evidence row: {}
- Source context preview: ## METHODS This double-blind randomized clinical trial was conducted after approval from the Research Ethics Committee of Golestan University of Medical Sciences. Of 182 hemodialysis patients referred to 5 azar Teaching Hospital in Gorgan in 2013, 52 eligible patients with uremic pruritus were selected. All patients undergoing hemodialysis were similar in frequency and method (maximum duration and frequency of hemodialysis) and patients suffering from itchy skin condition (non-uremic pruritus) were excluded. Patients were randomly assigned to two groups of 26 subjects (groups G and K). In group G, patients treated with gabapentin capsules (Iran Daroo Pharmaceutical Co., Tehran, Iran) 100 mg...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: the patients and drug distributors were not aware of the prescribed medications
- Model rationale: The report states random assignment but gives no information on allocation concealment (no central randomization, opaque/sequential envelopes, or equivalent). Because concealment is not described, risk of selection bias cannot be judged and is therefore Unclear.
- Model support: Quote: "Patients were randomly assigned to two groups of 26 subjects (groups G and K)." Comment: Allocation concealment method not reported in the paper. There is no description of central randomization, sealed envelopes, or other safeguards, so concealment is unclear (Probably not done or not reported).
- Model support context: [{"source": "article", "quote": "Patients were randomly assigned to two groups of 26 subjects (groups G and K).", "relevance": "Shows random allocation was performed but gives no detail on how assignments were concealed prior to enrolment."}, {"source": "methodology", "quote": "allocation_concealment_method: \"Not reported\"", "relevance": "Explicitly indicates the paper did not report the method used to prevent foreknowledge of assignments."}]
- GT support: QUOTE: "The patients and drug distributors were not aware of the prescribed medications".
- Evidence row: {}
- Source context preview: ## METHODS This double-blind randomized clinical trial was conducted after approval from the Research Ethics Committee of Golestan University of Medical Sciences. Of 182 hemodialysis patients referred to 5 azar Teaching Hospital in Gorgan in 2013, 52 eligible patients with uremic pruritus were selected. All patients undergoing hemodialysis were similar in frequency and method (maximum duration and frequency of hemodialysis) and patients suffering from itchy skin condition (non-uremic pruritus) were excluded. Patients were randomly assigned to two groups of 26 subjects (groups G and K). In group G, patients treated with gabapentin capsules (Iran Daroo Pharmaceutical Co., Tehran, Iran) 100 mg...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: the patients and drug distributors were not aware of the prescribed medications
- Model rationale: The study explicitly reports double-blinding and that patients and drug distributors were unaware of treatment allocation. Given participant blinding for a subjective, self-reported pruritus outcome, this likely prevented performance bias, supporting a Low risk judgement.
- Model support: Quote: "The patients and drug distributors were not aware of the prescribed medications." Comment: Reported as a double-blind randomized clinical trial with patients and drug distributors blinded, and the outcome (pruritus severity using Shiratori’s scores) is subject-reported but participants were reportedly masked. Probably done — blinding of participants was implemented and is likely to have reduced performance bias.
- Model support context: [{"source": "article", "quote": "This double-blind randomized clinical trial... The patients and drug distributors were not aware of the prescribed medications.", "relevance": "States trial was double-blind and that patients and those dispensing drugs were unaware of allocations."}, {"source": "methodology", "quote": "\"The patients and drug distributors were not aware of the prescribed medications.\"", "relevance": "Confirms blinding of participants/personnel relevant to performance bias for patient-reported outcomes."}]
- GT support: QUOTE: "The patients and drug distributors were not aware of the prescribed medications".
- Evidence row: {}
- Source context preview: ## METHODS This double-blind randomized clinical trial was conducted after approval from the Research Ethics Committee of Golestan University of Medical Sciences. Of 182 hemodialysis patients referred to 5 azar Teaching Hospital in Gorgan in 2013, 52 eligible patients with uremic pruritus were selected. All patients undergoing hemodialysis were similar in frequency and method (maximum duration and frequency of hemodialysis) and patients suffering from itchy skin condition (non-uremic pruritus) were excluded. Patients were randomly assigned to two groups of 26 subjects (groups G and K). In group G, patients treated with gabapentin capsules (Iran Daroo Pharmaceutical Co., Tehran, Iran) 100 mg...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: The trial is described as double-blind and patients were unaware of allocation, but there is no explicit information that outcome assessment was performed by blinded assessors. Given the subjective, self-reported nature of pruritus severity, lack of clear assessor blinding could materially bias results, so insufficient information leads to Unclear risk.
- Model support: Quote: "The patients and drug distributors were not aware of the prescribed medications." Comment: Study reports double-blind conduct and that patients and drug distributors were unaware, but there is no explicit statement about blinding of outcome assessors. Because outcomes (pruritus severity using Shiratori’s scores) are subjective patient-reported measures, and it is unclear whether outcome assessment was performed by blinded assessors or relied on unblinded staff or the patients themselves, risk of detection bias cannot be determined. Probably done for participant blinding but unclear for outcome assessor blinding.
- Model support context: [{"source": "article", "quote": "The patients and drug distributors were not aware of the prescribed medications.", "relevance": "Indicates some blinding but does not state whether outcome assessors were blinded."}, {"source": "methodology", "quote": "blinding_outcome_assessors: Not reported", "relevance": "Confirms absence of explicit information about assessor blinding; outcome is subjective (pruritus score)."}]
- GT support: No information
- Evidence row: {}
- Source context preview: ## METHODS This double-blind randomized clinical trial was conducted after approval from the Research Ethics Committee of Golestan University of Medical Sciences. Of 182 hemodialysis patients referred to 5 azar Teaching Hospital in Gorgan in 2013, 52 eligible patients with uremic pruritus were selected. All patients undergoing hemodialysis were similar in frequency and method (maximum duration and frequency of hemodialysis) and patients suffering from itchy skin condition (non-uremic pruritus) were excluded. Patients were randomly assigned to two groups of 26 subjects (groups G and K). In group G, patients treated with gabapentin capsules (Iran Daroo Pharmaceutical Co., Tehran, Iran) 100 mg...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: The report presents outcome data for all 52 randomized participants with no losses or exclusions described, so missing outcome data are absent and unlikely to introduce bias, meeting criteria for Low risk.
- Model support: Quote: "A total of 52 hemodialysis patients with uremic pruritus in two groups were treated with gabapentin and ketotifen." Comment: No losses to follow-up, exclusions, or missing outcome data are reported; therefore missing outcome data are nil and unlikely to bias results (Probably done).
- Model support context: [{"source": "article", "quote": "A total of 52 hemodialysis patients with uremic pruritus in two groups were treated with gabapentin and ketotifen.", "relevance": "Indicates full sample (52) in results with no mention of dropouts or missing outcome data."}, {"source": "methodology", "quote": "No losses to follow-up, exclusions, or reasons for missing data are reported.", "relevance": "Explicitly notes there were no reported missing data, supporting low attrition bias."}]
- GT support: No attrition
- Evidence row: {}
- Source context preview: ## METHODS This double-blind randomized clinical trial was conducted after approval from the Research Ethics Committee of Golestan University of Medical Sciences. Of 182 hemodialysis patients referred to 5 azar Teaching Hospital in Gorgan in 2013, 52 eligible patients with uremic pruritus were selected. All patients undergoing hemodialysis were similar in frequency and method (maximum duration and frequency of hemodialysis) and patients suffering from itchy skin condition (non-uremic pruritus) were excluded. Patients were randomly assigned to two groups of 26 subjects (groups G and K). In group G, patients treated with gabapentin capsules (Iran Daroo Pharmaceutical Co., Tehran, Iran) 100 mg...


## 27463536 - Gordon 2017

- Mode: hybrid
- Review context: none (0 chars)
- Article chars: 33699
- Extraction context chars: 12003
- Total seconds: 60.57

### Methodology Extraction

- `randomization_method`: "randomized participants, using 1:1 equal allocation, to receive either routine education only (control arm) or Inform Me after attending routine education (intervention arm), using a computer-generated random number list, with individual numbers inserted into sequentially numbered, sealed envelopes concealed until study arm was assigned. Randomization was stratified by site."
- `allocation_concealment_method`: "individual numbers inserted into sequentially numbered, sealed envelopes concealed until study arm was assigned."
- `blinding_participants`: "The trial was single blinded; research team members assessing outcomes (EJG, MWS, MGI) were blinded to assignments to the intervention."
- `blinding_personnel`: Not reported
- `blinding_outcome_assessors`: "The trial was single blinded; research team members assessing outcomes (EJG, MWS, MGI) were blinded to assignments to the intervention."
- `attrition_details`: "Our analysis was based on the intention-to-treat principle and included all persons who were randomized regardless of whether they completed the posttest assessments. We tested the pattern of missing values in Test 1 knowledge scores using a multivariable logistic regression to predict the probability of missing values as a function of all covariates in Table 1. None of them were significantly associated with the probability of Test 1 knowledge scores missing. Because they were missing at...
- `study_design`: "posttest-only control group design"
- `additional_notes`: "On the day of evaluation, intervention arm participants used Inform Me after receiving routine transplant education about IRD kidneys, while control arm participants received routine transplant education about IRD kidneys. Participants received the assigned intervention after completing routine education and clinician visits. All other measures were collected after completing Inform Me (intervention arm) or the knowledge survey (control arm)."

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Low risk | yes | no_support_phrase_match |  |
| Allocation concealment | Low risk | Low risk | yes | article_text_match |  |
| Blinding of participants and personnel: All outcomes | High risk | Unclear risk | no | article_text_match | over-inferred_from_sparse_reporting |
| Blinding of outcome assessment: All outcomes | Low risk | Low risk | yes | article_text_match |  |
| Incomplete outcome data: All outcomes | Low risk | Low risk | yes | no_support_phrase_match |  |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states a computer-generated random number list was used to allocate participants (a recognized random method). This meets Cochrane criteria for low risk of bias from sequence generation.
- Model support: Quote: "staff then randomized participants, using 1:1 equal allocation, to receive either routine education only (control arm) or Inform Me after attending routine education (intervention arm), using a computer-generated random number list, with individual numbers inserted into sequentially numbered, sealed envelopes concealed until study arm was assigned." Comment: Sequence generation used a computer-generated random number list, which is an adequate random component. Probably done.
- Model support context: [{"source": "article", "quote": "using a computer-generated random number list, with individual numbers inserted into sequentially numbered, sealed envelopes concealed until study arm was assigned.", "relevance": "Direct description of random sequence generation method showing use of a computer RNG."}, {"source": "methodology", "quote": "\"randomized participants... using a computer-generated random number list... Randomization was stratified by site.\"", "relevance": "Confirms randomized sequence generation with stratification, supporting adequacy of randomization."}]
- GT support: Staff then randomized participants, using 1:1 equal allocation, to receive either routine education only (control arm) or Inform Me after attending routine education (intervention arm), using a computer-generated random number list, with individual numbers inserted into sequentially numbered, sealed envelopes concealed until study arm was assigned. Randomization was stratified by site.
- Evidence row: {}
- Source context preview: ## Recruitment and Participation As KTCs arrived at the transplant center, research staff confirmed their eligibility and obtained written informed consent. Staff then randomized participants, using 1:1 equal allocation, to receive either routine education only (control arm) or Inform Me after attending routine education (intervention arm), using a computer-generated random number list, with individual numbers inserted into sequentially numbered, sealed envelopes concealed until study arm was assigned. Randomization was stratified by site. --- ## Initial Test Scores After Randomization (Test 1) The mean total knowledge score was 17.06 (range: 1–30) following either routine education only...

#### Allocation concealment

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: with individual numbers inserted into sequentially | individual numbers inserted into sequentially numbered
- Model rationale: The report explicitly states that individual random numbers were placed into sequentially numbered, sealed envelopes and concealed until assignment, which is an accepted method preventing foreseeability of allocations and thus indicates low risk of selection bias from allocation concealment.
- Model support: Quote: "using a computer-generated random number list, with individual numbers inserted into sequentially numbered, sealed envelopes concealed until study arm was assigned." Comment: Probably done — sequentially numbered, sealed envelopes were used to conceal allocation, which prevents foreseeability of assignments and meets the criteria for adequate allocation concealment.
- Model support context: [{"source": "article", "quote": "using a computer-generated random number list, with individual numbers inserted into sequentially numbered, sealed envelopes concealed until study arm was assigned.", "relevance": "Describes the allocation concealment method (sequentially numbered, sealed envelopes) which prevents recruiters foreseeing assignments."}, {"source": "methodology", "quote": "\"individual numbers inserted into sequentially numbered, sealed envelopes concealed until study arm was assigned.\"", "relevance": "Confirms extracted methods data matching the article statement about concealment."}]
- GT support: Using a computer-generated random number list, with individual numbers inserted into sequentially numbered, sealed envelopes concealed until study arm was assigned.
- Evidence row: {}
- Source context preview: ## Recruitment and Participation As KTCs arrived at the transplant center, research staff confirmed their eligibility and obtained written informed consent. Staff then randomized participants, using 1:1 equal allocation, to receive either routine education only (control arm) or Inform Me after attending routine education (intervention arm), using a computer-generated random number list, with individual numbers inserted into sequentially numbered, sealed envelopes concealed until study arm was assigned. Randomization was stratified by site. --- ## Study Design The RCT employed a posttest-only control group design.23 This design was used because of limited time for data collection in the...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: Unclear risk
- Match: False
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: research team members assessing outcomes
- Model rationale: Participants and personnel delivering the interventions were not blinded and the primary outcomes (knowledge scores and willingness) are subjective/self-reported and likely influenced by awareness of receiving an interactive educational app versus control, so risk of performance bias is high.
- Model support: Quote: "The trial was single blinded; research team members assessing outcomes (EJG, MWS, MGI) were blinded to assignments to the intervention." Comment: Participants were not blinded — they used the Inform Me iPad app (intervention) or completed a knowledge survey (control) in clinic, so they and likely personnel delivering the intervention knew allocation. Outcomes were knowledge and willingness (self-reported), which are subjective and highly susceptible to performance effects. Probably not done: participant/personnel blinding.
- Model support context: [{"source": "methodology", "quote": "\"The trial was single blinded; research team members assessing outcomes (EJG, MWS, MGI) were blinded to assignments to the intervention.\"", "relevance": "Shows only outcome assessors (research team) were blinded, not participants or staff."}, {"source": "article", "quote": "On the day of evaluation, intervention arm participants used Inform Me after receiving routine transplant education... control arm participants received routine transplant education... All other measures were collected after completing...", "relevance": "Confirms participants experienced clearly different interventions and completed self-reported knowledge/willingness outcomes after exposure."}]
- GT support: The trial was single-blinded; research team members assessing outcomes (EJG, MWS, MGI) were blinded to assignments to the intervention. Unclear how lack of blinding of participants influenced the outcomes.
- Evidence row: {}
- Source context preview: ## Initial Test Scores After Randomization (Test 1) The mean total knowledge score was 17.06 (range: 1–30) following either routine education only (control) and/or completing initial questions in Inform Me (intervention). The mean ± SD, interquartile range (25%–75%), and minimum-maximum range to complete Inform Me was 47 ± 21, (Median=42, IQR=30–60), (min-max range: 16–100) minutes. Knowledge scores were significantly greater among whites (p<0.001), and participants who had some college or higher education (p<0.001), higher incomes (p<0.001), adequate health literacy (p<0.001), higher Internet self-efficacy (p<0.02), and other characteristics (Table 2). No significant differences in...

#### Blinding of outcome assessment: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: research team members assessing outcomes
- Model rationale: Outcome assessment was performed by blinded research team members and the primary outcomes (knowledge test responses) were electronically transmitted and scored, making it unlikely that knowledge of allocation could have biased measurements, meeting criteria for Low risk.
- Model support: Quote: "The trial was single blinded; research team members assessing outcomes (EJG, MWS, MGI) were blinded to assignments to the intervention." Comment: Blinding of outcome assessors was explicitly reported and is unlikely to have been broken; outcomes were knowledge tests automatically transmitted and scored, reducing measurement bias. Probably done.
- Model support context: [{"source": "methodology", "quote": "\"The trial was single blinded; research team members assessing outcomes (EJG, MWS, MGI) were blinded to assignments to the intervention.\"", "relevance": "Direct statement that outcome assessors were blinded supports low detection bias."}, {"source": "article", "quote": "Responses to Test 1 and Test 2 were automatically electronically transmitted to an online database for analysis.", "relevance": "Objective, automated scoring reduces risk that assessor knowledge could influence outcome measurement."}]
- GT support: The trial was single-blinded; research team members assessing outcomes (EJG, MWS, MGI) were blinded to assignments to the intervention.
- Evidence row: {}
- Source context preview: ## Study Design The RCT employed a posttest-only control group design.23 This design was used because of limited time for data collection in the tight clinic schedule. Inform Me’s efficacy was assessed by comparing the intervention arm with the control arm. On the day of evaluation, intervention arm participants used Inform Me after receiving routine transplant education about IRD kidneys, while control arm participants received routine transplant education about IRD kidneys. Participants received the assigned intervention after completing routine education and clinician visits. All other measures were collected after completing Inform Me (intervention arm) or the knowledge survey (control...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The trial reported ITT analyses, tested and found missingness unrelated to baseline covariates, and applied multiple imputation (MCMC, 20 imputations). Missing data were thus plausibly missing at random and handled with appropriate methods, making meaningful bias unlikely.
- Model support: Quote: "Our analysis was based on the intention-to-treat principle and included all persons who were randomized regardless of whether they completed the posttest assessments. We tested the pattern of missing values in Test 1 knowledge scores... None of them were significantly associated with the probability of Test 1 knowledge scores missing. Because they were missing at random, we imputed them using multiple imputation based on a Bayesian iterative Markov Chain Monte Carlo (MCMC) method... with 20 repetitions." Comment: Study used ITT, examined predictors of missingness, found missingness unrelated to measured covariates, and handled missing data with appropriate multiple imputation. These steps make material bias from incomplete outcome data unlikely. Probably done.
- Model support context: [{"source": "article", "quote": "included all persons who were randomized regardless of whether they completed the posttest assessments.", "relevance": "Shows intention-to-treat inclusion of randomized participants minimizing attrition bias."}, {"source": "article", "quote": "None of them were significantly associated with the probability of Test 1 knowledge scores missing... we imputed them using multiple imputation... with 20 repetitions.", "relevance": "Demonstrates assessment of missingness mechanism and use of appropriate imputation."}]
- GT support: Flow diagram, > 90% of participants included in analysis.
- Evidence row: {}
- Source context preview: ## Statistical Analysis The primary outcome, mean difference in posttest knowledge scores, was used to compare intervention and control arms. Our analysis was based on the intention-to-treat principle and included all persons who were randomized regardless of whether they completed the posttest assessments. We tested the pattern of missing values in Test 1 knowledge scores using a multivariable logistic regression to predict the probability of missing values as a function of all covariates in Table 1. None of them were significantly associated with the probability of Test 1 knowledge scores missing. Because they were missing at random, we imputed them using multiple imputation based on a...

## Workflow Evolution Notes

- Inspect mismatches where prediction is `Unclear risk` but GT is `Low risk`: these usually mean retrieval or Stage 1 extraction missed a concrete methodological phrase.
- Inspect mismatches where prediction is `Low risk` or `High risk` but GT is `Unclear risk`: these usually mean the prompt is allowing too much inference from generic trial language.
- For blinding mismatches, add outcome-type cues to the prompt: self-report outcomes, objective outcomes, assessor-administered outcomes, and whether lack of blinding can materially affect the outcome.
- For allocation concealment mismatches, require the model to distinguish sequence generation from concealment before assignment.