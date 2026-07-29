# Audit archive

Each independent audit receives a date-and-slug directory:

    audits/YYYY-MM-DD-<scope>/

A directory should contain the final report, compact reproducible evidence, benchmarks, comparisons, and
a baseline record. Keep raw web reads, temporary fixtures, model outputs containing third-party pages,
and other bulky/generated material ignored inside that audit directory.

Audits are evidence artifacts, not product changes. They must state the exact audited commit, distinguish
observed behavior from recommendation, preserve failed/inconclusive results, and avoid silently changing
the implementation under review.
