# iPhone blue-light color filter for sleep — does removing (almost) all blue actually help?

**Run:** aletheia-research 0.4 `max` · 6 framings → 6 leaves · 418 sources, 73 primaries read in full,
341 independent origins, echo 0.18. 6 load-bearing numbers re-verified against primaries by an
independent second model (Sonnet) — **4 confirmed, 2 corrected** (noted inline).

## Bottom line
**Mostly no — not from the color change itself.** Direct trials of phone blue-light filters on sleep
are **null**, and the stronger, better-studied proxy (blue-blocking glasses) is **null** in blinded
trials. BUT the underlying mechanism is real, and your *specific* extreme intervention (remove almost
all blue) is the physiologically correct lever **only if you also drop brightness far down**. Honest
verdict: aggressive blue-removal + low brightness can produce a real but **modest melatonin/circadian**
effect; do not expect a meaningful change in sleep *quality/onset* from the color tint per se. The
dominant factors are (1) that you're on the phone at all and (2) total brightness.

## Verified numbers (second-model checked against primaries)
- **Direct RCT (decisive):** Duraccio 2021 (*Sleep Health*, n=167), 3 arms — Night Shift ON vs OFF vs
  no-phone, 7 nights actigraphy. **No difference between arms**; only *not using the phone* helped (and
  only in adequate sleepers). Night Shift ON = OFF = nothing. [verified]
- **Proxy (blue-blocking glasses):** blinded placebo-controlled meta (Luna-Rangel 2025, n=49) —
  sleep-onset **−4.9 min (p=0.54)**, total sleep **+8.8 min (p=0.70)**, both null; Cochrane 2023 —
  filtering lenses *"probably make no difference,"* low certainty. [verified]
- **Behavior dominates:** interactive/arousing screen use delays sleep **30 ± 14 min**; passive
  same-light use is *not* associated with later onset (Reichenberger 2024). Perceived color per se has
  no effect — the lever is melanopic irradiance, not tint (Blume 2023, blue/yellow metamers). [verified]

## Mechanism — real, but magnitude is the whole story
- Melatonin suppression is driven by melanopsin/ipRGCs (peak ~480 nm), quantified by **melanopic EDI**,
  not ordinary lux. Removing blue is the correct way to cut melanopic dose.
- **Can a phone even suppress melatonin? Contested** (a genuine disagreement I had to adjudicate):
  older work (Zeitzer 2000) put half-max at ~80–160 lux (phone ≈ 20 lux → little), but Phillips 2019
  (PNAS) found a group **ED50 ≈ 25 lux** (phone ≈ *half-maximal*) with a **58-fold** individual range
  (ED50 6–350 lux). So "a phone can't affect melatonin" is too strong; "it can, modestly, and it hugely
  depends on the person" is right. Children saturate near 5–10 lux. [verified]
- **Does filtering help at phone levels?** A metamer experiment (Schöllhorn/Lucas 2023) shows a large
  ~66–75% melanopic cut roughly **halves** melatonin suppression — proof the lever works. **[corrected:
  the ~1-hour onset advance is from the extreme ~30-fold end-to-end comparison; a realistic 2–3× cut
  shifts onset ~30 min, not an hour.]** Critically, warming color *without dimming* doesn't meaningfully
  change melatonin (Nagare 2019 — Night Shift's settings gave 10% vs 17% suppression, ns), and the
  evening "safe" threshold is **<10 melanopic-EDI lux** (Brown 2022), which a normal-brightness display
  exceeds. **[corrected: a specific "28.6 melanopic-lux" iPad figure a worker cited is not in the source
  and is dropped as miscited; the qualitative point — color-shift-alone ≈ no change — stands.]**

## Why the mechanism is real yet the sleep trials are null
Three reasons: (1) melatonin *suppression* ≠ worse *sleep* — a modest, variable blunting from a dim
phone doesn't reliably move measured onset/quality; (2) the tested interventions (Night Shift, mild
filters) cut only ~50% of blue, not "almost all," and don't dim — staying above the melanopic threshold
that matters; (3) the real sleep-killer is behavioral (arousing content) + total brightness, which a
color tint doesn't touch. Even the stronger whole-field intervention (amber glasses) is null in blinded
trials — and the *positive* glasses results are unblinded/expectancy designs (you can see the amber, so
blinding breaks).

## Practical read (for your exact setup)
- The iOS Accessibility color-filter trick removing *almost all* blue is stronger than Night Shift and
  is the right lever mechanistically — **but only paired with the lowest brightness** (spectrum +
  intensity together get you under the <10 melanopic-lux threshold; color alone at full brightness
  doesn't).
- Expect the payoff to be **circadian/melatonin** (possibly ~30 min earlier melatonin/onset *if* you're
  light-sensitive or a night owl), **not** a big jump in sleep quality. If you're not especially
  light-sensitive, the effect may be negligible.
- Higher-leverage moves, by the evidence: don't use the phone in the hour before bed (the only thing
  that beat both filter arms in the RCT); if you must, use it *passively* (not interactive/arousing) and
  dim / hold at arm's length.
- Net: the color filter is a cheap, defensible add-on — closer to "a weak form of dimming" than to a
  distinct blue-light cure.

## Honest gaps
- **No RCT tests your exact intervention** (near-total blue removal via Accessibility filter at low
  brightness). The nulls rebut *partial* filters (Night Shift) and glasses; your extreme setting is
  inferred from mechanism + dosimetry, not directly trialed — the biggest gap.
- Blinding is intrinsically broken for any visible color filter → subjective "it helps" is
  expectancy-prone.
- >50× inter-individual variability in light sensitivity means population nulls can hide real responders
  (and non-responders).
- Two worker-level number errors were caught and corrected by the cross-model verifier (1 h → 30 min
  onset magnitude; a miscited iPad lux figure) — even primary-read numbers need a second pass.
