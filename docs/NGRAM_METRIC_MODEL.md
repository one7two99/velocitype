# Velocitype — N-Gram Metric Model (Design)

_Backing the "bigrams, trigrams, and rhythm breaks" claim with real data.
Mirrors the existing per-key aggregation pattern (`key_stats`), reuses stored
`keystrokes` + `layouts.finger_map`, and stays inside the current architecture
(metrics in code, LLM only sees a summary)._

Target version: `0.27.0`.

---

## 0. Core insight

Three claimed capabilities collapse onto **one** primitive:

- A **bigram** is a key→key transition. Its **inter-key interval (IKI)** is the
  rhythm unit — the same delta the per-key code already computes
  (`ts_offset_ms[i] − ts_offset_ms[i-1]`).
- **Rhythm** is the *spread* of a bigram's IKIs: a steady bigram has low
  variance; a **rhythm break** is an occurrence whose IKI is far above your own
  baseline for that bigram (a hitch/hesitation).
- **Trigrams** add the direction dimension (rolls vs. redirects), which is a
  *classification* of finger movement, not a new measurement.

So rhythm is not a separate metric — it is bigram-latency consistency plus a
hitch counter. Nothing new needs to be captured at the keystroke layer.

---

## 1. What gets persisted vs. derived

| Data | Strategy | Why |
|---|---|---|
| **Bigrams** | **Persisted** running aggregate (`ngram_stats`), one row per `(user, layout, bigram)`. | Bounded (≤ ~30×30 = 900/layout, realistically far fewer observed), high value, needed for trend + recency + rhythm. |
| **Trigrams** | **Derived on read** from stored `keystrokes` over a recent window (e.g. last 20 sessions). | Trigram space is ~27 000; a persistent aggregate would bloat the table for data the coach reads only occasionally. Redirect/roll analysis is a read-time rollup, not a hot path. |

Alternative (documented, not chosen for v1): persist trigrams too, gated behind a
frequency floor (`attempts ≥ K`) so only common trigrams get a row. Switch to
this only if read-time trigram computation shows up in profiling.

---

## 2. Bigram / trigram classification (pure, from `finger_map` + `hand_map`)

New pure module `backend/app/engine/ngrams.py` (framework-free, unit-testable,
same discipline as `adaptive.py`). All classification is derived from the layout
maps that already exist — **no layout changes required**.

Per-hand finger order, pinky→index (used for roll direction):

```
LP=1  LR=2  LM=3  LI=4      RI=4  RM=3  RR=2  RP=1
```

`classify_bigram(c1, c2, layout) -> BigramClass`:

| Class | Rule | Split-keyboard meaning |
|---|---|---|
| `REPEAT` | `c1 == c2` | Double-letter; distinct motor pattern from an SFB. |
| `SFB` (same-finger bigram) | `finger(c1) == finger(c2)` and `c1 != c2` | **The marquee weakness.** Slow, cramped; minimizing these is the entire point of Colemak-DH. |
| `ROLL_IN` | same hand, different fingers, order strictly increasing (toward index) | Fast, comfortable inward roll. |
| `ROLL_OUT` | same hand, different fingers, order strictly decreasing (toward pinky) | Roll outward; usually weaker than inward. |
| `ALTERNATION` | `hand(c1) != hand(c2)` | Hand alternation; generally the easiest. |

`classify_trigram(c1, c2, layout) -> TrigramClass` (derived at read time):

| Class | Rule |
|---|---|
| `REDIRECT` | all three same hand, direction of (c1→c2) reverses at (c2→c3) — an awkward in-then-out (or out-then-in) motion. |
| `ROLL3` | all three same hand, monotonic direction — a smooth three-key roll. |
| `ALT` | hands alternate (L-R-L / R-L-R). |
| `SFB_CHAIN` | contains an `SFB` in either adjacent pair. |
| `OTHER` | anything else. |

**Deferred honestly:** *lateral-stretch bigrams (LSB)* need column x-coordinates,
which `finger_map` does not encode (finger only, not physical column). v1 does
not claim LSB detection. If wanted later, add an optional `coord_map`
(`char -> (row, col)`) to `Layout`; classification then extends without touching
the metric store.

---

## 3. Schema — `ngram_stats` (bigrams)

Mirrors `key_stats` field-for-field so the online mean/variance math and the
recency bookkeeping are identical and reviewable side by side.

```python
# backend/app/models/ngram_stat.py
class NgramStat(Base):
    __tablename__ = "ngram_stats"

    user_id:    Mapped[UUID]  = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    layout_id:  Mapped[str]   = mapped_column(String(64), primary_key=True)
    ngram:      Mapped[str]   = mapped_column(String(8), primary_key=True)   # e.g. "sr"
    n:          Mapped[int]   = mapped_column(Integer, server_default=text("2"), nullable=False)  # 2 (forward-compat)

    attempts:   Mapped[int]   = mapped_column(Integer, server_default=text("0"), nullable=False)
    errors:     Mapped[int]   = mapped_column(Integer, server_default=text("0"), nullable=False)

    # Transition-time (IKI) aggregate → mean + spread → rhythm consistency.
    # Identical running-stats shape as key_stats.
    avg_latency_ms:  Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    latency_n:       Mapped[int]   = mapped_column(Integer, server_default=text("0"), nullable=False)
    latency_sq_sum:  Mapped[float] = mapped_column(Float,   server_default=text("0"), nullable=False)

    # Direct "rhythm break" counter: transitions whose IKI blew past this
    # bigram's running mean at ingest time (see §4). rate = hitch_n / latency_n.
    hitch_n:    Mapped[int]   = mapped_column(Integer, server_default=text("0"), nullable=False)

    last_session_seq: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    updated_at:       Mapped[datetime] = mapped_column(DateTime(timezone=True),
                          server_default=func.now(), onupdate=func.now(), nullable=False)
```

Index: the composite PK already covers the `(user_id, layout_id)` range scan used
by `build_ngram_metrics`.

Migration `alembic/versions/0005_ngram_stats.py`: `create_table` only. Optional
one-off **backfill** (recommended, since raw keystrokes are retained): iterate
each user's historical `keystrokes` per session in `ts_offset_ms` order and fold
them through the same aggregator (§4) so existing users get bigram data on day
one instead of starting empty.

---

## 4. Ingest — extend `key_stats.apply_keystrokes`

Add a sibling folder `_bigram_aggregates(keystrokes)` and roll its output into
`ngram_stats` in the same commit as the per-key roll-up. Rules:

**Chain formation.** Walk the batch in `ts_offset_ms` order, holding `prev`.
Form the bigram `(prev.expected_char, cur.expected_char)` only when **both** are
single trainable chars (`len == 1` and in `layout.characters`). Any token that
is not a single trainable char — `space`, `backspace`, `enter`, layer keys —
**resets `prev` to None** (no bigram spans a word boundary or an edit).

**Latency (the rhythm signal).** `iki = cur.ts_offset_ms − prev.ts_offset_ms`.
Use the IKI, **not** `hold_ms` (hold is single-key dwell; the transition is what
carries rhythm).

**Error attribution.** Count `attempts += 1` for every formed bigram;
`errors += 1` when `not cur.correct` (the transition landed wrong).

**Clean rhythm, honest errors.** Contribute the IKI to the latency aggregate
**only when both keys are correct** — error-recovery pauses are huge and would
wreck the consistency metric. Errors are still counted above; only the *timing*
of fumbled transitions is excluded.

**Pause guard.** Ignore IKIs `> IKI_CAP_MS` (default **3000**) for the latency
aggregate — that's a coffee break, not a bigram rhythm. (Still counts as a hitch,
see below.)

**Hitch counter (rhythm break).** At ingest, if a correct-pair IKI exceeds
`HITCH_FACTOR × running_mean` (default `HITCH_FACTOR = 2.5`, using the mean known
*before* this batch's update) **or** exceeds `IKI_CAP_MS`, increment `hitch_n`.
This gives an online, defensible "rhythm break rate" = `hitch_n / latency_n`
without storing per-sample data.

Running mean/variance update is copied verbatim from the existing `key_stats`
merge (prior_n / prior_avg / combined_n), so there is exactly one algorithm to
trust.

---

## 5. Pure engine — metrics, consistency, scoring

In `engine/ngrams.py`, alongside the classifiers:

```python
@dataclass
class NgramMetric:
    ngram: str
    n: int
    attempts: int
    errors: int
    avg_latency_ms: float | None
    latency_n: int
    latency_sq_sum: float
    hitch_n: int
    sessions_since_seen: int
```

**Consistency (rhythm)** — identical formula to per-key `latency_consistency`:

```
stddev   = sqrt(max(0, latency_sq_sum/latency_n − mean²))
cv       = stddev / mean                      # mean = avg_latency_ms
consistency = clamp(1 − cv, 0, 1)             # 1.0 == metronomic
```

**Weakness score** (`weakest_bigrams`, tuned differently from per-key — for
n-grams flow matters more than raw speed, and SFBs are the highest-value fix):

```
raw = W_ERR    · error_rate
    + W_RHYTHM  · (1 − consistency)
    + W_LAT     · normalized_latency        # vs. median bigram latency, as in adaptive.py
    + W_RECENCY · recency_penalty
score = raw · (1 + SFB_BONUS if class == SFB else 1)
```

Proposed starting weights (tunable, mirror `adaptive.py`'s explicit constants):
`W_ERR = 0.35`, `W_RHYTHM = 0.35`, `W_LAT = 0.20`, `W_RECENCY = 0.10`,
`SFB_BONUS = 0.5`.

**Trust threshold.** Only rank bigrams with `attempts ≥ MIN_NGRAM_ATTEMPTS`
(default **8**) and `latency_n ≥ 4` — never surface a bigram seen twice as "your
worst."

---

## 6. Service + API integration

- `services/ngram_stats.py`:
  - `apply_bigrams(...)` — called from within `apply_keystrokes` (same commit).
  - `build_ngram_metrics(db, user_id, layout_id) -> list[NgramMetric]` — the read
    side, mirrors `build_key_metrics`.
  - `build_trigram_rollup(db, user_id, layout_id, window_sessions=20)` — derives
    trigrams on demand from stored keystrokes; returns counts + mean latency per
    `TrigramClass`, plus the worst `REDIRECT`/`SFB_CHAIN` trigrams.
- `services/coach.py` — extend the summary the LLM sees (this is what actually
  backs the claim). Add a compact block to the `analyze` payload:

  ```json
  {
    "weak_bigrams": [
      {"bigram": "sr", "class": "SFB", "err_pct": 22, "wpm": 41, "consistency": 0.63, "hitch_pct": 9}
    ],
    "trigram_rollup": {"redirect_pct": 14, "sfb_chain_pct": 6, "worst_redirect": "was"}
  }
  ```

  Update `ANALYZE_USER` to reference bigrams/trigrams/rhythm explicitly (keep
  "never invent numbers; use only the data provided"). The prose can now say
  *"your same-finger bigram `sr` is choppy (63% consistent, 22% errors)"* — the
  claim is literally grounded in the payload.

- **Drills targeting bigrams.** Extend `drill()` so `focus` can be *bigrams*, not
  only keys: add `_annotate_focus_bigrams` and have the drill prompt ask to weave
  the target bigrams into real words. Extend `_covers_focus` to count bigram
  substrings (`lesson.count("sr")`), keeping the existing verify-retry-fallback
  loop. The deterministic fallback `adaptive.generate_lesson` already injects
  bigram shells, so coverage stays guaranteed.

- **API surface.** Add `GET /api/stats/ngrams` (bigram table + consistency for the
  Analysis page / a future rhythm heatmap) and include the trigram rollup in
  `GET /api/coach/metrics`. No auth/model changes.

---

## 7. Decisions called out (so review is fast)

1. **Rhythm = bigram IKI consistency + hitch rate.** No new keystroke capture.
2. **Bigrams persisted; trigrams derived on read.** Keeps the table lean; revisit
   only if profiling says so.
3. **Fumbled-transition IKIs excluded from rhythm, still counted as errors.**
   Clean timing, honest error rate.
4. **Boundary tokens reset the chain**; `IKI_CAP_MS` guards against pauses.
5. **SFB gets a score bonus** — it's the most actionable fix on an ergo layout and
   the one the target audience cares about most.
6. **LSB deferred** — needs column coordinates the layout doesn't carry yet;
   v1 does not claim it.
7. **Backfill from retained keystrokes** so existing users aren't reset to zero.

---

## 8. Suggested build order

1. `engine/ngrams.py` — classifiers + `NgramMetric` + `weakest_bigrams`, with unit
   tests (pure, no DB) covering SFB/roll/redirect on both Colemak-DH and QWERTY.
2. `models/ngram_stat.py` + migration `0005` (+ optional backfill script).
3. Extend `key_stats.apply_keystrokes` with `_bigram_aggregates` + `ngram_stats`
   upsert; test against a hand-built keystroke stream with a known SFB.
4. `services/ngram_stats.build_ngram_metrics` + `build_trigram_rollup`.
5. Wire into `coach.analyze` summary + prompt; then bigram-targeted `drill`.
6. `GET /api/stats/ngrams`; frontend Analysis/heatmap surface (separate task).
