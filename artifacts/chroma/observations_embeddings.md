**Embedding comparison (3 models, chunking `B_rec_384_64`, dense top-3, 38 dev questions).**

- `bge-m3` (open-source): Hit@3 0.95, MRR 0.868, Prec@3 0.67, index time 27s
- `bge-base` (open-source): Hit@3 0.90, MRR 0.816, Prec@3 0.57, index time 8s
- `mxbai-large` (open-source): Hit@3 0.84, MRR 0.768, Prec@3 0.50, index time 20s

**Best overall by MRR:** `bge-m3`. **Selected for the final system:** `bge-m3` (best open-source: MRR 0.868, Hit@3 0.95).
Commercial comparison: skipped: no OPENAI_API_KEY.
Cost/speed: `bge-base` indexes in 8s vs `bge-m3` in 27s. With only 38 dev questions, differences of a few points in MRR are within noise: read them as a tie-break between similar models, not as a ranking.
Caveat: synthetic questions are generated from the same text they are tested on, which can flatter models with high lexical overlap; hand-written questions in `eval_manual.csv` reduce this bias.