# Context-Aware Subtitle Translation (DeepL API)

This is the single reference for how SRTranslator builds DeepL context. It replaces the
former `LLM_SUBTRANS_CONTEXT.md` and `CONFIGURATION.md`, which described older budgets.

Everything here applies to the `deepl-api` translator. The scraper and DeepLX translators
receive the same context string, but only the official API has a real `context` parameter.

## Why context matters

DeepL translates **each entry of the text list independently**. Entries in one request never
see each other. The only thing they share is the `context` parameter. A subtitle chunk is a
list of short lines, so without context a line like "He looked tired" has nothing to
disambiguate it.

This is why the current chunk is **repeated inside** the context, alongside the lines around
it. Context characters are not billed by DeepL, so there is no cost reason to keep it small.

For Finnish this matters more than for most targets. "Hän" covers he and she, and only the
surrounding dialogue reveals which person is meant.

## What gets sent

Built by `_build_deepl_context()` in `srtranslator/srt_file.py` and `ass_file.py`. Both
copies are kept in step deliberately.

```
Scene 3

Earlier in this scene:
The detective arrived at the crime scene...
The witness described a tall man...

Previous dialogue:
12. She looked worried.
13. The meeting had gone badly.

Current dialogue:
14. He said nothing.
15. Not a single word.

Upcoming dialogue:
16. John would have to fix this.
17. There was no other choice.
```

| Block | Source | Default budget |
|---|---|---|
| Earlier in this scene | Distant lines, truncated to 50 characters each | 2000 chars |
| Previous dialogue | Lines before the chunk, walking backwards | 4000 chars |
| Current dialogue | The chunk being translated | Bounded by `max_char` |
| Upcoming dialogue | Lines after the chunk | 2000 chars |

Line numbers are the subtitle's own index, so they match the file.

## Rules the builder follows

- **Scenes are never crossed.** Boundaries come from timing gaps of 2.0 seconds or more,
  detected by `_detect_scenes()`. Each scene starts fresh.
- **Translated lines are never used as context.** On a `.tmp` resume the first lines of the
  file already hold target-language text, so the backward walk stops at `self.start_from`.
- **Placeholders are stripped.** The `////` dialog marker and the ASS line break
  placeholder (four backslashes) are replaced by spaces via `clean_context_line()` in
  `srtranslator/util.py`. Only the context copy is cleaned; the text actually sent for
  translation keeps its placeholders so `wrap_lines` can restore them.
- **The request body is kept under the limit.** DeepL rejects a body over 128 KiB.
  `_context_for_chunk()` tries the budget tiers in `util.CONTEXT_BUDGETS` in order and takes
  the first whose bytes fit under `MAX_REQUEST_BODY_BYTES` (120 000). Chunks are measured in
  characters while the body is measured in bytes, and CJK text runs up to 3 bytes per
  character, which is why the guard exists.

## Tuning

The budgets are function arguments, not CLI flags. Change the defaults in
`_build_deepl_context()`, or the tier list in `srtranslator/util.py`.

Scene gap is the one knob worth touching per content type. It is the
`scene_gap_seconds` argument of `_detect_scenes()`.

| Content | Value |
|---|---|
| Default, most material | 2.0 |
| Fast-paced action | 1.5 |
| Slow drama, more continuity | 3.0 |
| Near-continuous dialogue | 4.0 |

Hardcoded by design: the `{line_num}. {content}` line format, the block headings, and the
50-character truncation in scene summaries.

## CLI options

```bash
srtranslator movie.srt \
  --translator deepl-api \
  --auth "YOUR_KEY" \
  --src-lang en --dest-lang fi \
  --context "Television drama series. Natural conversational dialogue."
```

- `--context` adds a global description in front of the per-chunk context, joined by a blank
  line. Give genre and tone, for example "Action thriller film. Dynamic and intense
  dialogue." or "Historical drama set in 1920s. Formal period-appropriate language."
- `--model-type` defaults to `quality_optimized`, DeepL's next-generation model, which has
  covered every language pair since December 2025. Use `latency_optimized` for the faster
  classic model. `prefer_quality_optimized` is a legacy alias of `quality_optimized`.
- `--instruction` passes a DeepL custom instruction such as "Keep character names
  untranslated". Repeatable up to 10 times, 300 characters each. DeepL supports it only for
  target languages de, en, es, fr, it, ja, ko and zh; for any other target it is dropped with
  a warning. It cannot be combined with `latency_optimized`.

Do not use `--context` to give orders. DeepL states that context is reference material, not
a system prompt. Rules and tone belong in `--instruction`.

## Debugging

```bash
DEBUG_CONTEXT=1 srtranslator movie.srt --translator deepl-api --auth "KEY" -i en -o fi
```

Prints the scene count, then per chunk the line range and the exact context string.

What to check:

- The current chunk's lines **do** appear, under "Current dialogue". This is intended.
- Line numbers are sequential and stay inside one scene.
- No `////` or stray backslashes survive in the context.
- On a resumed run, "Previous dialogue" holds no already-translated lines.

## Billing

Only the `text` array is billed. Context is free, and so is a generous scene summary. The
translator sums `billed_characters` across the run and logs the total at INFO level on exit,
along with the `model_type_used` reported by the first response.

One API call is made per chunk. Chunk size comes from `translator.max_char`, 1500 characters
for DeepL. Context does not change the number of calls.
