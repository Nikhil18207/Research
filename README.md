# Who's Home? Adapter-Residency Side Channels in Multi-Tenant LoRA Serving

Research artifact: a timing side channel in vLLM's multi-LoRA adapter cache that lets an
unprivileged co-tenant infer another tenant's activity (and, under a named misconfiguration,
identity and adapter rank) from request latency alone.

**Start here:** [`docs/PAPER_DRAFT.md`](docs/PAPER_DRAFT.md) is the current paper draft and the
source of truth for every claim and number. [`docs/PROJECT.md`](docs/PROJECT.md) is the
chronological research log behind it (dated entries — read as history, not current status).

## Layout

```
harness/            Core attacker/measurement primitives (Prober, GPUMonitor, noise
                     generator, constant-time-padding defense proxy) -- imported by
                     every script under scripts/drivers/ and some of scripts/analysis/.
scripts/
  launch/            Start vLLM (one variant per cache config / base model / batch-
                     invariance setting) or the constant-time proxy / noise generator.
  run/               Drive one experiment against an already-running server; writes
                     raw output to results/. Calls scripts/drivers/ and scripts/setup/.
  drivers/           The actual experiment logic (rq1..rq4, scenario_b, rank sweep,
                     volume sweep, 8-way identification, adaptive/multiprobe variants).
  analysis/          One analyze_*.py per driver/variant: turns a raw CSV/JSON in
                     results/ into the statistics reported in the paper (AUC, bootstrap/
                     Wilson/Hanley-McNeil CIs, Shapiro-Wilk/Mann-Whitney, etc.), plus a
                     few standalone stats/debug utilities (statistical_audit.py,
                     hanley_mcneil_ci.py, debug_poisson.py, check_leak_rate*.py).
  setup/             One-time data/adapter generation: train_adapter.py, med_law_data.py
                     (the Q&A training corpora), make_junk_adapters.py.
  smoke/             Quick manual sanity checks (curl one adapter, compare direct vs.
                     proxied latency) -- not part of the measurement pipeline.
adapters/            Config only (adapter_config.json) for every adapter used in the paper
                     (med, law, rank-sweep and cross-model variants, attacker-controlled
                     "junk" adapters) served by vLLM via --lora-modules. Weight files
                     (adapter_model.safetensors) are NOT tracked -- see the note below.
results/             Raw CSV/JSON output of every experiment run, referenced directly by
                     PAPER_DRAFT.md's tables. This is the actual evidence -- treat it as
                     data, not as regeneratable cache.
docs/                Paper draft and research log.
```

## Reproducing an experiment

1. A script in `scripts/launch/` starts vLLM with the adapter set and cache config a
   given experiment needs (see the script for the exact flags; `docs/PAPER_DRAFT.md`
   §3.1 explains which experiments use which configuration).
2. A script in `scripts/run/` runs the corresponding driver from `scripts/drivers/` (or
   `scripts/setup/` for adapter training) against that server and writes its raw output
   to `results/`.
3. A script in `scripts/analysis/` reads that CSV/JSON and reproduces the statistics
   reported in the paper (AUC, bootstrap/Wilson/Hanley-McNeil CIs, Shapiro-Wilk/Mann-
   Whitney, etc.).

All three layers still assume a `results/`/`adapters/`/`harness/` sibling layout at the
repo root -- every `scripts/run/*.sh` still `cd`s into `scripts/` before invoking its
driver as `../drivers/<name>.py`, so the relative paths inside them resolve correctly
without needing an installed package or a PYTHONPATH change.

Environment notes (WSL2/vLLM-specific gotchas) are documented in `docs/PAPER_DRAFT.md` §3.1
and in `requirements.txt`.

## A note on `adapters/`

Only `adapter_config.json` (rank, target modules, base model) is tracked for each adapter --
the trained/placeholder weight files (`adapter_model.safetensors`, ~440MB total) are not, and
are gitignored. This repo's artifact-availability goal is reproducing the *statistical
analysis* from the CSV/JSON in `results/`, not re-running the GPU experiments -- the paper is
explicit that a reviewer isn't expected to do the latter. To actually re-run an experiment
end-to-end against a live vLLM server, regenerate the weights first via `scripts/setup/`
(`train_adapter.py` for `med`/`law`/rank-sweep/cross-model adapters, `make_junk_adapters.py`
for the untrained eviction-pressure adapters) using the ranks/epochs/base-models documented in
`docs/PAPER_DRAFT.md` §3.1 and each adapter's own `adapter_config.json`.
