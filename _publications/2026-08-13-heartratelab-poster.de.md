---
title: "Using The HeartRateLab.jl for Normative Evaluation of Heart Rate Variability from Open Datasets"
collection: publications
category: posters
permalink: /publication/2026-heartratelab-poster
lang: de
excerpt: 'Normative HRV-Referenzen, mit HeartRateLab.jl aus offenen PhysioNet-Datensätzen erstellt: die Aufnahmen eines Teilnehmers bei langsamer Atmung, bewertet sowohl gegen eine allgemeine gesunde Population als auch gegen eine Gruppe von Meditierenden — dieselbe Aufnahme, zwei Urteile.'
date: 2026-08-13
venue: 'JuliaCon 2026'
slidesurl: 'https://github.com/abcsds/HeartRateLab.jl/blob/main/docs/poster/poster_notes.md'
paperurl: 'https://github.com/abcsds/HeartRateLab.jl/blob/main/docs/poster/juliacon2026_poster.pdf'
citation: 'Barradas-Chacón, L. A. (2026). Using The HeartRateLab.jl for Normative Evaluation of Heart Rate Variability from Open Datasets. Poster presented at JuliaCon 2026, Mainz, Germany, 13 August 2026.'
---

Given a new HRV recording, "is it normal?" is unanswerable without a reference — and the answer changes with the reference. This poster builds normative references from open PhysioNet data using HeartRateLab.jl, scores one participant's longitudinal recordings against them, and is explicit about what the score does and does not mean.

One subject (148 windows over 88 dates of paced resonant breathing, 2019–2025) is scored against two references: a general healthy population (nsrdb + nsr2db, 61,715 windows from 66 subjects) and a group of meditators (263 windows from 11 practitioners). Against the general population the participant's low-frequency band is strongly elevated (LF/HF z = +2.6, LF power z = +2.5) while short-term vagal tone sits at the healthy median (RMSSD z = +0.0). Re-scored against the meditators, the elevation roughly halves (LF/HF z = +1.7) — the same recording, two verdicts: atypical for the general population, but meditator-like.

The full Julia pipeline is shown end to end: reading inter-beat intervals, preprocessing, extracting 53 registered HRV features, windowing, fitting a per-feature normative prior by maximum likelihood, and re-expressing a percentile as a normal-equivalent z score. The references are convenience open datasets rather than populations sampled to represent "normal", so the claim is deliberately narrow: relative to these datasets, here is where the participant falls.
