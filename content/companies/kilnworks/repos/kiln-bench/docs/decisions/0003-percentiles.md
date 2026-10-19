# 0003: How we compute percentiles

- Status: accepted
- Author: Ines Duarte
- Reviewers: Kenji Mori, Theo Lindqvist
- Date: 2026-08-12

## Decision

Linear interpolation between the closest ranks:
`statistics.quantiles(values, n=100, method="inclusive")`. Same numbers as
numpy's default, so notebooks and kiln-bench agree. No numpy dependency.

We report p50, p90 and p99 only.

## Why not more nines

A p99.9 from 400 samples is the second-largest value with a costume on.
To mean anything a percentile needs enough samples beyond it: as a rule
of thumb at least 10 samples above the cut, so p99 wants ~1,000 requests
and p99.9 wants ~10,000. Our default 10 s local run has a few hundred.

If someone adds more nines, the report should say how many samples it
used, and the tests should include sample sizes that are not round
numbers. Percentile code that is right for n = 100 and wrong for n = 37
is the classic bug here.

## Failed requests

Percentiles are over successful requests. Failures are counted in
`errors` and broken down by kind. Never drop a failure silently: the
requests that time out are the slowest ones, and dropping them makes the
tail look better exactly when it is worst.
