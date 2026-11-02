# DDS local reference data — minimal model context

Place this package in the existing project. Read this README; do not dump the database or data arrays into the model conversation. Use code to query data on disk. The database is non-patient reference data, not a synthetic fixture.

## Files
- data/dds_reference.sqlite — SQLite database; actual supplied provinces, districts and population.
- inspect_reference.py — standard-library smoke test. Run it; its output is a bounded summary, not a data dump.

## Verified contents
- province: 77 provinces. province_code is a two-character string. scr_group_source preserves the supplied สคร column, not a province code or verified current regional classification.
- district: 878 districts in 76 provinces, from the supplied PDF. Four-character district_code; prefix is province_code and suffix is district_local_code. XX00 headings are excluded. No Bangkok districts; no boundary geometries. Source metadata dates to 2023; current administrative boundaries have not been verified. Names were extracted using corrected embedded font mappings, not guessed.
- population_snapshot: 13 periods for 2013–2025. 2025 is November, other snapshots are December; not automatically midyear population.
- population_by_geography: 1,014 rows, 78 per snapshot. Province 00 is the national aggregate and MUST NOT be summed with provinces.
- age_bin: 102 age slots: 0=<1, 1–100=completed years, 101=>100. male_by_age_json/female_by_age_json hold 102 integer counts each. source_counts_json retains source subtotals and special registry categories, without silently redefining their universe.
- population_by_age: SQL view for age/sex-specific queries. Uses SQLite JSON functions. This is a convenient query interface, not independent additional people.
- dataset_metadata: source hashes, dates and coverage limitations.

## Query pattern
Parameterize values. Select only columns/rows needed. Return to the model at most a schema summary, row counts, a few examples and validation results. Never print an unbounded SELECT *, all age arrays or a generated full-data JSON.

Examples (use parameters in application code):

```sql
SELECT province_code,province_name_th FROM province ORDER BY province_code;
SELECT district_code,district_name_th FROM district WHERE province_code=? ORDER BY district_code;
SELECT reference_year,reference_month,population_total_source FROM population_by_geography WHERE province_code='00' ORDER BY reference_year;
SELECT SUM(population) FROM population_by_age WHERE reference_year=? AND province_code=? AND age_index BETWEEN 5 AND 9;
```

The final example gives the all-sex sum for ages 5–9 in a selected geography/year; the population-universe metadata still require verification before using it for a particular nationality denominator.

## Required application corrections
1. Continue the existing project; inspect source files selectively, then implement and test. Do not rebuild from scratch or ask for raw data to be pasted into chat.
2. No hard-coded Phitsanulok comparison anywhere. Province 65 is an ordinary selectable province. Default comparison is none; default scope is eligible imported data, not a presumed nationally representative sample.
3. Match province/district code strings using the same address family. Example 11 + 01 = 1101, เมืองสมุทรปราการ. Do not infer districts from names alone. A missing Bangkok lookup is explicit, not invented.
4. Match denominators by actual year, geography, age, sex and verified population/nationality universe. No district population, no age-by-nationality cross-tabulations and no 2026 population are supplied. Keep supported counts and hospitalization proportions enabled; unsupported rates unavailable. Never divide district cases by provincial population or sum national and province rows together. Missing death/type values are not alive/OPD.
5. Hospitalization proportion = IPD/(IPD+OPD)*100, with unknown type and completeness disclosed. Distinguish it from IPD/population*100000 and cases/population*100000. Single-age population nationality universe has not been verified; do not infer it from a foreign-national grand total. Do not double-count source subtotals.
6. Forecast only the latest available one year, at most 52 complete epi weeks through the data-defined training cutoff, with a visible completeness lag if selected. If shorter history is available, use it and state the actual weeks; do not demand 2–5 years. Preserve real coverage gaps. OLS weekly_cases=beta0+beta1*t+error with a continuous calendar-based index t across New Year. No multi-year seasonality or historical-median requirement. Default forecast 4 weeks, optionally 1–12. Provide model-based prediction intervals, chronological evaluation versus last-observation naive when feasible, and honest insufficient-data states. Keep all training/backtest observations within the latest-year window. Do not use Phitsanulok as a forecast comparator.
7. Preserve time-place-person analysis, district views, Thai/non-Thai comparisons, suitable simple logistic models, summary tables, and presentation figures. All tables/figures/exports share filters and denominators. PNG at actual 3840x2160 pixels plus SVG/PDF and slide-readable table exports; Thai text must render correctly.
8. In model-facing command output, limit samples to 3 rows and summaries to about 2 KB per command. Full results should be saved to project files and consumed by the app, not echoed back to the agent. Do not load historical JSON reference files into chat.

## Checks
Run python inspect_reference.py. It verifies integrity, expected table/view counts, and 2025 national source population 65,826,149. These are reference-data tests, not real patient-file integration tests. Afterwards verify the existing application's import, filters, denominator joins, models and exports with appropriate fixtures.
