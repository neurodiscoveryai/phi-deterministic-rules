# Evaluation of the rules against the model's spans

**Provenance.** On 2026-09-16 every span the de-identification model had redacted was recovered from the
pipeline's own output (470,445,960 verified spans over 19.1 M records: notes tables, OCR exports, the HTML/XML
re-run and progressnotes vendor XML). The 52 rules were then run on the SOURCE text of a stratified sample --
89 parts, 42,991 records, all five table groups -- and scored by character overlap against the model's spans
of the same records.

**Vocabulary.** Per model span: *covered* = a rule span of the same label contains it entirely; *same family*
= same family (names, places, institutions, numbers, dates); *any* = any rule span; *partial* = 50-99% covered;
*missed*. Per rule span: *hit same / family / other* = overlaps a model span of that label / family / another
label; *unhit* = overlaps nothing the model redacted -- a LOWER bound on false positives, because the model's
own misses land there and, on vendor-XML identifiers, the model redacted the same key in about half of the
records. Wilson 95% intervals; `n<200` means too few spans to quote.

The reference is the model, not ground truth. Where the model was inconsistent (structural XML ids, system
account names, fee-schedule amounts) this library follows a stated policy instead -- see `policy.md`.

```text
## Recall of LLM spans by label  (covered = a rule span of that label contains the whole LLM span)
label                      n              same label             same family                any rule   partial   missed
identified_number    810,548       33.1% [33.0-33.2]       33.2% [33.1-33.3]       33.4% [33.3-33.5]      0.0%    66.5%
address               75,025       72.3% [72.0-72.6]       72.5% [72.2-72.8]       73.0% [72.7-73.3]      3.3%    23.7%
doctor_name           62,155       62.7% [62.3-63.1]       69.6% [69.2-69.9]       73.1% [72.7-73.4]      5.4%    21.5%
person_name           60,723       23.5% [23.2-23.8]       47.4% [47.0-47.8]       48.1% [47.7-48.5]      2.9%    49.0%
hospital_name         37,323       40.1% [39.6-40.6]       40.7% [40.2-41.2]       43.3% [42.8-43.8]      3.2%    53.5%
signature_block       33,636       49.4% [48.9-50.0]       62.8% [62.3-63.3]       62.9% [62.4-63.4]      4.4%    32.7%
date                  23,814       86.0% [85.6-86.5]       89.4% [89.0-89.8]       89.5% [89.1-89.9]      0.0%    10.5%
zip_code              22,576       80.9% [80.4-81.5]       83.0% [82.5-83.5]       83.1% [82.6-83.6]      0.7%    16.3%
organization          16,657        1.6% [ 1.5- 1.8]       67.3% [66.6-68.0]       69.0% [68.3-69.7]      1.9%    29.1%
phone                  9,181       64.4% [63.4-65.4]       64.7% [63.7-65.6]       65.5% [64.6-66.5]      0.6%    33.9%
age_90_plus            5,893       57.5% [56.2-58.7]       87.0% [86.1-87.8]       87.4% [86.5-88.2]      0.1%    12.6%
fax                    4,559       91.5% [90.6-92.2]       93.9% [93.1-94.5]       93.9% [93.1-94.5]      0.4%     5.7%
location               3,394       29.5% [28.0-31.0]       30.4% [28.9-32.0]       31.6% [30.1-33.2]      0.5%    67.9%
amount                   798       90.1% [87.8-92.0]       90.1% [87.8-92.0]       90.6% [88.4-92.4]      2.0%     7.4%
url                      408       74.8% [70.3-78.7]       74.8% [70.3-78.7]       75.7% [71.3-79.6]      1.5%    22.8%
study_id                 124       39.5% [31.4-48.3]       42.7% [34.4-51.5]       42.7% [34.4-51.5]      0.0%    57.3%
device_id                 64       43.8% [32.3-55.9]       43.8% [32.3-55.9]       43.8% [32.3-55.9]      0.0%    56.2%
email                     28       60.7% [42.4-76.4]       60.7% [42.4-76.4]       75.0% [56.6-87.3]      0.0%    25.0%
ip_address                 2        0.0% [ 0.0-65.8]        0.0% [ 0.0-65.8]        0.0% [ 0.0-65.8]      0.0%   100.0%

## Recall (same family) by table group
label                            OCR run1               OCR run2 markup re-run(HTML/XML)     notes tables(run1)    progressnotes(CCDA)
identified_number       39.4% [38.6-40.2]      36.9% [36.2-37.7]      55.8% [54.3-57.2]      47.5% [45.0-50.0]      32.8% [32.7-32.9]
address                 53.1% [52.4-53.9]      55.5% [54.8-56.3]      53.0% [51.6-54.4]      35.4% [31.5-39.6]      93.2% [93.0-93.5]
doctor_name             68.0% [67.2-68.7]      70.3% [69.5-71.0]      87.4% [86.7-88.1]      85.8% [83.7-87.7]      63.1% [62.5-63.7]
person_name             32.2% [31.3-33.1]      38.9% [38.0-39.9]      66.8% [65.7-67.9]      60.3% [58.7-61.9]      49.1% [48.6-49.7]
hospital_name           20.6% [19.8-21.5]      18.7% [18.0-19.4]       7.4% [ 6.5- 8.4]       9.6% [ 7.9-11.7]      84.5% [83.9-85.1]
signature_block         47.7% [46.1-49.2]      59.3% [58.1-60.5]      70.2% [68.5-71.9]      61.4% [58.6-64.2]      66.1% [65.4-66.7]
date                    86.6% [85.8-87.3]      86.9% [86.1-87.6]      98.3% [97.1-99.0]                  n<200      93.9% [93.3-94.4]
zip_code                69.6% [68.2-70.9]      69.1% [67.9-70.4]      79.4% [77.1-81.5]                  n<200      95.0% [94.6-95.4]
organization            10.4% [ 9.2-11.7]      10.3% [ 8.9-11.8]      15.7% [13.1-18.8]      15.1% [11.6-19.3]      91.3% [90.8-91.8]
phone                   56.6% [54.4-58.8]      57.1% [54.8-59.3]      98.2% [97.4-98.7]                  n<200      55.8% [54.1-57.4]
age_90_plus             81.0% [78.8-83.0]      78.1% [75.4-80.6]                  n<200                  n<200      91.9% [90.9-92.7]
fax                     83.0% [79.5-86.0]      69.7% [65.9-73.3]      99.8% [99.4-99.9]                  n<200      99.8% [99.5-99.9]
location                27.3% [24.4-30.5]      20.3% [18.3-22.6]      64.9% [61.2-68.3]      21.7% [17.3-26.9]      11.4% [ 8.1-15.7]
amount                              n<200      93.4% [91.1-95.1]                  n<200                  n<200                  n<200
url                                 n<200      73.3% [67.0-78.7]                  n<200                  n<200                  n<200
study_id                            n<200                  n<200                  n<200                  n<200                  n<200
device_id                           n<200                  n<200                  n<200                  n<200                  n<200
email                               n<200                  n<200                  n<200                  n<200                  n<200
ip_address                          n<200                  n<200                  n<200                  n<200                  n<200

## Precision per rule  (hit = overlaps an LLM span; unhit is a LOWER bound on FP -- the LLM's own misses land there)
rule                               fired              same label             same family            any LLM span  over-red chars/hit
dob_labelled                      12,877       92.1% [91.6-92.6]       99.6% [99.5-99.7]       99.7% [99.5-99.7]                 0.0
dob_after_guarantor_tokens         5,213       81.3% [80.2-82.3]       82.7% [81.7-83.7]       82.7% [81.7-83.7]                 0.0
age_labelled_90plus                  147       57.8% [49.7-65.5]       57.8% [49.7-65.5]       58.5% [50.4-66.2]                 0.0
age_suffix_90plus                    504       63.7% [59.4-67.8]       63.7% [59.4-67.8]       63.7% [59.4-67.8]                 0.0
id_labelled                       18,377       81.0% [80.4-81.5]       81.0% [80.4-81.6]       81.3% [80.8-81.9]                 0.1
json_by_name                         315       98.1% [95.9-99.1]       98.1% [95.9-99.1]       98.1% [95.9-99.1]                 0.0
after_final_column                 1,374       82.0% [79.8-83.9]       99.1% [98.4-99.4]       99.1% [98.4-99.4]                 0.0
phone_after_zip_or_comma             580       98.4% [97.1-99.2]      99.8% [99.0-100.0]      99.8% [99.0-100.0]                 0.0
attr_by_name                     708,918       40.3% [40.2-40.4]       42.8% [42.7-42.9]       43.4% [43.3-43.5]                 1.3
elem_by_name                      55,888       91.7% [91.5-92.0]       92.2% [91.9-92.4]       92.2% [92.0-92.4]                 0.1
elem_v_attribute                   2,606        9.8% [ 8.7-11.0]       72.9% [71.2-74.6]       72.9% [71.2-74.6]                 0.0
addr_v_attribute                   1,299       99.6% [99.1-99.8]       99.6% [99.1-99.8]       99.6% [99.1-99.8]                 0.0
birth_v_attribute                    284       84.9% [80.2-88.6]       99.6% [98.0-99.9]       99.6% [98.0-99.9]                 0.0
id_attribute                       2,342       71.2% [69.4-73.0]       71.2% [69.4-73.0]       71.3% [69.5-73.1]                 0.0
xml_id_extension                   INERT
ssn_shape                              6     100.0% [61.0-100.0]     100.0% [61.0-100.0]     100.0% [61.0-100.0]                 0.0
fax_labelled                       2,298       96.9% [96.1-97.5]       97.8% [97.1-98.3]       97.8% [97.1-98.3]                 0.0
phone_labelled                     2,668       97.9% [97.3-98.4]       99.0% [98.6-99.3]       99.0% [98.6-99.3]                 0.0
phone_formatted_unlabelled           961       88.6% [86.4-90.4]       97.0% [95.7-97.9]       97.1% [95.8-98.0]                 0.0
tel_href                              18     100.0% [82.4-100.0]     100.0% [82.4-100.0]     100.0% [82.4-100.0]                 1.8
email_shape                           17     100.0% [81.6-100.0]     100.0% [81.6-100.0]     100.0% [81.6-100.0]                 0.0
url_scheme                            48       97.9% [89.1-99.6]       97.9% [89.1-99.6]       97.9% [89.1-99.6]                 0.0
url_bare_domain                      387       68.5% [63.7-72.9]       69.0% [64.2-73.4]       69.5% [64.7-73.9]                 0.1
ip_shape                              23        0.0% [-0.0-14.3]        0.0% [-0.0-14.3]        0.0% [-0.0-14.3]                 0.0
dollar_amount                      1,730       42.4% [40.1-44.7]       42.4% [40.1-44.7]       42.7% [40.3-45.0]                 0.0
amount_labelled                       86       11.6% [ 6.4-20.1]       11.6% [ 6.4-20.1]       11.6% [ 6.4-20.1]                 0.0
city_state_zip                    13,173       88.2% [87.6-88.7]       95.3% [95.0-95.7]       96.6% [96.2-96.9]                 0.0
upstream_city_then_state           7,164       73.9% [72.8-74.9]       74.0% [73.0-75.0]       79.0% [78.0-79.9]                 0.0
street_line                       11,683       94.3% [93.8-94.7]       94.4% [94.0-94.8]       94.9% [94.4-95.2]                 0.2
po_box                               348       84.2% [80.0-87.7]       84.5% [80.3-87.9]       85.6% [81.6-88.9]                 0.1
address_labelled                   1,804       31.7% [29.6-33.9]       32.9% [30.8-35.1]       39.7% [37.5-42.0]                 7.7
zip_labelled                         108     100.0% [96.6-100.0]     100.0% [96.6-100.0]     100.0% [96.6-100.0]                 0.0
zip_after_state                    4,670       92.2% [91.4-92.9]       95.3% [94.6-95.9]       96.3% [95.8-96.8]                 0.0
location_labelled                  2,839       35.2% [33.5-37.0]       40.0% [38.2-41.8]       65.4% [63.6-67.1]                 1.2
org_with_suffix                    7,220       57.3% [56.2-58.4]       66.4% [65.3-67.5]       67.4% [66.3-68.5]                 1.6
hospital_labelled                  1,953       69.8% [67.8-71.8]       77.4% [75.5-79.2]       82.3% [80.5-83.9]                 2.3
employer_labelled                    274       53.3% [47.4-59.1]       54.4% [48.5-60.2]       58.0% [52.1-63.7]                 1.9
dr_prefix                         11,562       80.6% [79.9-81.3]       83.6% [82.9-84.2]       83.9% [83.2-84.6]                 0.3
name_with_credential              38,986       56.6% [56.1-57.0]       91.4% [91.1-91.7]       92.5% [92.3-92.8]                 0.5
provider_labelled                  4,189       67.5% [66.1-68.9]       86.8% [85.8-87.8]       89.1% [88.1-90.0]                 1.6
by_verb_name                         818       39.5% [36.2-42.9]       79.5% [76.6-82.1]       89.9% [87.6-91.7]                 3.3
signature_labelled                10,442       56.4% [55.4-57.3]       79.3% [78.5-80.1]       79.4% [78.6-80.2]                 1.9
usersig_login                        377       69.8% [64.9-74.2]       70.3% [65.5-74.7]       74.0% [69.4-78.2]                 0.0
patient_labelled                   3,591       48.4% [46.7-50.0]       55.8% [54.2-57.4]       59.7% [58.1-61.3]                 0.4
relative_named                       303       88.8% [84.7-91.9]       89.1% [85.1-92.1]       89.8% [85.8-92.7]                 0.2
honorific                          2,447       96.8% [96.0-97.4]       97.2% [96.5-97.8]       97.2% [96.5-97.8]                 0.0
salutation                           270       42.2% [36.5-48.2]       49.6% [43.7-55.6]       50.4% [44.4-56.3]                 0.6
after_upstream_name_tokens           987       36.8% [33.8-39.8]       36.8% [33.8-39.8]       38.4% [35.4-41.5]                 0.0
xml_name_parts                       509        0.0% [ 0.0- 0.7]        0.0% [ 0.0- 0.7]        0.0% [ 0.0- 0.7]                 0.0
device_labelled                      506        5.5% [ 3.9- 7.9]       31.4% [27.5-35.6]       31.6% [27.7-35.8]                 0.1
study_labelled                       135       31.1% [23.9-39.4]       84.4% [77.4-89.6]       84.4% [77.4-89.6]                 0.0
nct_shape                              9       77.8% [45.3-93.7]       77.8% [45.3-93.7]       77.8% [45.3-93.7]                 0.0
```
