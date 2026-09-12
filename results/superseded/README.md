# Superseded results

Files here are raw data whose *conclusion* was later reversed by a larger,
more careful follow-up -- kept for provenance (this project's convention is
to keep and narrate corrections, not delete them), but not the current
evidence for any claim.

## scenario_b_gradient_sweep_*_raw.csv (2026-09-12, n=60/condition)

Pilot graduated-contention sweep for Scenario B (0/2/4/6 competing workers +
a 6-worker queueing-only control). Read as a graded dose-response at the time
(AUC 1.00->0.65->0.55->0.52). **This conclusion did not hold up.**

Superseded by `../scenario_b_gradient_scaled_*_raw.csv` (n=150/condition, plus
three more worker-count points): at proper sample size the signal collapses to
chance immediately at any nonzero contention (a cliff), not gradually. The
pilot's one intermediate point (2 workers, AUC=0.653, CI [0.51,0.79]) barely
excluded 0.5 at n=60 and did not replicate at n=150 (0.409).

The *mechanism* finding from the same pilot (cache-slot competition, not
generic queueing delay -- see the matched-throughput queueing-only control)
was NOT reversed; it replicated and got stronger at n=150. Only the
dose-response *shape* was wrong.

## rq1_defended_raw.csv, rq1_defended_300_raw.csv (n=30 pilots)

Small-scale pilots of the constant-time defense proxy, predating the n=200
runs PAPER_DRAFT.md Table 9 actually reports (`rq1_defended_n200_150_raw.csv`
at T=150, `rq1_tmax300_retest_raw.csv` at T=300). Superseded by scale, not by
being wrong -- kept as the historical v1/early-v2 pilot data the third
critique round's "v1 (flawed) / v2 (fixed)" narrative in PROJECT.md describes.

## rq1_defended_n200_300_raw.csv (n=200, T=300, unstable)

**This one is not just smaller-scale, it is the confirmed-flawed run.** Row
stats (hot mean=355.82ms, std=60.35 -- vs. the clean rerun's hot=301.95ms,
std=0.82) match PROJECT.md's fourth-critique-round description of "a second
n=200 rerun showed even worse, all-states-inflated numbers (hot mean 356ms
vs. expected ~301ms)" -- later root-caused to laptop battery-power throttling
(fifth critique round), not the proxy or WSL2. Superseded by
`../rq1_tmax300_retest_raw.csv`, the clean AC-power re-run PAPER_DRAFT.md
Table 9 actually cites.

## rq1_native_clean_raw.csv (n=30 pilot)

Initial, smaller native-storage filesystem-bridge check (hot=25.89ms,
ram=30.63ms, disk=36.58ms per PROJECT.md's fifth critique round). Superseded
by scale: `../rq1_native_n100_raw.csv` (n=100, "the tighter estimate") is the
one PAPER_DRAFT.md §3.7 actually cites (AUC=0.8667/0.7432/0.7937) -- confirmed
by matching row-stats exactly (hot=29.32ms std=10.59 in the file vs.
"hot=29.32ms(std10.64)" in the text).

## rq1_native_diag_raw.csv (n=100, anomalous)

**Not a valid experimental result -- a diagnostic artifact of the same
power-throttling bug.** Row stats (hot mean=348ms, ram=435ms, disk=502ms) are
wildly inconsistent with every other native-storage RQ1 measurement (all
~25-40ms) and match the exact symptom (all states uniformly inflated, GPU
otherwise cool) that PROJECT.md's fifth critique round root-caused to laptop
battery-power throttling. Kept as a record of that diagnostic process, not as
evidence for any claim -- the valid version is `../rq1_native_n100_raw.csv`.
