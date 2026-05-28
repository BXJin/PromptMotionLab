# Runtime Character Matrix Test

## Purpose

Validate realtime conversation behavior before Unreal character UI, weather tools, and final face tuning.

This test answers three questions:

- Does the same prompt produce natural variation across repeated runs?
- Do different `characterId` values produce meaningfully different replies?
- What are the response/TTS latencies for each route and model?

## What This Test Measures

CSV columns include:

- `character_id`
- `case_id`
- `repeat_index`
- `message`
- `status`
- `accepted_ms`
- `response_ready_ms`
- `tts_ready_ms`
- `total_ms`
- `provider`
- `model`
- `route`
- `fallback_used`
- `reply`
- `emotion`
- `intent`
- `tts_duration_seconds`
- `viseme_count`
- `issues`

Summary includes average, p95, and max latency by model, route, and character.

The script also writes a JSON file with raw accepted/final job payloads.

Default output folder:

```text
Build/reports/runtime_character_matrix/
```

## How To Run

1. Start the server:

```bat
scripts\run-server.bat
```

2. In another terminal:

```bat
python scripts\runtime_character_matrix_test.py
```

Optional:

```bat
python scripts\runtime_character_matrix_test.py --repeats 3
python scripts\runtime_character_matrix_test.py --characters default_girl,e_f_n,i_t_s
python scripts\runtime_character_matrix_test.py --cases Docs\Plan\10-RuntimeCharacter\runtime_character_matrix_cases.json
```

## Current Scope

This is server-side validation only.

Included:

- same prompt repeated multiple times
- multiple `characterId` values
- route/model/latency recording
- response/TTS completion timing
- loose pass/fail checks

Not included yet:

- Unreal character type selection UI
- weather/tool execution
- face preset quality scoring
- semantic repeat detection by embeddings
- human-labeled user state accuracy

## Interpretation

Good signs:

- `short_social` prompts usually use `gpt-4.1-nano`
- weather/tool-like prompts stay on the default model
- `fallback_used` is false
- responses are short, natural, and not identical across repeats
- character IDs produce noticeably different tone once character profiles are implemented

Known limitation:

Until the 8 character profiles and prompt builder are implemented, `characterId` differences may be small or absent. This test still records the baseline.

Tool/realtime-info cases are kept separate from the default daily-conversation matrix:

```bat
python scripts\runtime_character_matrix_test.py --cases Docs\Plan\10-RuntimeCharacter\runtime_character_tool_cases.json
```

Stress cases intentionally mix greetings, apologies, emotional disclosure, and short instructions to expose routing and behavior-guard regressions:

```bat
python scripts\runtime_character_matrix_test.py --cases Docs\Plan\10-RuntimeCharacter\runtime_character_stress_cases.json
```

## Voice WAV Regression

Use this when you want fixed WAV inputs for STT and conversation regression.

The script uses the server TTS endpoint to synthesize the test sentences, downloads the WAV files, and optionally runs batch STT against those WAV files. This is useful for repeatable server-side checks before doing visual face/lip-sync review in Unreal.

```bat
python scripts\runtime_voice_regression_wav_test.py
```

Default input cases:

```text
Docs/Plan/10-RuntimeCharacter/runtime_voice_regression_cases.json
```

Default output folder:

```text
Build/reports/voice_regression/<timestamp>/
```

Outputs:

- `wav/*.wav` generated test audio
- `voice_regression_*.csv` STT/TTS result table
- `voice_regression_*.json` raw payloads
- `voice_regression_*_summary.json` aggregate timings

To generate matrix-compatible cases from the STT transcripts:

```bat
python scripts\runtime_voice_regression_wav_test.py --write-matrix-cases
```

Then run the character matrix against the generated file:

```bat
python scripts\runtime_character_matrix_test.py --cases Build\reports\voice_regression\<timestamp>\runtime_character_matrix_cases_from_voice_<timestamp>.json
```

Limitations:

- TTS-generated WAV is cleaner than real microphone audio, so it is not a replacement for live PTT testing.
- Visual face/lip-sync quality still requires Unreal viewport review.
