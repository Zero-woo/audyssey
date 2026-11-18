# Routing eval set: generation guide

You are writing test cases for a router. The router reads one Korean edit request plus a summary of a video-audio editing job. It answers with exactly one decision:

- one edit command,
- `clarify` (ask back), or
- `none` (not an edit request).

Each case states the request and the set of answers that count as correct.

## Output format

Output one JSON object per line (JSONL), with exactly these keys and no others:

```json
{"id": "<prefix>-001", "fixture": "F1", "request": "개 짖는 소리 반으로 줄여줘", "category": "positive", "pair": null, "template": "<prefix>-t01", "expected": [{"type": "set_gain", "source_id": "s1", "gain": {"ge": 0.4, "le": 0.6}}], "split": null}
```

- `id`: unique, using your prefix (given in your task).
- `template`: one intent. All paraphrases of the same intent share a template id. Every case in a template has the same `category`, and usually the same `fixture`.
- `category`: one of `positive`, `none`, `near_miss`, `clarify`, `constraint`, `composite`.
- `pair`: for `near_miss` only, the confusable pair this case probes, written exactly as in the table below (e.g. `"set_gain|set_pitch"`). Use `null` otherwise.
- `expected`: the allowed set. Any one entry matching counts as correct. List two entries only when both answers are genuinely right.
- `split`: always `null`.

### Expected entries

- **command:** `{"type": "<command>", "source_id": "<id>", ...value fields}`. The `source_id` must exist in the fixture; use `"residual"` for 나머지 소리.
  - Numbers are absolute values, computed from the job's current values.
  - Give a number for an exact value.
  - Give a range for an approximate value: `{"ge": x, "le": y}` (keys `lt`, `le`, `ge`, `gt`).
  - `gain` is the new absolute gain, 0–2, where 1 is unchanged. "반으로" on a source at gain 1 → `{"ge": 0.4, "le": 0.6}`. "두 배로" from 1 → `2.0`.
  - `semitones` is the new absolute pitch shift, an integer from −12 to 12, equal to current `pitch_semitones` + change. "한 키 올려" from 0 → `1`.
  - `add_source` uses `{"type": "add_source", "method": "separate"|"generate", "plan": {"kind": "<kind>"}}`. Kinds are `sfx`, `dialogue`, `music`, `ambience`. Do not pin the name or description.
  - `render` uses `{"type": "render"}`.
  - `reseparate` and `generate` use `{"type": ..., "source_id": ...}` and do not pin the description.
- **clarify:** `{"type": "clarify", "reason": "<reason>"}`, where the reason is one of `ambiguous_target`, `missing_value`, `composite`, `unsupported`, `other`.
- **none:** `[{"type": "none"}]`.

## The five job states (fixtures)

All fixtures are 12 s long, and every one has a residual track ("나머지 소리", id `residual`, keep true, gain 1). Sources are listed as id, name (kind, origin, state):

- **F1, basic:**
  - s1 dog barking (sfx, separated)
  - s2 car passing (sfx, separated)
  - s3 man speaking (dialogue, separated)
  - s4 street ambience (ambience, separated)
  - All are on, gain 1, pitch 0.
- **F2, similar sources:**
  - s1 big dog barking (sfx)
  - s2 small dog barking (sfx)
  - s3 birds chirping (ambience)
  - All are separated and on, gain 1.
- **F3, generated replacement:**
  - s1 dog barking (sfx, separated, **keep=false**)
  - s2 dog barking (generated) (sfx, generated, replaces s1, on)
  - s3 woman speaking (dialogue, separated)
- **F4, silent video:**
  - silent=true.
  - s1 footsteps (sfx, generated)
  - s2 wind (ambience, generated)
  - Separation is impossible here.
- **F5, off/quiet sources:**
  - s1 dog barking (sfx, **keep=false**)
  - s2 car horn (sfx, **gain 0.3**)
  - s3 man speaking (dialogue, gain 1)

## Commands and what the system can and cannot do

| command | does | cannot |
|---|---|---|
| `keep` / `drop` | turn a source or residual on / off | — |
| `set_gain` | set volume 0–2 (absolute) | values outside 0–2 |
| `set_pitch` | set pitch −12..12 semitones (absolute) | residual; outside ±12 |
| `reseparate` | separate the source again from the original audio | residual, generated sources, silent videos |
| `generate` | replace a source with a generated one (the original is muted and kept) | residual, dialogue |
| `add_source` | add a new sound by separating it from the audio, or by generating it | separate on a silent video; generate dialogue; reuse an existing name |
| `render` | export / mix the result | — |

## Decision rules (these define the right answers)

1. **The amount must be explicit.** `set_gain` / `set_pitch` need a numeric, multiplier or fraction amount ("반으로", "두 배", "30%", "0.5로", "한 키", "반음", "옥타브").
   - A bare or vague request ("줄여줘", "키워줘", "좀 높여줘", "조금", "살짝", "많이", "시끄러워") → `clarify` / `missing_value`.
   - Turning something fully off or on is not an amount problem: "꺼줘", "안 들리게", "빼줘" → `drop`; "다시 켜줘", "살려줘" → `keep`.
2. **Out of range** (gain above 2 such as "3배", pitch beyond ±12 such as "20키") → `clarify` / `unsupported`. Never clamp.
3. **Known impossible actions** (table above), such as regenerating dialogue, re-separating on F4, or pitch on residual → `clarify` / `unsupported`.
4. **Ambiguous target.** Two or more sources match ("개 소리" in F2), no source is named for an edit, or the target is a screen position ("왼쪽에서 짖는 개") → `clarify` / `ambiguous_target`. If both the target and the amount are missing, either `ambiguous_target` or `missing_value` is acceptable; list both.
5. **Two or more edits in one request** ("차 소리 줄이고 새소리 추가해") → `clarify` / `composite`.
6. **Not an edit request** (questions about the video, chit-chat, unsupported features such as subtitles, trimming, speed or video effects) → `none`.
7. "Fully quiet" wording ("거의 안 들리게", "아예 없애") may allow both `drop` and `set_gain` with `{"le": 0.1}`. List both.
8. Names in requests are natural Korean or English descriptions ("개 짖는 소리", "자동차", "남자 목소리", "배경 소음", "dog sound"). Never use ids like s1 in the request.

## Categories and counts (for your share)

Your task gives your share. As a whole, the set covers:

- **positive:** every command, with plain requests that have an explicit amount where one is needed.
- **near_miss:** one case per pair from the table below. The request should be easy to confuse with the other side of its pair.

  | pair | boundary |
  |---|---|
  | `set_gain\|set_pitch` | "높여/낮춰" can mean volume or pitch ("목소리 한 키 높여" vs "목소리 소리 두 배로") |
  | `drop\|set_gain` | off vs quieter ("차 소리 빼줘" vs "차 소리 반으로") |
  | `keep\|set_gain` | turning an off source back on vs making it louder (F3/F5 keep=false sources; F5 car horn at 0.3) |
  | `reseparate\|generate` | extract again from the original vs make a new one |
  | `add_source_separate\|add_source_generate` | a sound present in the original (separate) vs absent (generate) |
  | `render\|none` | export request vs a question about exporting |
  | `residual\|source` | "나머지 소리 / 배경 잡음" means residual vs a named ambience source |

- **none:** questions, chit-chat, unsupported features.
- **clarify:** ambiguous_target, missing_value, and screen-position references.
- **constraint:** known-impossible actions → `clarify` / `unsupported`.
- **composite:** two or more edits in one request → `clarify` / `composite`.

## Style

- Mix 존댓말 and 반말, short and long requests, a typo here and there, mixed English ("dog volume 반으로"), and implicit wording.
- Write each paraphrase in a template with genuinely different wording, not just a changed particle.
- Double-check every `source_id` and every number against the fixture before you output it.
