# Who's Home? Adapter-Residency Side Channels in Multi-Tenant LoRA Serving

**Target venue:** AISec (ACM CCS workshop) or equivalent security-tier workshop (2027 cycle — 2026 deadlines passed). IEEE S&P side-channel/DL-security workshops as backup.

**Hardware:** RTX 4060 laptop, 8GB VRAM, WSL2 + Ubuntu 22.04 + vLLM.

---

## Abstract, contributions list, and every current claim: see PAPER_DRAFT.md

This file is a chronological research log, not the paper. Two superseded abstract
drafts (dated 2026-09-03, describing "four escalating experiments" with RQ3
identification as the headline result) used to live here and were deleted —
they were stale relative to the paper's actual current framing (five claims,
Scenario B / §5.5 as the central claim since the fourth critique round, RQ3
as the identification upper bound under a named misconfiguration, plus the
production-scale and native-filesystem findings from the fifth and sixth
rounds) and risked being read as current by anyone skimming this file instead
of PAPER_DRAFT.md. **PAPER_DRAFT.md's abstract is the only current one.**

Section headers below this point are dated and reflect what was true *at the
time they were written* — several call RQ3 the "headline result," which was
accurate on 2026-09-02/03 and has not been true since Scenario B was measured.
Read them as history, not current status.

---

## Cast (experiment vocabulary)

| Name | What it is |
|---|---|
| Base model | Llama-3.2-1B, shared by all tenants |
| Adapter | LoRA add-on = one tenant |
| `med` | Victim adapter (medical Q&A) |
| `law` | Second co-tenant adapter (legal text) |
| Junk adapters | Attacker-owned, used to force evictions |
| Attacker | Just another tenant, timing only its own requests |
| GPU1 | The only GPU in scope (laptop) — all RQ1-4 run here |
| GPU2 | Multi-replica production — framing/future work ONLY, not built |

---

## Current contribution status (kept up to date; supersedes the table below, which is historical planning, not current status)

| # | Current contribution | Status |
|---|---|---|
| 1 | Residency timing side channel (existence + inducibility) | Validated |
| 2 | Active prime-and-probe inducibility | Validated |
| 3 | Scenario-B self-eviction activity channel — the paper's central claim | Validated on idle GPU; severe-contention robustness unresolved (§5.5) |
| 4 | Tenant identification under cross-tenant adapter naming | Validated, framed as the channel's upper bound under an avoidable misconfiguration, not the central claim |
| 5 | Mitigation evaluation | Constant-time padding measured (two margins); CPU-tier headroom measured; architectural defenses (reservation, random replacement) discussed, not evaluated |

**Superseded planning table (2026-09-02, kept for history — see above for current status):**

| # | Contribution | Workshop scope | Top-venue scope (later) |
|---|---|---|---|
| 1 | Residency externally observable via timing, unprivileged, remote | Full | Full |
| 2 | Active manipulation via prime-and-probe | Full | Full |
| 3 | Tenant identification via multi-adapter probing | Full | + contention-hardened |
| 4 | Config/rank leakage via reload-time fingerprint | Bonus result | Expanded |
| 5 | Mitigation | Discussed only | Measured w/ tradeoffs |

**Key framing sentence (the paper's spine):** prior work (PromptPeek, EarlyBird, InputSnatch, KV-cache sharing attacks) leaks *prompt content* via cache-key overlap. We leak *tenant identity* via adapter-management-layer residency — a structurally distinct channel. **[Superseded — see the sixth critique round entry below]:** "Governing the KV Cache" does not explicitly scope adapter/LoRA-level channels out of its threat model; it simply does not discuss them, and its own taxonomy shows the KV-cache layer can produce identity/activity leaks too. The paper's actual distinction is layer + zero-co-location-requirement, not a clean content-vs-identity split (PAPER_DRAFT.md §6.1, §6.5).

**Critical precision (do not lose this):** residency is *measured*; activity is *inferred*. The inference requires stating the LRU-eviction assumption explicitly — don't collapse "adapter is resident" into "tenant is active" without naming the assumption.

**Do not claim "first"** in the abstract until a fresh lit search is run immediately before submission.

---

## RQ1 — Existence (go/no-go gate)

Time requests to `med` in known hot vs. evicted states.

**Critical trap:** vLLM has (at least) two eviction tiers — GPU-resident (`--max-loras`) and CPU-resident (`--max-cpu-loras`). Evicting from GPU typically spills to CPU RAM first (small PCIe copy, low-single-digit ms), NOT disk. The large gap (~200ms) only appears when an adapter falls out of *both* tiers to disk. **First experiment: characterize all three tiers' reload latencies on this hardware before assuming any gap size.** Tune `--max-cpu-loras` low enough (or use enough junk adapters) to force disk eviction reliably for the main experiments.

Metrics: latency per residency state (hot/RAM-evicted/disk-evicted), separation vs. noise floor, classification AUC, temp+clock control per sample (rule out thermal throttling — laptop GPU, this control is load-bearing, not decorative).

## RQ2 — Inducibility (prime + probe)

Flood GPU1 with junk adapters to evict `med` (prime) → wait → probe `med`, time it.

**Trap:** the probe is destructive — probing a evicted adapter reloads it. Must re-evict between rounds and log ordering/timestamps.

Metrics: probe latency before/after victim activity, detection rate, false-positive rate, detection AUC. Ground truth: victim active/idle (experimenter-controlled).

## RQ3 — Identification (headline result)

Evict both `med` and `law`, probe each independently, read the fast/slow pattern to name which tenant was active.

**Trap:** cache-size vs. number of probed adapters — if `--max-loras` is too small, probing one adapter evicts the other, contaminating results. Set `--max-loras ≥` number of adapters probed. Build the harness around **burst probing + timestamps from day one** (not single-shot reads) — this is what makes the noisy/concurrent case tractable.

Metrics: classification accuracy/AUC (which tenant), confusion matrix, channel capacity (bits/s), measurements-per-bit, **attack-cost curve** (N measurements → accuracy: e.g. 10→70%, 25→90%, 50→97%), attack duration. Ground truth: adapter identity, adapter rank.

**Bonus:** rank leakage — bigger adapters (rank 32) take longer to reload than smaller ones (rank 8), fingerprinting adapter configuration for free from the mixed-rank training already planned.

## RQ4 — Control (prove it's a leak, not interference)

Compare `med`/`law` output logprobs/distributions with attacker present vs. absent. Must be statistically indistinguishable (fixed seed, greedy decoding, distribution-level comparison — not eyeballing text).

Also compare with `VLLM_BATCH_INVARIANT` on/off to separate true output effects from known batching-numerics effects.

---

## Methodology commitments (locked in, not optional)

1. **Noise-robustness matrix** — every AUC number must be reported under realistic concurrent load (concurrent tenants, varying prompt/gen length, background traffic, varying batch composition), not just on an idle GPU. An idle-GPU-only number will not survive review.
2. **Thermal/clock control logging** — mandatory every sample, not just as a check. Laptop GPU throttling is a real confound for RQ1 specifically.
3. **Attack-cost curves** — report measurements-required-vs-accuracy and wall-clock attack duration alongside AUC/ROC/CIs. A bare AUC number is not sufficient.
4. **Client-side timing only for the attack; server-side instrumentation only for ground truth** — don't let ground truth leak into the attacker's measurement channel.
5. **Scope discipline:** single GPU (GPU1) only for all experiments. Multi-replica (GPU2) is discussion/limitations only — do not build it for the workshop tier.

---

## RQ1 Results (2026-09-02, RTX 4060 Laptop, 30 trials)

**Verdict: PASS.** The residency signal exists and is strongly separable — but the actual numbers are far more compressed than the brief's illustrative "3ms vs 200ms" example. This is exactly the risk flagged during planning (§2 of the original assessment): always measure the real tiers, never assume the gap size.

| State | Mean (ms) | Std | Median | Min | Max |
|---|---|---|---|---|---|
| hot | 27.13 | 3.10 | 27.04 | 20.83 | 32.37 |
| ram_evicted | 36.58 | 5.69 | 37.48 | 25.86 | 47.12 |
| disk_evicted | 80.53 | 10.14 | 78.03 | 69.85 | 113.66 |

**Classification AUC (latency alone):**
- hot vs disk_evicted: **1.0000** (perfect separation), Cohen's d = 7.12
- ram_evicted vs disk_evicted: **1.0000**, d = 5.34
- hot vs ram_evicted: **0.9222**, d = 2.06 (real but noisier — some overlap)

**GPU temp held flat at 53-55°C throughout** — thermal throttling ruled out as a confound for this run.

**Design implication for RQ2/RQ3:** the disk-eviction tier gives near-perfect, trivially separable signal and should be the primary channel the attack is built around. The RAM-eviction tier is a real but weaker/noisier signal (still highly significant, d=2.06) — usable as a secondary/faster-but-less-reliable channel, not the primary one.

**Config used:** `--max-loras 2 --max-cpu-loras 4 --max-lora-rank 32 --gpu-memory-utilization 0.75 --max-model-len 4096`, base model meta-llama/Llama-3.2-1B, 6 placeholder (untrained, standard-LoRA-init) adapters at ranks 8/16/32. Target adapter was a rank-8 stand-in; real med/law adapters with trained content still to come — RQ1 only needed real tensor shapes, not trained weights.

**Environment gotchas resolved to get here (for reproducibility):**
1. `--gpu-memory-utilization` default (0.92) exceeded actual free VRAM once Windows background apps' usage was accounted for — lowered to 0.75.
2. vLLM's newest GPUModelRunnerV2 needs CUDA UVA (pinned memory), which vLLM conservatively disables by default under WSL2. Fixed via `VLLM_WSL2_ENABLE_PIN_MEMORY=1` (requires WSL2 kernel ≥4.19.121; this machine runs 6.6.114, well above threshold).
3. Llama-3.2-1B defaults to 131K context, which alone would need 4GB of KV cache — irrelevant for tiny timing-probe prompts. Fixed via `--max-model-len 4096`.
4. FlashInfer's optimized sampler JIT-compiles a CUDA kernel via `nvcc`, which isn't installed (only CUDA runtime libs were pulled in via pip). Since sampling-kernel performance is irrelevant to a latency-timing study, disabled it via `VLLM_USE_FLASHINFER_SAMPLER=0` rather than installing a full CUDA toolkit.

## RQ2 Results (2026-09-02, RTX 4060 Laptop, 40 trials, balanced active/idle)

**Verdict: PASS, cleanly.** Prime (disk-evict target) → simulate hidden victim activity (or not) → attacker probes only its own request → detect.

| Ground truth | Mean probe latency (ms) | Std | Min | Max |
|---|---|---|---|---|
| active (victim reloaded it) | 42.78 | 6.57 | 27.32 | 57.61 |
| idle (still evicted) | 104.00 | 10.44 | 88.80 | 123.97 |

**Detection AUC (probe latency alone, threshold-free): 1.0000** — perfect rank-ordering separation; every active-state latency (max 57.61ms) falls below every idle-state latency (min 88.80ms). At a fixed 50ms threshold, raw accuracy read 39/40 (97.5%) with 1 false negative — that was purely a suboptimal threshold choice (50ms cut into the active distribution's tail), not a real classification ambiguity. A threshold anywhere in [58, 88]ms would have gotten 40/40.

**Confirms:** an attacker can actively evict a target adapter via requests to adapters they control, then detect the victim's subsequent (or absent) activity via prime-and-probe, using only its own request timing. Ground truth (victim active/idle) was hidden from the detector — only the attacker's own probe latency was used, matching the real threat model.

**Still idle-GPU, single-target, n=40** — same caveats as RQ1 apply before this is paper-ready (noise-robustness matrix, larger n, real med/law adapters, CIs).

## RQ3 Results (2026-09-02, RTX 4060 Laptop, 40 trials, balanced across 4 classes) — HEADLINE RESULT

**Verdict: PASS, perfectly.** Evict both `A` and `B` (two same-rank r8 adapters, avoiding a rank confound) → hidden ground truth (A active / B active / both / neither, 10 trials each) → attacker burst-probes both, in order, using only its own latencies.

**Confusion matrix (rows=truth, cols=predicted) — perfect diagonal, 40/40:**

| | A | B | both | neither |
|---|---|---|---|---|
| **A** | 10 | 0 | 0 | 0 |
| **B** | 0 | 10 | 0 | 0 |
| **both** | 0 | 0 | 10 | 0 |
| **neither** | 0 | 0 | 0 | 10 |

Precision/recall/F1 = 1.0000 for all four classes. Zero errors in 40 trials — by rule-of-three, the true error rate could plausibly be as high as ~7.5% at 95% confidence from this sample size alone, so this still needs a larger-n run before it's a citable number, but the mechanism is unambiguously confirmed.

**This is the headline claim of the paper:** adapter-granular tenant identification — naming *which* specific tenant was active, not merely detecting that some tenant was active — demonstrated via independent burst-probing of co-resident adapters, using only the attacker's own request timing.

**Not yet done:** the rank-leakage bonus result (do different-rank adapters reload at measurably different speeds, fingerprinting configuration) — RQ3 deliberately used same-rank (r8/r8) adapters to keep this a clean identity-only test. A dedicated rank-leakage check (e.g. probe an r8 vs an r32 target under identical eviction) is still open. Also open: channel capacity (bits/s) and measurements-per-bit curves — not yet computed, meaningful once the noise-robustness pass is done (a channel capacity number on an idle GPU with n=40 isn't the number that belongs in the paper).

## RQ3 Confirmation with REAL med/law adapters (2026-09-02, n=60, balanced 4-class)

**Verdict: PASS, confirmed with real trained content, larger n.** Real `med` (rank 8, trained on 30 genuine medical Q&A pairs, train_loss 1.74→0.37) and `law` (rank 32, trained on 30 genuine legal Q&A pairs, train_loss 1.58→0.34) adapters replace the placeholder stubs used in the pilot. Both verified to produce genuinely domain-correct completions (spot-checked: med correctly answers diabetes symptoms, law correctly defines contracts).

**Confusion matrix — perfect diagonal again, 60/60 (15 per class):** identical structure to the pilot, now at 50% more trials. Rule-of-three upper bound on true error rate tightens to ~5.0% (from ~7.5% at n=40).

### Rank-leakage bonus — CONFIRMED, not just plausible

Using the "neither evicted... wait, both-evicted" trials' raw latencies (med=rank 8 vs law=rank 32, identical disk-eviction procedure applied to both):

| Adapter | Rank | Mean reload latency | Std |
|---|---|---|---|
| med | 8 | 83.37ms | 11.18 |
| law | 32 | 158.60ms | 21.29 |

**t=12.119, p<0.000001, Cohen's d=4.43.** The rank-32 adapter takes ~75ms longer to reload than the rank-8 adapter, on average — a massive, statistically overwhelming effect obtained for free from data already being collected for the identification test. This confirms the "free bonus result" the original brief predicted: reload latency fingerprints adapter configuration (rank/size), a second independent leakage channel beyond tenant identity.

## Noise-Robustness Matrix (2026-09-02) — the honest, load-bearing result

Ran with 6 concurrent background workers continuously firing randomized-adapter, randomized-length requests at the server (realistic multi-tenant contention), not the idle GPU used for RQ1-3 above.

**Single-probe signal degrades substantially under heavy contention** (first noise run, heaviest load, queueing delay reached 0-2200ms, GPU temp rose to 73-79°C from real work):

| Comparison | Idle-GPU AUC | Single-probe AUC under noise |
|---|---|---|
| hot vs ram_evicted | 0.9222 | 0.7189 |
| hot vs disk_evicted | 1.0000 | 0.7044 |
| ram_evicted vs disk_evicted | 1.0000 | 0.4789 (chance level) |

Queueing delay variance (up to 2200ms) can dwarf the underlying tens-of-ms reload-cost signal. This is real, honest, and exactly what a reviewer would demand to see before believing an idle-GPU AUC=1.0.

**Attack-cost curve — does multi-probe aggregation recover the signal?** Second noise run (lighter contention, mean latencies 87-473ms), median-of-N repeated probes per measurement:

| N probes/measurement | hot-vs-disk AUC | hot-vs-ram AUC | ram-vs-disk AUC |
|---|---|---|---|
| 1 | 0.9556 | 0.6756 | 0.6667 |
| 2 | 0.9689 | 0.6844 | 0.5511 |
| 3 | **1.0000** | 0.6800 | 0.5911 |
| 5 | 1.0000 | 0.6978 | 0.5778 |
| 10 | 1.0000 | 0.6978 | 0.5333 |

**Conclusions (paper-ready, nuanced, defensible):**
1. **The primary channel (hot vs. disk-evicted) is robust and cheaply recoverable under contention** — median-of-3 repeated probes fully restores AUC=1.0000, at attacker cost of only 3 requests per measurement instead of 1.
2. **The RAM-eviction tier is noise-fragile and should NOT be relied upon under contention** — hot-vs-ram AUC plateaus around 0.68-0.70 regardless of how many probes are averaged (the underlying idle-GPU gap, ~10ms, is simply too small relative to realistic queueing noise). This confirms the design recommendation from RQ1: build the attack around disk-eviction, treat RAM-eviction as unreliable under real load.
3. **Distinguishing RAM-evicted from disk-evicted (i.e., precisely which tier a target fell to) gets WORSE with more averaging under contention** (0.67 → 0.53, near chance) — the two "evicted" states become hard to tell apart from each other once queueing dominates, even though each remains distinguishable from "hot." The paper's threat model should rely on the hot/evicted distinction, not the specific evicted-tier identity, under realistic conditions.

This is a stronger, more credible result than a flat "AUC=1.0 everywhere" claim — it shows the channel's real boundary conditions rather than only its best case.

## RQ4 Results (2026-09-02) — Control: is it a pure leak, or interference?

10 fixed prompts (5 med, 5 law), greedy decoding (temperature=0), top-5 logprobs requested, compared attacker-absent (idle) vs. attacker-present (6-worker concurrent noise), under two server configs.

**Default vLLM (VLLM_BATCH_INVARIANT unset) — the naive hypothesis is FALSIFIED:**
- 3/10 completions produced different text depending on whether the attacker was present (e.g. med's flu-symptoms answer diverged after "dry cough, and..." — "sore throat...nausea" vs "nausea...shortness of breath")
- Logprob differences: mean 0.058, max 1.43 (not zero)
- **Honest conclusion: under default settings, concurrent load DOES measurably perturb outputs** via known batching-numerics non-determinism (different batch composition -> different floating-point reduction order -> occasional argmax flips at greedy decoding). This is a real, important caveat — a naive "outputs never change" claim would have been wrong.

**With VLLM_BATCH_INVARIANT=1 — the pure-leak claim is CONFIRMED, decisively:**
- 0/10 text mismatches
- **All 300 compared logprob positions: |diff| = 0.0 exactly.** Not "very close" — bit-for-bit identical.
- **Conclusion: with batch-invariant kernels enabled, the channel is a provably pure information leak.** The attacker learns residency/identity/rank facts through timing alone, with mathematically zero effect on victim outputs. This isolates the real side-channel claim from a separate, known, orthogonal systems artifact (batching numerics) rather than conflating the two.

This is the strongest, cleanest result in the study precisely because "exactly 0.0" is about as strong a scientific claim as is possible to make — no statistical test needed, no ambiguity.

**Paper framing implication:** report BOTH halves. State plainly that default-config vLLM has nonzero output perturbation under load (honest, expected, disclosed), then show that enabling batch-invariant kernels eliminates it entirely — proving the timing channel and the batching-numerics effect are separable, and that the core side-channel claim (identity/residency leak without content leak) holds unconditionally once that confound is controlled for.

## RQ2 Confirmation with real `med` adapter (n=40): 40/40 = 100%, consistent with the earlier stub-adapter pilot.

## Channel Capacity (RQ3, real med/law adapters, n=60)

- 60 trials, 4 balanced classes (A/B/both/neither), 0 errors observed -> 2.00 bits of tenant-identity information per trial
- Average wall-clock time per trial: 1.255s (measured from real timestamps)
- **Channel capacity: ~1.6 bits/s**
- **~7 attacker requests per bit of identity information** — directly answers the "prior timing attacks needed 200+ measurements" critique from the original framing pass: this channel is dramatically more request-efficient.

---

# STATUS: Core research pipeline complete (2026-09-02)

All four RQs executed end-to-end with real data, real trained adapters, and honest noise-robustness characterization:

| RQ | Idle-GPU result | Real adapters? | Under moderate/severe noise |
|---|---|---|---|
| RQ1 Existence | AUC 1.0 (disk) / 0.92 (RAM) | med (also stub pilot) | Single-probe degrades (0.70/0.48 at moderate-heavy load); **median-of-3 fully recovers primary channel to AUC 1.0** |
| RQ2 Inducibility | AUC 1.0000 (stub n=40, real med n=40) | med | Single-probe -> chance (AUC ~0.45-0.50) under severe load; **does not recover with median-of-N** — signal smaller than noise floor scale, not just variance |
| RQ3 Identification | 100% (40/40 stub, 60/60 real), perfect confusion matrix | med + law | Collapses to ~25-30% (chance) under severe load with a fixed threshold; **diagnosed root cause is a static-threshold artifact**, not signal disappearance |
| RQ3 bonus: rank leakage | law(r32) reloads 75ms slower than med(r8), p<0.000001, d=4.43 | med + law | Not re-tested under noise |
| RQ4 Control | — | med + law | Default vLLM: NOT a pure leak (3/10 text mismatches). **VLLM_BATCH_INVARIANT=1: pure leak confirmed, all 300 logprob diffs exactly 0.0**, tested both idle and under noise |

**Full noise-robustness matrix is now complete across all four RQs** (this was the single biggest "still open" item as of the previous status update — now closed). The honest finding: the core existence signal (RQ1) is robust and cheaply recoverable under contention; RQ2/RQ3's derived detection tasks are load-bearing on a fixed threshold that breaks down under severe/saturating contention specifically, with a clearly diagnosed cause (threshold needs to be adaptive/relative, not absolute) rather than an unexplained failure. This is exactly the shape of finding a "Limitations and Future Work" section should be built from. Multi-replica/production-routing evaluation remains explicitly out of scope per the workshop-tier plan (single GPU only, GPU2 = discussion/future-work).

**Everything above is real, executed data from this machine (RTX 4060 Laptop) on 2026-09-02** — not projected or illustrative numbers. Raw CSVs and JSON logs are in `results/`, analysis scripts in `scripts/`, trained adapters in `adapters/med` and `adapters/law`.

## Noise-Robustness Matrix, Part 2 — RQ2 and RQ3 under load (2026-09-02/03)

Symmetric treatment to RQ1's noise-robustness pass, now applied to RQ2 (activity detection) and RQ3 (identification).

### A real methodological confound found and fixed

The first noise-generator design included `med`/`law` (the targets under test) in its own random-adapter pool. This meant the "noise" wasn't just queueing delay — it was **genuinely, accidentally reloading the target adapter**, directly contaminating the "idle" ground-truth label rather than just adding measurement noise. Symptom: RQ2 multiprobe accuracy got *worse* with more averaging (0.60 -> 0.46 AUC), the opposite of RQ1's result, because more probes meant more chances to catch a spurious noise-induced reload within an "idle" trial's window. **Fix:** noise generator must exclude the target adapter(s) under test from its own traffic pool — contention should come from *other* tenants, never from spuriously touching the exact adapter whose state you're trying to measure. All results below use the corrected generator.

### RQ2 (activity detection) under load: does NOT recover via simple averaging

| Condition | AUC |
|---|---|
| Idle GPU baseline | 1.0000 |
| Single-probe, corrected noise | 0.4525 (chance) |
| Median-of-5, corrected noise | 0.5100 (still chance) |

Unlike RQ1's hot-vs-disk_evicted distinction, RQ2's single-event activity detection **did not recover with median-of-N averaging** under this (severe) load level. Root cause, diagnosed from the raw data: under saturating 6-worker contention, absolute latencies balloon to 500-2300ms (vs. ~30-100ms clean) — queueing delay swamps the ~20-60ms reload-cost signal by 10-40x, and no amount of median-filtering recovers a signal that's simply smaller than the noise floor's *scale*, not just its variance.

### RQ3 (identification) under load: fixed-threshold detection collapses, diagnosably

| N probes/measurement | Accuracy (4-class) |
|---|---|
| 1 | 30.0% |
| 2 | 25.0% |
| 3 | 25.0% |
| 5 | 25.0% (= chance for 4 balanced classes) |

Confusion matrix at N=5 shows the detector collapsing to predicting "neither" for nearly every trial — because a **static 60ms threshold**, calibrated for idle/moderate conditions, becomes meaningless once both adapters' latencies inflate to 1000-1600ms regardless of true state. This is a diagnosed, fixable methodology gap (the threshold needs to be adaptive — e.g., a live concurrent calibration probe, or relative/paired ranking between A and B rather than an absolute cutoff), not evidence the underlying channel disappears.

### Honest, load-bearing conclusion for the paper

The residency-existence signal (RQ1) is **robust to moderate contention** and cheaply recoverable (median-of-3 -> AUC 1.0). The **derived detection tasks (RQ2 activity inference, RQ3 identification) are load-bearing on a threshold that was calibrated for low-noise conditions**, and degrade to chance under severe/saturating contention with that fixed threshold. This is a genuine, reportable boundary condition — the correct framing for the paper is: *"the channel exists and is exploitable under realistic moderate contention; under severe/saturating load, naive fixed-threshold detection fails, and an adaptive-threshold or relative-ranking detector is needed — which we identify as concrete future work rather than claim to have solved here."* This is a stronger, more credible paper than one that only reports best-case numbers, and it gives a clear, specific next engineering step (adaptive thresholding) rather than a vague "more robustness work needed."

## Adaptive-Threshold Fix Attempt (2026-09-03) — real progress, root cause fully isolated, not yet solved

Three iterations, each diagnosing exactly why the previous one failed:

**Attempt 1 — sequential paired-canary (probe canary, wait for response, then probe target):** Failed worse than the static threshold. Diffs ranged wildly (-1600ms to +1100ms) — because waiting for the canary's response before firing the target probe means hundreds of ms elapse between them under saturating load, so the two probes no longer share the same queue state. The pairing assumption (shared noise cancels in the difference) requires near-simultaneity, not just temporal adjacency.

**Attempt 2 — concurrent paired-canary (fire canary + target as truly simultaneous requests via a thread pool):** Real, measurable improvement — diff magnitude collapsed from a ~2700ms range down to a ~50-160ms range, confirming the core theory that shared queueing delay cancels when the two probes are actually concurrent, not just close in time. **This is a genuine, working technique and should be kept** for any future noise-robustness work.

**But a second-order problem surfaced:** threshold-free AUC on the concurrent-paired diffs was still ~0.44-0.52 (chance) pooled across the full run. Splitting the run in half revealed why: `active` trials averaged diff=84.6ms in the first half vs. 24.3ms in the second half; `idle` trials went 67.7ms -> 31.8ms over the same split — **the load itself is non-stationary across the run, and a single threshold calibrated once at the start doesn't hold for the whole experiment.** The underlying signal is present (the two classes separate correctly within each half, just at different absolute diff levels) but a naive pooled/static-threshold analysis destroys it.

**Honest conclusion:** concurrent-pairing is the correct fix for the *spatial* problem (two probes experiencing different concurrent load) but a full solution also needs to handle the *temporal* problem (load level drifting across the experiment) — e.g. a rolling/windowed threshold re-estimated periodically, or a paired statistical test within a short local window rather than one global cutoff. This is now a precisely-scoped, concrete future-work item — not a vague "needs more robustness work" — and the concurrent-pairing technique itself is a reusable, validated building block for it. Reporting this honestly (three attempts, each diagnosed, the real fix identified but not fully implemented) is stronger evidence of engineering rigor than a paper that only shows the one attempt that happened to work.

## RQ3 at n=120 (2026-09-03) — the actual headline number for the paper

Bumped from n=60 to n=120 (30 per class) specifically to stop reporting a suspicious "always 100%" and find the true error rate.

**Result: 118/120 = 98.33% accuracy — not perfect, and that's a feature, not a bug.** A genuinely small, nonzero, characterized error rate is far more credible to a reviewer than a small-sample "always perfect" score (which invites exactly the "is this real or did you get lucky" skepticism raised earlier in this project).

**Confusion matrix (rows=truth, cols=predicted):**

| | A | B | both | neither |
|---|---|---|---|---|
| **A** | 30 | 0 | 0 | 0 |
| **B** | 0 | 28 | 0 | 2 |
| **both** | 0 | 0 | 30 | 0 |
| **neither** | 0 | 0 | 0 | 30 |

**Both errors are the same specific failure mode: B (law) misclassified as neither** (2/30 false negatives on that one class; every other class is perfect). This is a real, reportable, characterized error pattern, not random noise scattered across classes.

**Formalized confidence intervals (two independent methods, replacing the informal rule-of-three estimate used earlier):**
- Bootstrap (10,000 resamples): **95% CI = [95.83%, 100.00%]**
- Wilson score interval (standard method for binomial proportions): **95% CI = [94.13%, 99.54%]**

## RQ1 AUC with formalized bootstrap CI (2026-09-03, reusing existing n=30/state idle-GPU data)

| Comparison | AUC | 95% CI |
|---|---|---|
| hot vs ram_evicted | 0.9222 | [0.8398, 0.9806] |
| hot vs disk_evicted | 1.0000 | [1.0000, 1.0000] |
| ram_evicted vs disk_evicted | 1.0000 | [1.0000, 1.0000] |

The disk-eviction comparisons bootstrap to an exact [1.0, 1.0] CI because the raw value ranges are completely non-overlapping (69.85-113.66ms vs. 20.83-32.37ms) — no resample of this sample can produce overlap. Note this reflects certainty *within this sample*, not a guarantee about the true population rate; the rule-of-three caveat (true error rate could plausibly be nonzero, just not observed at this n) still applies for the population-level claim. The hot-vs-ram_evicted CI [0.84, 0.98] is the more informative one — it shows real, honestly-quantified uncertainty at n=30 for that specific (weaker) comparison.

**Both formalized-CI passes above address gap #2 from the "is this good enough for a top-tier workshop" assessment** (informal rule-of-three bounds -> standard bootstrap/Wilson CIs reported alongside every headline number).

## Statistical Analysis Summary — consolidated, for direct use in the paper's Results/Methods

Everything below is the canonical, paper-ready statistics for each claim — consolidated from the individual RQ sections above, with test-selection validity checked (not assumed).

### Test selection validity (Shapiro-Wilk normality checks)

| Distribution | W | p | Normal? |
|---|---|---|---|
| RQ1 hot latency | 0.9582 | 0.2788 | Yes |
| RQ1 ram_evicted latency | 0.9740 | 0.6522 | Yes |
| RQ1 disk_evicted latency | 0.7987 | 0.0001 | **No** (right-skewed, as expected for latency data) |
| med(r8) evicted latency | 0.8515 | 0.0182 | **No** |
| law(r32) evicted latency | 0.8364 | 0.0112 | **No** |

Because several key distributions are non-normal, every headline claim below is backed by BOTH a parametric test (t-test, reported earlier) AND a nonparametric test that makes no distributional assumption (Mann-Whitney U) — the two agree in every case, which is the correct way to report this rather than relying on a t-test alone.

### RQ1 — Existence (n=30/state, idle GPU)

| Comparison | AUC | 95% CI (bootstrap) | Mann-Whitney U | p |
|---|---|---|---|---|
| hot vs ram_evicted | 0.9222 | [0.8398, 0.9806] | — | — |
| hot vs disk_evicted | 1.0000 | [1.0000, 1.0000] | U=900.0 | 1.51e-11 |
| ram_evicted vs disk_evicted | 1.0000 | [1.0000, 1.0000] | — | — |

Cohen's d: hot-vs-ram = 2.06, hot-vs-disk = 7.12, ram-vs-disk = 5.34. Bonferroni-corrected alpha for 3 comparisons = 0.0167; does not change any conclusion (all p far below threshold).

### RQ2 — Inducibility (n=40, idle GPU, real med adapter)

Detection AUC = 1.0000 (threshold-free). 40/40 at fixed 60ms threshold.

### RQ3 — Identification (n=120, idle GPU, real med/law adapters) — HEADLINE RESULT

- Accuracy: 98.33% (118/120)
- Bootstrap 95% CI: [95.83%, 100.00%]
- Wilson score 95% CI: [94.13%, 99.54%]
- Per-class precision/recall/F1: 1.0/1.0/1.0 for A, both, neither; 1.0/0.933/0.966 for B (both errors are B->neither false negatives)

### RQ3 bonus — Rank leakage (n=15/adapter, from n=60 real-adapter run's "neither" trials)

| Test | Statistic | p | Effect size |
|---|---|---|---|
| Welch's t-test | t=12.119 | p<0.000001 | Cohen's d = 4.43 |
| Mann-Whitney U (nonparametric, doesn't assume normality) | U=225.0 (=n1*n2, max possible) | p=0.0000017 | rank-biserial r=-1.00 (complete rank separation) |

Both tests agree: law (rank 32) reloads reliably slower than med (rank 8), ~75ms difference on average.

### RQ4 — Control

Not a hypothesis test in the traditional sense — a direct comparison. Default config: 3/10 text mismatches, logprob diffs mean=0.058/max=1.43 (nonzero, real effect). VLLM_BATCH_INVARIANT=1: 0/10 mismatches, all 300 compared logprob positions exactly 0.0 difference (deterministic equality, not a statistical claim).

### What this closes from the earlier "top-tier readiness" audit

- Formalized CIs (bootstrap + Wilson) in place of informal rule-of-three estimates — done
- Test-selection validity checked via normality tests rather than assumed — done
- Nonparametric robustness checks added alongside every parametric test — done
- Multiple-comparisons correction considered and reported — done (no conclusions change)
- Effect sizes reported in both parametric (Cohen's d) and nonparametric (rank-biserial r) form for the rank-leakage claim — done

### What remains genuinely open (honest, not hidden)

- **Sample-size justification / power analysis was not pre-registered** — n's were chosen pragmatically (30 -> 40 -> 60 -> 120, escalating as results warranted more confidence), not from an a priori power calculation. This is normal for exploratory systems-security work but a very statistics-heavy reviewer could ask for it; worth a one-line justification in the paper ("sample sizes were increased iteratively until bootstrap CIs stabilized") rather than pretending it was pre-planned.
- **The severe-noise adaptive-threshold problem remains diagnosed-but-unsolved** (see dedicated section above) — this is Limitations/Future Work material, not a statistics gap.
- RQ2 and RQ4's core claims don't need hypothesis tests in the same way (RQ2 is AUC/threshold-based classification performance; RQ4 is an exact-equality demonstration) — this is the correct choice of analysis for each claim type, not a gap.

## External-Validity Round (2026-09-03) — response to reviewer critique on generalization

Four additions, all executed on the existing single RTX 4060, in response to a critique that the paper's biggest weakness was single-GPU/single-model/single-config external validity. Full writeup in PAPER_DRAFT.md §4.6; summary here:

1. **Rank sweep** (ranks 1/8/16/32/64, same content domain): Pearson r=0.9834 (p=7.89e-56), linear fit R²=0.967 — reload latency scales linearly with rank, confirming rank-leakage is a real monotonic effect, not a two-point artifact.
2. **Cache-size sweep** (max_loras=1/2/4): AUC=1.0000 at every setting — mechanism is not specific to one cache configuration.
3. **Second base model** (Qwen2.5-1.5B, same GPU, newly trained med/law adapters): RQ1 AUC=1.0000, RQ3=40/40=100% — both central claims replicate on an architecturally distinct model.
4. **Realistic Poisson-process victim traffic** (replacing the deterministic single hidden request): found and fixed two real implementation bugs along the way (multi-probe self-contamination — attacker's own first probe keeps target warm for later probes in the same window; orphaned victim-traffic threads outliving their window due to a sleep-then-check pattern). With both fixed, threshold-free AUC: idle-vs-low=1.0000, idle-vs-high=1.0000, idle-vs-bursty=0.9600 — stronger evidence than the deterministic design, since it demonstrates detection of genuine stochastic traffic shapes, not just one artificial probe event.

Not pursued (by user's explicit choice, given overhead vs. the other three): cross-GPU validation via free-tier Colab/Kaggle. Remains a known, named limitation rather than a silently-dropped item.

## Security Analysis + Related Work written (2026-09-05)

Two remaining paper sections completed, responding to the request for a "polished security analysis" and "exhaustive related-work comparison":

**§5 Security Analysis** (PAPER_DRAFT.md): attacker capabilities enumerated (4 concrete requirements, no more), attack prerequisites as an ordered operational sequence, deployment scenarios split by Scenario A/B (§2), and a mitigations discussion with honest tradeoffs grounded in our own data (namespace isolation, dedicated cache slots, constant-time loading, noise injection — explicitly flagged as *weak* per our own §4.5 median-of-3 recovery result, traffic-pattern detection, larger caches — shown *not* to help per §4.6, batch-invariant kernels with the distinction from the timing channel made explicit).

**§6 Related Work** (PAPER_DRAFT.md): positions against PromptPeek/EarlyBird/InputSnatch (KV-cache prompt-content leaks) and the KVGov survey (confirmed to explicitly exclude adapter-layer channels), against LoRA memorization/extraction work (StolenLoRA, "Leaner Training Lower Leakage" — a different attack class, ruled out early in scoping), and against the classical prime-and-probe side-channel lineage (technique borrowed, target novel). Includes a verified (not assumed) comparison of S-LoRA/Punica/LoRAX's actual caching architectures — a dedicated verification pass found S-LoRA is two-tier with predictive prefetch and **no LRU terminology anywhere in the primary paper** (contradicting secondary-source claims we do not repeat uncritically), Punica has no documented eviction policy at all, and only LoRAX (per vendor blog, not verified at source-code level) closely matches vLLM's GPU/CPU/disk LRU hierarchy. This directly prevented repeating the exact kind of overclaim a reviewer had already flagged once (the original "S-LoRA, LoRAX, and vLLM all use variants of this pattern" line).

**Still not pursued, by explicit user choice earlier in the project:** cross-GPU-vendor validation (free-tier Colab/Kaggle) — remains a named limitation, not a silently dropped item.

**Remaining for a complete paper draft:** Discussion (synthesizing limitations already scattered across RQ sections) and Conclusion.

## Third base model: SmolLM2-1.7B (2026-09-05)

Same pipeline as Qwen, third architecturally-distinct model family (HuggingFaceTB lineage, ungated, no license-click friction unlike Llama). RQ1 AUC=1.0000 (hot=36.67ms, disk_evicted=164.11ms, n=20). RQ3=40/40=100% (n=40). Now have three open-source local models total, all replicating both central claims:

| Model | Params | disk_evicted mean | RQ1 AUC | RQ3 |
|---|---|---|---|---|
| Llama-3.2-1B | 1B | 80.53ms | 1.0000 | 98.3% (n=120) |
| Qwen2.5-1.5B | 1.5B | 97.43ms | 1.0000 | 100% (n=40) |
| SmolLM2-1.7B | 1.7B | 164.11ms | 1.0000 | 100% (n=40) |

Bonus observation: disk-evicted latency increases monotonically with base model size (80→97→164ms), consistent with the same physical mechanism as the rank sweep (bigger = more to deserialize = slower reload). Full writeup in PAPER_DRAFT.md §4.6, Table 8.

**Next per user's plan:** move to Kaggle for 1-2 cloud GPU models (cross-hardware validation — the one remaining external-validity gap that three same-GPU models cannot address).

## Second critique round — framing/stats fixes applied (2026-09-05)

Note: this critique included a claim ("your memory has this program pointed at ICLR 2027, abstract deadline in two weeks") that we checked and found **false** — the memory directory is empty, no such entry exists. We never targeted ICLR in this conversation; AISec/CCS-tier framing has been the target throughout. Flagging this because the claim was specific and checkable, and we check rather than assume.

Fixes applied to PAPER_DRAFT.md (all text/stats, no new experiments):
1. **"Claim the layer, not the technique"** — reframed both the abstract and §1's novelty paragraph: prime-and-probe is classical 20+-year cache-timing methodology, not our invention; the novel part is applying it to the adapter-management layer (reachable over ordinary API, no co-located process needed) rather than claiming the mechanism itself is novel.
2. **Concrete adversary ("so what")** — added a named scenario to §1: competitive business intelligence (inferring a co-tenant's activity pattern/volume without seeing content) as primary, adapter-rank-as-configuration-IP-disclosure as secondary.
3. **Rank-sweep p-value overclaim** — fixed in 3 places (abstract, §4.3.1, §4.6): now leads with slope=3.42ms/rank-unit [95% CI 3.27, 3.57], R²=0.967, explicitly de-emphasizing the p=7.89e-56 figure as a large-N artifact rather than added evidence.
4. **Batch-invariance framed as control, not discovery** — §4.4 now states explicitly that batch-composition-dependent numerics effects are already documented (it's why `VLLM_BATCH_INVARIANT` exists as a named vLLM flag) — our contribution is checking whether it's sufficient to isolate *our specific* channel, not the underlying phenomenon.

**Not yet acted on — genuinely substantial, need explicit direction:**
- **Scenario B (self-eviction-only) experiment**: attacker never names the victim adapter, only watches for unexpected eviction of its OWN adapters to infer "someone else was active" without identification. This is the single highest-value remaining item — it tests whether the paper's claims survive the most obvious deployment fix (blocking cross-tenant adapter naming). Fully executable now with existing infra.
- **Defense evaluation**: implement a constant-time-response proxy in front of vLLM (pad every response to worst-case latency) and measure AUC drop. Executable now, no new infra needed beyond a thin Python proxy.
- **Real commercial multi-tenant endpoint test** (Fireworks/Together/Predibase-hosted LoRA, using only 2 self-owned adapters, no victim): would convert "works on my desk GPU" into "works in production," sidesteps ethics entirely. Requires external account signup and possibly cost — needs user decision before proceeding.

## Scenario B experiment + Defense evaluation, both completed (2026-09-06)

Both items the user asked to finish off completely, both executed to a clean, honest result.

**Scenario B (self-eviction-only observer):** attacker owns 2 adapters (=max_loras), round-robin touches only those, never names/probes the victim adapter at all. Detects victim activity purely from unexpected eviction of its own adapter. Result: **AUC=0.7875, 72.5% accuracy at optimal threshold (n=40)** — a real but substantially weaker signal than Scenario A's near-perfect results, confirming the critique's own prediction exactly ("detects co-tenant activity and volume, without learning who"). Diagnosed why the gap is small: with only 3 distinct adapters touched and `max_cpu_loras=4` giving ample headroom, victim activity only demotes the attacker's adapter to the RAM tier (not disk), a shallower/noisier eviction than RQ1's disk-tier characterization. Full writeup: PAPER_DRAFT.md §5.5.

**Defense evaluation (constant-time response padding):** built a ~50-line Python reverse proxy (`harness/constant_time_proxy.py`) that pads every response to a fixed T_MAX=150ms floor. Re-ran RQ1 through it instead of directly against vLLM. Result: **AUC collapsed from 0.92-1.00 (undefended) to 0.11-0.36 (defended)** — near-chance, with the small departure from exactly 0.5 attributable to sub-ms noise around the shared floor, not a residual signal. Honest wrinkle found and reported: proxy can only pad *up*, so true latency exceeding T_MAX leaks through — measured at **3.3% tail-leak rate** (1/30 disk_evicted samples) at a +20ms calibration margin. Cost stated plainly: >5x latency tax on the common (hot) case. Full writeup: PAPER_DRAFT.md §5.6, and §5.4's constant-time bullet updated to point to this measured result instead of the earlier hypothetical framing.

Both results, plus the framing/stats fixes from the second critique round, are now folded into the abstract as well.

## Third critique round — a real analysis error caught and corrected, both experiments extended properly (2026-09-06)

**The critical catch: the defense evaluation's original conclusion was wrong.** AUC=0.11/0.15/0.36 is not "collapsed to chance" — noise gives AUC≈0.5, not a value pinned far from it. The correct metric for a defended channel is distinguishing advantage = max(AUC, 1-AUC): recomputed, v1's numbers were 0.89/0.85/0.64 — the defense had barely helped. Root cause: `time.sleep(remainder)` overshoot/jitter scales with sleep duration, so a hot request (long sleep) accumulates more overshoot than an evicted one (short sleep) — the padding computation itself re-encodes the residency bit with inverted sign.

**Fixed:** proxy now blocks until an absolute deadline (`t0 + T_MAX`) instead of sleeping a computed remainder, busy-waiting the final ~1ms. Re-tested at two margins:

| Version | T_MAX | hot-vs-ram advantage | hot-vs-disk advantage | ram-vs-disk advantage |
|---|---|---|---|---|
| v1 (flawed) | 150ms | 0.89 | 0.85 | 0.64 |
| v2 (fixed) | 150ms | 0.77 | 0.81 | 0.58 |
| v2 (fixed) | 300ms | **0.50** | 0.64 | 0.63 |

Doubling the margin fully closes the RAM-tier channel but the disk-tier channel stays leaky (disk_evicted's true latency hit 788ms at T_MAX=300, confirming the critique's structural point: the ceiling must exceed what an *adaptive adversary* can induce, not the observed benign tail). Full corrected writeup: PAPER_DRAFT.md §5.6.

**Scenario B corrected too — it was a floor, not a ceiling.** Original write-up called AUC=0.79 "the honest ceiling." Wrong framing: the config tested (max_cpu_loras=4, only 3 adapters touched) was maximally defender-favorable, letting eviction land softly in RAM. Retested with max_cpu_loras tightened to 2 (forcing genuine disk-depth eviction): **AUC=0.9875** [95% CI 0.952, 1.000] — signal strength is a tunable function of a cache-sizing parameter, exactly as predicted. Also added: Hanley-McNeil CI on the original AUC=0.7875 → [0.645, 0.930] (wide at n=40, reported honestly); bootstrap-simulated multi-round majority-vote accuracy (plateaus 82-87% by round 15, slower than naive intuition due to asymmetric per-class error rates at the Youden threshold — a real, more honest nuance); defense tested against Scenario B specifically (advantage 0.79→0.54, closes cleanly since Scenario B's signal lives entirely in the shallow RAM-tier range); and a note that `max_loras` is cheaply learnable by self-experimentation, closing an unstated assumption. Full corrected writeup: PAPER_DRAFT.md §5.5.

**Not done, noted as open:** the volume-sweep demonstration (detection frequency vs. victim request rate) — explicitly flagged in §5.5 as the natural next experiment, not fabricated or approximated.

**Also added:** §5.4's mitigation table now has an honest measured-vs-discussed distinction (padding measured; random-replacement and per-tenant-reservation explicitly marked discussed-only, since implementing either requires patching vLLM's scheduler internals, a materially bigger lift than a client-side proxy).

This is the third critique round in a row where a genuine methodological or analytical error was caught, root-caused, and fixed rather than defended — the pattern itself is now a real strength of the paper's narrative, not incidental.

## Fourth critique round — Table 9 metric bug fixed, mean-combining fixed, and a real environmental limitation discovered and disclosed (2026-09-06)

**Table 9 metric inconsistency (real error):** was mixing `|AUC-0.5|` (undefended column) with `max(AUC,1-AUC)` (defended columns) in the same table. Fixed to use `max(AUC,1-AUC)` throughout.

**n=200 rerun of T_MAX=150 (fixed proxy):** clean, coherent, trustworthy. hot-vs-ram=0.632 [0.578,0.686], hot-vs-disk=0.633 [0.579,0.688], ram-vs-disk=0.527 [0.470,0.583] (CI touches 0.5). This is now the primary reported defense number.

**Multi-round detection, corrected:** majority-vote (hard-decision) analysis was genuinely understating the attack — replaced with mean-combining (soft-decision, average raw latencies before one threshold decision), recalibrated to the midpoint threshold (38.22ms) instead of the single-shot Youden threshold. Result: 69.8% (k=1) → 97.5% (k=10) → 99.2% (k=15), matching the reviewer's own hand-calculation almost exactly (d'≈1.22 per probe, scales as √k).

**T_MAX=300 comparison: pursued hard, ultimately reported as inconclusive rather than forced.** Sequence of events: (1) n=200 rerun showed disk_evicted max=788ms (7x the original 113.66ms calibration baseline) — flagged as needing explanation. (2) A second n=200 rerun showed even worse, all-states-inflated numbers (hot mean 356ms vs. expected ~301ms) — diagnosed as likely ambient system load. (3) Checked system state directly (load average, GPU temp) — confirmed load had been elevated during the run and was settling. (4) Launched a "clean" re-run once load settled — still showed the same inflation pattern, ruling out simple ambient-load-at-the-time-of-check as the explanation. (5) Found and fixed a real bug: the proxy used module-level `requests.post()` (fresh TCP connection every call) instead of a persistent, pooled `Session` — confirmed the fix worked via the upstream server's own access log showing one persistent source port. (6) Re-ran with the fix — instability persisted (individual trials alternating between clean ~312ms readings and unexplained spikes to 776ms for states that should be rock-steady). **Conclusion: real, unresolved measurement-environment jitter (most likely WSL2/host-OS scheduling, which scales with how long a request thread holds a connection open) that we could not eliminate in the time available.** Reported as an explicit, honest limitation in PAPER_DRAFT.md §5.6 rather than forced into a "300ms closes the deep channel" or "doesn't close it" claim either way. This is a genuine engineering finding in its own right: implementing a reliable constant-time defense inside a virtualized dev environment is harder than the naive version suggests, for reasons beyond the sleep-remainder bug already documented.

**CPU-tier headroom reframed as a mitigation, not just an attack-tuning knob:** added as its own row in the §5.4 table (0.79 with headroom vs. 0.99 without) — zero latency cost, moderate host-RAM cost, doesn't fully close the channel but is a cheap complement to the other rows.

**Quantized padding:** implemented (bucket-based rounding instead of a hard ceiling). Tested at bucket=150ms, n=100 (chosen so most requests need only one bucket). Showed the SAME instability as the T_MAX=300 attempts -- including for `hot` requests that should trivially complete within one bucket. This ruled out the working hypothesis that instability scaled with padding duration specifically; it appears to be session-level environmental degradation (this machine, after ~many hours of continuous heavy GPU/CPU use across this whole project) rather than tied to any specific T_MAX/bucket value. Stopped the test rather than report unreliable numbers. Reported in the paper as "implemented and motivated, not experimentally validated" -- an honest status, not a fabricated result.

**Session-level lesson for future work on this machine:** at this point, sub-100ms-precision timing experiments are no longer reliable in this WSL2 environment without a fresh restart of the VM/session. This affected only the NEW defense-margin experiments (T_MAX=300, quantized padding) attempted late in this very long session -- it does not retroactively call into question the earlier, already-completed RQ1-4/rank-sweep/cache-sweep/Poisson/Scenario-B results, which were collected before this degradation became severe and were each internally consistent and coherent at time of collection.

**Meta-commentary trimmed** throughout §5.4-5.6 per direct feedback that self-justifying narration ("exactly the kind of thing that should not survive review," etc.) reads as anxiety and costs space needed for the actual numbers.

## Fifth critique round — GPU power-throttling root cause found, native-ext4 filesystem confound quantified, production-scale cache config tested (2026-09-08)

**Root cause of the T_MAX=300/quantized-padding instability, finally found.** `nvidia-smi -q -d POWER` showed Current Power Limit = 35-40W against a Default Power Limit of 115W, while the GPU sat at a cool 40°C — power-based, not thermal, throttling. Cause: the laptop was running on battery (confirmed via `Get-CimInstance Win32_Battery`, BatteryStatus=1/discharging, charge draining 40%→22% over the diagnostic session). Laptop vendors hard-cap discrete-GPU power budget on battery independent of temperature. User plugged in AC power; `nvidia-smi` then showed Current Power Limit=140W (above the 115W default, i.e. full boost), BatteryStatus=2 (charging), no active throttle reasons. This resolves the entire "unstable measurement environment" thread from the fourth critique round — WSL2/host-OS scheduling jitter was never the cause.

**9p-filesystem-bridge confound quantified, with mechanism.** Re-ran RQ1's exact protocol on a fresh server reading adapters from native ext4 (`/home/researcher/native_test`) instead of the 9p bridge to `/mnt/e` every other experiment in this paper uses. n=30: hot=25.89ms, ram_evicted=30.63ms, disk_evicted=36.58ms (vs. Table 1's 27.13/36.58/80.53ms). n=100 (tighter estimate): hot=29.32ms(std10.64), ram=35.00ms(std8.16), disk=40.65ms(std9.04); AUC hot-vs-disk=0.8667[0.81,0.92], ram-vs-disk=0.7432[0.67,0.81], hot-vs-ram=0.7937[0.72,0.86] — all real (Shapiro-Wilk confirms non-normal, Mann-Whitney p<10⁻⁸) but far weaker than Table 1's near-perfect separation. Mechanism confirmed: hot and ram_evicted (GPU-resident / CPU-RAM-resident reload, never touch the filesystem) are statistically unchanged between the two environments; disk_evicted (the one state that reads the adapter file from storage) is the only one that dropped, by roughly half. Applying the same median-of-N aggregation §4.5 already established for contention noise recovers strong separability here too: median-of-5 AUC=0.9950. Written up in full in PAPER_DRAFT.md §3.7, with a forward-pointer from §4.1 and a caveat added to the abstract. Did NOT re-run RQ2-RQ4/rank-sweep/cache-sweep/cross-model/Scenario-B/defense-eval on native storage — not feasible in the time available; those results remain internally consistent (9p-bridged) per §3.7's within-run invariant, but likely inflated on the disk tier specifically, same mechanism.

**Production-scale cache configuration tested — the critique's central objection, answered empirically.** vLLM's own default for `max_cpu_loras` is `max_num_seqs` (confirmed via docs.vllm.ai), commonly tens to hundreds in production — nothing like this paper's `--max-cpu-loras 4`. Generated 65 additional rank-{8,16,32} filler adapters (`make_junk_adapters.py`, untrained stand-ins, valid since only tensor shape matters for cache-pressure purposes) and relaunched the native-ext4 server at `--max-loras 8 --max-cpu-loras 64` with 67 total registered adapters (med, law, 65 fillers). Forcing disk eviction now requires cycling all 65 fillers (`max_cpu_loras+1`), exactly as the critique predicted — but this is not a barrier for an attacker who already knows adapter names (Scenario A), only more requests.

RQ1 protocol at this scale, n=30, idle GPU: hot=20.73ms(std1.23), ram_evicted=28.27ms(std1.90), disk_evicted=33.57ms(std2.23). AUC: hot-vs-ram=**0.9944**[0.978,1.000], hot-vs-disk=**1.0000**[1.000,1.000], ram-vs-disk=**0.9689**[0.917,1.000]. This directly contradicts the critique's predicted failure mode ("the RAM tier is where your channel is weak... AUC~0.68 under load") for the idle-GPU case: at production cache scale, under idle conditions, all three tiers remain cleanly, near-perfectly separable — if anything tighter than the original small-scale 9p-based numbers, likely because this run benefited from stable AC power and a quiet system.

RQ3 (identification, med vs law) at the same scale, n=40: raw accuracy at an a-priori 27ms threshold (chosen from RQ1-prod's own hot/disk midpoint) was 82.5% (33/40), with errors concentrated in "neither" misclassifications very close to the threshold boundary. Per-adapter Youden-optimal thresholds recomputed from the same data (AUC=0.9600 for A-active, 1.0000 for B-active) recovered 90.0% (36/40), with the residual errors concentrated in one specific confusion (`both`→`B`, 3/10 `both` trials) — the same "errors cluster in one failure mode, not scattered" pattern the original small-scale n=120 run showed. Folded into PAPER_DRAFT.md §4.6 as a new "Production-scale cache configuration" paragraph + Table 8, with tables 8/9/10 renumbered to 9/10/11 to stay sequential, and into the abstract and §8.

Generated 6 more untrained adapters (`adapters_track/`) to serve as a "tracked 8" set (med, law, track_0..track_5) distinct from the 65 filler adapters, and ran an 8-way (single-active-of-8) identification test at the same production cache scale, to address the critique's "eight adapters, 8-way... probe cost and false positives compound" item.

**Result: 100% (80/80), Wilson 95% CI [95.4%, 100%].** True-active adapter consistently read 19-22ms vs. 29-43ms for the other 7 — a much cleaner separation than the 4-way production-scale test (90.0%), likely because argmin-over-8 is threshold-free by construction (no calibration point to get wrong) whereas the 4-way design's per-adapter binary thresholding is exactly where that test's errors came from. Probe cost scales linearly with tracked-set size (8 probes/trial vs. 2); accuracy did not degrade. Folded into PAPER_DRAFT.md §4.6 and abstract; §8's limitation item updated from "planned" to "measured, one scale point."

Server crash note: relaunching vLLM for the 8-way test initially failed with a CUDA OOM ("Free memory 3.22/8.0 GiB... less than desired GPU memory utilization 0.75, 6.0 GiB") — root cause: `pkill -9 -f 'vllm serve'` matches the API-server process by its literal command-line string but NOT its `VLLM::EngineCore` worker subprocess (a different process title), so two prior servers' engine-core workers were still holding VRAM. Fixed by killing the specific lingering PIDs directly; worth remembering for any future server relaunch on this box.

## Sixth critique round — volume-sweep design flaw caught before it entered the paper, plus a cleanup pass (2026-09-08)

**Real methodological catch: the first volume-sweep run was blocked by rate, not interleaved.** `rq_volume_sweep.py`'s original loop (`for rate in args.rates: for trial in range(...)`) ran all 15 trials at rate=0, then all 15 at rate=0.1, ..., ascending. Since §4.5/§4.6 both document real session-length latency drift, this design makes rate and session-order nearly collinear — any detection-vs-rate trend could be partly or entirely a time artifact. Checked this empirically on the completed pilot run rather than just accepting the theoretical risk: Spearman(session_order, latency) = -0.603 (p=3.1e-10) vs. Spearman(rate, latency) = -0.592 (p=8.2e-10) — nearly identical magnitude, confirming the confound is real in this specific run, not just possible. Monotonicity across adjacent rate-pair means also broke at one point (4/5, not 5/5). **Conclusion: this pilot run does not count as evidence either way and is not going in the paper as a validated result.**

**Fixed and re-run.** `rq_volume_sweep.py` now builds the full (rate, trial) schedule and shuffles it (seeded), logs `session_order` per row for future confound-checking, and added a `--canary` option (10 probes of a non-target, non-filler adapter at the very start and very end of the run) per §3.7's stated discipline. Re-launched at the same 6 rates × 15 trials, with `nvidia-smi -q -d POWER` logged at both ends of the run to make "stable AC power throughout" a recorded fact rather than an assumption — confirmed still on AC (BatteryStatus=2, charging, 72%) before relaunch. Result pending.

**Paper cleanup applied while waiting (all non-GPU, no new data):**
- Reordered §4.6 so Table 7 (cross-model replication) physically precedes Table 8 (production-scale cache config) — they were in the wrong physical order even though numbered correctly, an easy reviewer catch.
- Fixed a stale "(the unmeasured Scenario B channel, §2)" parenthetical in §5.4 — Scenario B has been measured since the third critique round; now reads "(the Scenario B channel, measured in §5.5 at AUC=0.79-0.99)".
- Abstract now leads with 82.5% (the honest, non-recalibrated RQ3-production-scale accuracy) rather than the train-set-optimistic 90.0%, matching how Scenario B's own headline number is already flagged elsewhere in the paper.
- §4.5's "build around the disk tier, not the RAM tier" recommendation now carries an explicit scope caveat: it was calibrated on the small-scale, 9p-bridged config's absolute gap sizes, and §3.7/§4.6 both found the RAM tier shows comparable-or-stronger idle-GPU separation once the 9p-bridge inflation of the disk tier is removed — whether this recommendation holds under contention at production scale or on native storage is untested, not assumed to transfer. Added to §8 too.
- §3.1 now states explicitly which experiments use the default (small-scale, 9p) config vs. the two that don't (§3.7's filesystem check, §4.6's production-scale check + 8-way extension use native ext4; the latter also uses `max_loras=8/max_cpu_loras=64`).
- Drafted the vLLM disclosure email (`docs/DISCLOSURE_DRAFT.md`) — not yet sent, per §7's stated plan.

**Also flagged, not yet acted on:** total paper length is now ~15,000 words, likely 2-3x a typical AISec workshop page budget. Noted to the user as a distinct, deliberate cutting pass to do once the empirical work settles, not something to rush alongside it.

**Corrected volume sweep, result: clean success.** Canary check confirmed no drift this time — settled `law` readings 18.04ms (start) vs. 18.06ms (end), Mann-Whitney p=0.70. Confound checks confirmed the shuffle worked: session_order vs. rate ρ=-0.07 (p=0.51), session_order vs. latency ρ=0.09 (p=0.37) — both null, unlike the discarded pilot's ρ≈-0.6 collinearity. With the confound ruled out: detection frequency by rate = 6.7%/73.3%/73.3%/80.0%/86.7%/100.0% (rates 0/0.1/0.3/0.5/1.0/2.0), **Spearman ρ=0.5466 (p=2.5e-8)** on rate vs. detected-activity, **ρ=-0.6232 (p=5.4e-11)** on rate vs. raw latency directly. Saturates at 100% by rate=2.0/s — consistent with the adapter becoming continuously resident at that traffic level (mechanism, not a sensitivity ceiling), exactly as anticipated. Folded into PAPER_DRAFT.md §4.6 (full writeup), abstract (one sentence), §5.5 and §8 (cross-references updated, bracket placeholder removed). This uses Scenario A's direct-naming protocol; a Scenario-B-specific version remains open, stated as such in both places.

**Rank-sweep native-ext4 check: the last unquantified confound, and it's worse than RQ1's.** Relaunched a native-ext4 server with the five rank-sweep adapters (med_r1/med/med_r16/med_r32/med_r64, `--max-lora-rank 64`) plus the 6 junk fillers, matching `run_rank_sweep.sh`'s exact protocol (n=15/rank, `max_cpu_loras=4`). Result: slope=**0.1364ms/rank-unit** [0.1023,0.1704], R²=**0.4661**, p=1.5e-11 — vs. the original 9p-bridged 3.42ms/rank-unit, R²=0.967. That's roughly a **25x** inflation factor, well beyond the ~2x seen on the RQ1 disk-tier gap itself. Mechanistically sensible: rank differences are file-size differences, and a bridge whose overhead scales with bytes transferred amplifies a size-dependent slope far more than it inflates one fixed reload cost — this measurement is sensitive to a derivative (rate of latency growth with size), which per-byte overhead distorts more than an intercept. The relationship stays real, monotonic (31.6→32.5→33.7→35.9→40.2ms across ranks 1/8/16/32/64), and highly significant; only its magnitude was overstated. Folded into §3.7 (as a second, more severe instance of the same confound), §4.3.1, §4.6, and the abstract — native slope now stated as the trustworthy number throughout, 9p slope kept as reported-and-corrected context, same treatment as the RQ1 disk-tier finding.

**Seventh critique round — five wording fixes, all applied.** (1) §4.5 no longer conflates RQ2 (signal genuinely below noise floor, doesn't recover) and RQ3 (threshold miscalibration as scale shifts) — split into two explicit sentences, Scenario B pointed to §5.5. (2) §1's "present in every multi-LoRA serving system" replaced with the safer "deliberate architectural response to the scaling constraint... one implementation of this broader pattern," cross-referencing §6.2's verification. (3) "Provably" removed from §4.4 and §5.4 (both were experimental observations — exact equality across 300 tested positions — not formal proofs); reworded to "we observe exact equality" / "isolates the timing channel from the measured confound." (4) §2's Scenario B bullet now states the idle-GPU condition and points to the contention result immediately, not two sections later. (5) §8's conclusion and Table 7's caption reworded "production-representative" → "production-scale" throughout (was defensible as a cache-size stress point, not an actual production deployment). Also updated PROJECT.md's own stale top-of-file contribution table (added a current-status version, kept the original as explicitly-labeled history) and corrected the KVGov "explicitly scopes out" overclaim that had already been fixed in the paper but not here.

**CORRECTION to the entry below: the n=40 aggregation-recovers-it result did not survive a properly-nested bootstrap or a larger n=200 re-run. Read this note first.** The n=40 single-probe advantage (0.57) had a CI [0.38,0.76] that already included no-effect; the reported "aggregation reaches 0.95 by N=30" was a bootstrap projection computed by resampling only the derived groups, not the original 40 trials, which understates uncertainty. Recomputed correctly (resampling the original data, propagating its uncertainty into each N): every N's CI touched or nearly touched 0.5, including N=30 (0.95 [0.53,1.00]). Re-ran at n=200 to settle it properly: single-probe advantage=0.5498 [0.4689,0.6305] (CI includes below-0.5 — not established), and active/idle means nearly converged (64.20 vs 65.50ms, vs. the idle-GPU 36.71 vs 21.42ms gap) — a gap-erasure pattern, not RQ1's noisier-but-preserved-gap pattern. Directly-measured aggregation (grouping real consecutive same-label trials, not bootstrap-projecting) at N=5/10/20: advantage 0.595/0.550/0.600 — flat, noisy, every CI touching 0.5. **Conclusion reversed: we do NOT have evidence that aggregation recovers this signal under this contention level.** Hypothesized mechanism (not confirmed): Scenario B's detector depends on the attacker's own adapters holding a stable self-tracked LRU ordering, which ANY competing cache traffic (not just the victim's) can disrupt — a more severe contention-sensitivity than RQ1's simpler hot-vs-evicted mechanism. Rewrote §5.5's contention subsection, the abstract, and §8 to report this honestly as an open, unresolved limitation rather than a solved result. This is the most consequential single correction of the session — caught only because the user pushed on "bootstrap the whole curve and report a CI at each N" rather than accepting the point-estimate curve.

**Scenario B under contention — the single most important remaining validity question, now measured [SUPERSEDED, see correction above].** Set up a fresh native-ext4 server at production-scale tight config (`max_loras=8, max_cpu_loras=8`, zero CPU-tier headroom — the config that gave the strongest small-scale signal, replicated at scale): victim=`med`, attacker owns 8 adapters (law, track_0-5, junk_0_r8), separate 8-adapter noise pool (noise_0-7, excluded from both attacker and victim roles, using the corrected noise generator that never touches victim/attacker adapters).

Idle-GPU baseline at this exact config: **AUC=1.0000 [1.000,1.000] (n=40)** — cleaner than the original small-scale tight result (0.9875), consistent with zero headroom forcing full disk-depth eviction every time.

Under 6-worker contention (n=40): fixed-threshold (30ms) detector collapses to **50.0% (chance)**, Wilson CI [35.2%,64.8%] — same failure mode as RQ2/RQ3. Threshold-free single-probe AUC=**0.5700** [0.3791,0.7551] — barely above chance, not significant at this n, weaker than RQ1's contention-degraded existence signal (~0.70). But unlike RQ2/RQ3, median-of-N aggregation recovers it: advantage 0.59(N=1)→0.67(N=5)→0.77(N=10)→0.89(N=20)→0.95(N=30). Genuinely different pattern from both RQ1 (recovers fast, N=3) and RQ2/RQ3 (never recovers) — Scenario B recovers, but slowly, needing dozens of rounds for a strong result.

Folded into §5.5 (new subsection), abstract (one clause), and §8 (new limitation-turned-result item, plus updated the now-stale "untested" production-scale/contention bullet). This directly answers the reviewer's stated top priority: the central claim survives realistic contention, but only for a patient, multi-round attacker — a real, now-quantified cost rather than an assumed one.

**Cut pass #2: applied the "replace a result with a bound" template to three more sections.** §4.5 (noise-robustness matrix) compressed from ~6 paragraphs + a 5-row table to one bound paragraph with inline numbers, dropping Table 4 entirely (renumbering all subsequent tables 5→4 through 11→10 to stay sequential). §5.6 (defense evaluation) compressed by cutting the v1-flawed-implementation narrative entirely (kept only the one-sentence lesson: pad to an absolute deadline, not a computed remainder, since sleep overshoot scales with duration) and folding the T_MAX=300 power-throttling story into a cross-reference to §3.7/§8 rather than re-narrating it. §6.2 (multi-LoRA system architecture verification) compressed from 4 paragraphs to 1, keeping the S-LoRA secondary-source correction (the one substantive catch) and cutting the rest. Net word count after this pass: ~15,200 (roughly flat vs. before this critique round's new experiments were added — meaning the paper now holds substantially more validated content at the same length, but the big cut is still fully ahead).

**Rank-sweep follow-up: bucket-resolution analysis, functional-form check, and a scope demotion.** Computed native-data linear-vs-log-linear fit directly rather than assume the critique's prediction that they'd be indistinguishable: linear still wins (R²=0.4661 vs. 0.3376, a real 0.13 gap). Computed pairwise rank AUCs and probes-needed-for-AUC≥0.95 via median-of-N bootstrap: adjacent ranks (8-vs-16, 1.25ms gap) stay unresolvable past 30 probes; wide spans (8-vs-64, 7.72ms; 1-vs-64, 8.56ms) resolve in a single probe. Rewrote §4.3.1 (retitled "a supporting observation," cut the now-superseded two-point med-vs-law statistical detail entirely) and §4.6's rank-sweep subsection (Table 5 now presents native data as primary with per-rank stds, 9p demoted to one caveat sentence; added the bucket-resolution paragraph). This was also the correct place to start the length cut the paper still needs — a ~0.14ms/rank effect billed as a contribution was exactly the kind of thing a reviewer would flag.

**Remaining before the T_MAX=300 re-run:** kill lingering `VLLM::EngineCore` workers explicitly (learned from the 8-way OOM), log `nvidia-smi -q -d POWER` at both ends, confirm still on AC power immediately before launch.

**T_MAX=300 re-run: clean, and the power hypothesis is confirmed.** Killed lingering `VLLM::EngineCore` workers explicitly (learned from the 8-way OOM), confirmed AC power via `Get-CimInstance Win32_Battery` (charging, 82%) and `nvidia-smi -q -d POWER` (140W) immediately before launch, relaunched the original small-scale 9p-path server (`launch_server.sh`), and re-ran the exact n=200 protocol through the fixed (absolute-deadline) proxy at T_MAX=300ms, logging power at both ends (140W start and end, no drift).

Result: **hot=301.95ms (std=0.82), ram_evicted=301.93ms (std=1.12)** — both now tightly, reliably padded with zero spiking, confirming the previous 400-800ms instability was entirely the battery-power-throttling confound, not the proxy, WSL2, or the padding mechanism. `disk_evicted=306.47ms (std=25.84, max=557.56ms)` still shows real overshoot in 12/200 (>310ms) and 4/200 (>400ms) trials — but this is the already-documented "padding can only pad up" mechanism (true latency exceeding the ceiling), not the mystery instability, and is expected given disk_evicted's known heavy right tail.

Distinguishing advantage at T=300: hot-vs-ram=**0.568** [0.511,0.624], hot-vs-disk=**0.563** [0.506,0.618], ram-vs-disk=**0.502** [0.445,0.560] (fully closed). Compared to T=150's 0.632/0.633/0.527: doubling the margin genuinely helps (advantage drops ~0.06-0.07 on the hot-vs-evicted comparisons) but does not close the residual, exactly matching the critique's original structural point (the ceiling must exceed what an adaptive adversary can induce, and disk_evicted's true latency occasionally exceeds even 300ms). Folded into PAPER_DRAFT.md Table 10, §5.4's Table 9 and bullet, §5.6's "what we take away," and §8 (bracket removed, replaced with the real result). This closes the last open experimental thread from this critique round — quantized padding remains untested under the corrected power state, unchanged from its prior "implemented, not validated" status.

**Correction after review: the volume sweep's headline Spearman was substantially carried by the idle-vs-nonzero step, not a graded rate response.** Recomputed on the 75 nonzero-rate trials alone (rates 0.1/0.3/0.5/1.0/2.0): rate-vs-detection drops from ρ=0.5466 (all 90) to ρ=0.2491 (p=0.031, barely significant); rate-vs-raw-latency drops from ρ=-0.6232 to ρ=-0.4290 (p=0.00012, holds up meaningfully better — the threshold-free measure, as expected, is the more robust one). Also added Wilson 95% CIs per rate point directly into the paper (they were previously only "in the repository," which is exactly the point-estimate-in-abstract/interval-in-appendix asymmetry we'd already fixed elsewhere) and named rate=0's 6.7% (1/15) explicitly as the false-positive rate. Fixed "volume estimate"/"estimation" language in the abstract and §4.6 to "tracks victim request rate" — we measured ordinal correlation, not a rate estimator, and estimation would need a held-out curve inversion we haven't built. All folded into PAPER_DRAFT.md §4.6/§5.5/§8/abstract.

**Honest scope of the production-scale (8/64) result specifically, not the volume sweep below.** This is idle-GPU, n=30, one session, one config point (8/64). Contention-robustness at production cache scale has not been tested (the original paper's §4.5 noise-robustness matrix used the small-scale config) — that remains the natural next check before claiming the production-scale result is fully load-bearing under realistic concurrent traffic.

## Open engineering questions to resolve during build (all resolved — kept for history)

- [x] Confirm GPU passthrough works inside WSL2 (`nvidia-smi` inside WSL)
- [x] vLLM version compatible with driver CUDA 13.1 / an appropriate torch cu12x wheel
- [x] Train or source `med` (medical QA) and `law` (legal text) LoRA adapters at mixed ranks (e.g. 8 and 32) for Llama-3.2-1B
- [x] Set of junk adapters for prime/eviction pressure
- [x] Tune `--max-loras` / `--max-cpu-loras` to get a reliable, large hot/disk-evicted gap
- [x] Build timing harness: nanosecond timestamps, burst probing, ordering log, thermal/clock sampling
- [x] Server-side instrumentation for ground-truth residency state (separate from attacker's client-side timing)
