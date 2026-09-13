# Validation tables

This directory stores quality-control artifacts produced while constructing the trusted benchmark from the refined baseline.

These files describe the transformation from refined to trusted and therefore are intentionally kept outside `tables_analysis_refined/` and `tables_analysis_trusted/`, whose scientific table sets and schemas must remain identical.

The trusted-data workflow writes:

- `trusted_trim_audit_annual.csv`;
- `trusted_distribution_tests_annual.csv`.
