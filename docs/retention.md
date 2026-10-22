# Retention rules behind the checks (Oct 2026)

`reelsmith build <dir> --lint` (and every `--stills` / full build) prints **RETENTION CHECKS**. Each rule comes from a source below. Grades: [OFFICIAL] platform or exec statement, [RESEARCH] peer-reviewed or preprint, [DATA] large-sample industry analysis, [EXPERT] practitioner framework. Most evidence is correlational, and follower count / distribution explains more than any creative feature.

| Check | Rule | Evidence |
|---|---|---|
| voice start | voice (or a sound) from the first frames, `vo.offset` ≈ 0.05 | Instagram's Reels ranking predicts "watched under 3 s" incl. skips within 2 s [OFFICIAL, Meta Reels system card, 11/2025]; audio-visual hook in the first 1–2 s → 1.5× odds of top-20% purchase intent [DATA, Meta × Toluna, Reels ads] |
| hook text at 0 s | the hook works on mute from frame 0; spoken line = on-screen text = first frame | 63% of top-CTR TikTok ads show the key message in 3 s [OFFICIAL, TikTok Creative Tips]; swipes cluster in the first 20% of a video [RESEARCH, Li et al. 2022, arXiv 2204.12954] |
| code word in hook | CTA after the payoff, never in the hook | Instagram named "comment a specific word" an engagement-bait example (06/2024), then said ManyChat-style flows are fine [OFFICIAL]; effect on reach unmeasured |
| pace | ≈ 0.33 visual changes/s; > 0.5/s for long lowers watch-through and rewatching; no 4 s stretch without a change | Dost & Huang 2026 (N=242, median 0.33 cuts/s) [RESEARCH]; inverted U of shot count vs engagement, 2,511 TikToks [RESEARCH, Xiao, Li & Mou 2024] |
| voice pace | faster speech → more engagement; TTS voices read slowly, try `vo.speed` 1.12–1.15 | Guo, Kim & Rubin 2014, 6.9M sessions [RESEARCH]; faster speech raised shares on TikTok [RESEARCH, Xiao 2024] |
| end card ≤ 3 s, no tail | cut right after the payoff and the CTA | 42% of swipes fall in the last 20% of a video [RESEARCH, Li 2022]; completion is judged against same-length videos [OFFICIAL, Meta; RESEARCH, Kuaishou KDD'22] |
| > 60 s | make a ≤ 59 s Shorts cut | Shorts over 1 min with any Content ID claim are blocked worldwide [OFFICIAL, YouTube Help 15424877] |
| subtitles ≤ 17 chars/s | 2–5 words per chunk (`subs_words`, default 5) | Netflix timed-text reading speed for adult content [OFFICIAL style guide]; captions improve comprehension [RESEARCH, Gernsbacher 2015 review] |
| first frame | not dark, already moving | Instagram skip rate counts views that leave within 3 s [OFFICIAL, 08/2025] |
| loop | last frame close to the first when the story loops | replays count as views on Shorts (03/2025) [OFFICIAL]; no peer-reviewed loop study exists yet |

## Script rules (skills/reel-script)
Topic clear by 4 s, a contrast word by 5 s, payoff foreshadowed by 6 s, first value by 10 s, rehook at 10–12 s, a turn in the middle; beats linked by *but / therefore* [EXPERT: Kallaway, Jenny Hoyos, Parker & Stone]. Sends per reach is Instagram's strongest signal for non-follower reach [OFFICIAL, Mosseri 2024–2025]: write identity lines, humour, awe or real usefulness, and don't ask for shares outright.

## Sources
- Meta, Instagram Reels Chaining system card: https://transparency.meta.com/features/explaining-ranking/ig-reels-chaining/
- Mosseri on top signals (01/2025): https://www.socialmediatoday.com/news/instagram-shares-algorithm-insights-2025/738034/
- Instagram on single-word CTAs and ManyChat (06/2024): https://www.socialmediatoday.com/news/instagram-clarifies-advice-single-word-ctas-longer-reels/718151/
- Instagram retention chart and skip rate (08/2025): https://www.socialmediatoday.com/news/instagram-adds-retention-insights-reels/758464/
- TikTok Auction Ads Creative Tips: https://ads.tiktok.com/business/library/Auction_Ads_Creative_Tips.pdf
- Li et al. 2022, swipe behaviour in short videos: https://arxiv.org/abs/2204.12954
- Zhan et al., KDD'22, duration-debiased watch time: https://arxiv.org/abs/2206.06003
- Dost & Huang 2026, editing pace: https://archives.marketing-trends-congress.com/2026/pages/PDF/paper_professor_DOST_HUANG.pdf
- Xiao, Li & Mou 2024, Internet Research: https://www.emerald.com/insight/content/doi/10.1108/intr-07-2023-0521/full/pdf
- Guo, Kim & Rubin 2014: https://up.csail.mit.edu/other-pubs/las2014-pguo-engagement.pdf
- Meta × Toluna Reels ads study: https://ppc.land/meta-and-toluna-study-finds-emojis-lift-reels-purchase-intent-2-5x/
- YouTube Shorts length and Content ID: https://support.google.com/youtube/answer/15424877
- Gernsbacher 2015, captions review: https://doi.org/10.1177/2372732215602130
