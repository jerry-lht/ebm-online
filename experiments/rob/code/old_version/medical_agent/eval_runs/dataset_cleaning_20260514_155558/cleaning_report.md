# Dataset cleaning report

- Input files: 617
- Accepted core benchmark files: 414
- Accepted article-only files: 346
- Rejected files: 203

Core benchmark rule: keep only files with all five canonical RoB domains, one valid judgement per canonical domain, and article XML text present.

Article-only rule: additionally exclude otherwise-clean files where core support text points to author correspondence, protocol, registry, or other review/external context.

## Reject reason counts

- missing_core_domain: 397
- conflicting_judgements: 61
- unsupported_judgement: 52
- top_level_not_object: 10
- missing_xml_content: 1

## Reject detail counts

- missing_core_domain:blinding of participants and personnel: 134
- missing_core_domain:blinding of outcome assessment: 98
- missing_core_domain:random sequence generation: 57
- missing_core_domain:allocation concealment: 55
- missing_core_domain:incomplete outcome data: 53
- conflicting_judgements:blinding of outcome assessment:High risk|Low risk: 24
- unsupported_judgement:incomplete outcome data:Not applicable: 17
- unsupported_judgement:blinding of participants and personnel:Not applicable: 15
- unsupported_judgement:blinding of outcome assessment:Not applicable: 14
- conflicting_judgements:blinding of participants and personnel:High risk|Low risk: 12
- top_level_not_object: 10
- conflicting_judgements:blinding of outcome assessment:Low risk|Unclear risk: 7
- conflicting_judgements:incomplete outcome data:High risk|Low risk: 5
- conflicting_judgements:blinding of participants and personnel:High risk|Unclear risk: 3
- conflicting_judgements:blinding of participants and personnel:Low risk|Unclear risk: 3
- unsupported_judgement:random sequence generation:Not applicable: 3
- unsupported_judgement:allocation concealment:Not applicable: 3
- conflicting_judgements:incomplete outcome data:High risk|Unclear risk: 2
- conflicting_judgements:incomplete outcome data:Low risk|Unclear risk: 2
- conflicting_judgements:blinding of outcome assessment:High risk|Unclear risk: 2
- conflicting_judgements:incomplete outcome data:High risk|Low risk|Unclear risk: 1
- missing_xml_content: 1

## Removed non-core domain counts

- Selective reporting (reporting bias): 532
- Other bias: 480
- Blinding (performance bias and detection bias): All outcomes: 36
- Are there concerns that the included patients and setting do not match the review question?: 22
- Are there concerns that the target condition as defined by the reference standard does not match the question?: 22
- Could the patient flow have introduced bias?: 22
- Could the reference standard, its conduct, or its interpretation have introduced bias?: 22
- Could the selection of patients have introduced bias?: 22
- Did all patients receive the same reference standard?: 22
- Was a case-control design avoided?: 22
- Was a consecutive or random sample of patients enrolled?: 22
- Did the study avoid inappropriate exclusions?: 20

## Merged duplicate core domain item counts

- blinding of outcome assessment: 46
- incomplete outcome data: 36
- blinding of participants and personnel: 14

## External/review context core-domain counts

- allocation concealment: 25
- blinding of participants and personnel: 20
- random sequence generation: 19
- blinding of outcome assessment: 19
- incomplete outcome data: 17

## Rejected examples

- 15249261.json PMID=15249261: conflicting_judgements:blinding of participants and personnel:High risk|Low risk; conflicting_judgements:blinding of outcome assessment:High risk|Low risk; conflicting_judgements:incomplete outcome data:High risk|Unclear risk
- 19017773.json PMID=19017773: conflicting_judgements:blinding of participants and personnel:High risk|Unclear risk; conflicting_judgements:blinding of outcome assessment:High risk|Low risk
- 19624813.json PMID=19624813: missing_core_domain:random sequence generation; missing_core_domain:allocation concealment; missing_core_domain:blinding of participants and personnel; missing_core_domain:blinding of outcome assessment; missing_core_domain:incomplete outcome data
- 19902798.json PMID=19902798: missing_core_domain:blinding of participants and personnel
- 20102596.json PMID=20102596: missing_core_domain:blinding of participants and personnel; missing_core_domain:blinding of outcome assessment
- 20298571.json PMID=20298571: missing_core_domain:blinding of participants and personnel
- 20418251.json PMID=20418251: missing_core_domain:blinding of participants and personnel; missing_core_domain:blinding of outcome assessment
- 20478960.json PMID=20478960: missing_core_domain:blinding of participants and personnel; missing_core_domain:blinding of outcome assessment
- 20579848.json PMID=20579848: unsupported_judgement:blinding of participants and personnel:Not applicable; unsupported_judgement:blinding of outcome assessment:Not applicable; unsupported_judgement:incomplete outcome data:Not applicable
- 20662805.json PMID=20662805: conflicting_judgements:blinding of outcome assessment:High risk|Low risk
- 20819082.json PMID=20819082: missing_core_domain:blinding of participants and personnel; missing_core_domain:blinding of outcome assessment
- 21329525.json PMID=21329525: top_level_not_object
- 21496343.json PMID=21496343: missing_core_domain:blinding of participants and personnel; missing_core_domain:blinding of outcome assessment
- 21507271.json PMID=21507271: missing_core_domain:random sequence generation; missing_core_domain:allocation concealment; missing_core_domain:blinding of participants and personnel; missing_core_domain:blinding of outcome assessment; missing_core_domain:incomplete outcome data
- 21649880.json PMID=21649880: missing_core_domain:random sequence generation; missing_core_domain:allocation concealment; missing_core_domain:blinding of participants and personnel; missing_core_domain:blinding of outcome assessment; missing_core_domain:incomplete outcome data
- 21666789.json PMID=21666789: missing_core_domain:blinding of participants and personnel
- 21830317.json PMID=21830317: missing_core_domain:blinding of participants and personnel; missing_core_domain:blinding of outcome assessment
- 21970320.json PMID=21970320: unsupported_judgement:blinding of participants and personnel:Not applicable; unsupported_judgement:blinding of outcome assessment:Not applicable; unsupported_judgement:incomplete outcome data:Not applicable
- 22065657.json PMID=22065657: missing_core_domain:random sequence generation; missing_core_domain:allocation concealment; missing_core_domain:blinding of participants and personnel; missing_core_domain:blinding of outcome assessment; missing_core_domain:incomplete outcome data
- 22086522.json PMID=22086522: missing_core_domain:random sequence generation; missing_core_domain:allocation concealment; missing_core_domain:blinding of participants and personnel; missing_core_domain:blinding of outcome assessment; missing_core_domain:incomplete outcome data
