# Latency Measurement Plan

Updated: 2026-05-17

## Purpose

The runtime goal is not only "get an LLM answer." The goal is to minimize the time from user input to visible character reaction, first spoken audio, and stable facial behavior.

Latency must be measured from the beginning. Otherwise it is impossible to know whether STT, LLM, TTS, Unreal, or network transfer is the bottleneck.

## Recommended Log Format

Use CSV first, not Excel-native `.xlsx`.

Reason:

- CSV can be appended from Python and Unreal easily.
- Excel, Google Sheets, and pandas can all open it.
- It works well for quick latency charts.
- It avoids adding spreadsheet dependencies to the runtime server.

Recommended file:

```text
Server-Python/data/metrics/runtime_latency.csv
Client-Unreal/PromptMotionClient/Saved/Metrics/runtime_latency_client.csv
```

Server and Unreal write separate files first. Join them later by `request_id`.
This avoids file locking and packaging-path issues while the runtime is still changing.

## CSV Columns

```csv
timestamp,session_id,request_id,input_mode,message_length,provider,model,fallback_used,stt_ms,llm_ms,tts_ms,total_server_ms,unreal_round_trip_ms,first_visible_reaction_ms,first_audio_start_ms,emotion,intent,notes
```

Column meaning:

| Column | Meaning |
|---|---|
| timestamp | ISO timestamp when request started |
| session_id | runtime session id |
| request_id | client or server request id |
| input_mode | text, push_to_talk, vad_stt, streaming_stt |
| message_length | final user text length |
| provider | OpenAI, mock, Azure, local, etc. |
| model | active LLM/STT/TTS model when known |
| tech_profile | applied pipeline or optimization set, such as text_llm_behavior_json_v1 |
| fallback_used | true if fallback response was used |
| stt_ms | audio to final text time |
| llm_ms | final text to Behavior JSON time |
| tts_ms | reply text to audio/timeline time |
| total_server_ms | full server processing time |
| unreal_round_trip_ms | Unreal request to response received |
| first_visible_reaction_ms | user action to listening/thinking face |
| first_audio_start_ms | user action to audio playback start |
| emotion | final behavior emotion |
| intent | final behavior intent |
| notes | timeout, parse fallback, network issue, manual note |

## Measurement Targets

Current text MVP:

```text
0-150 ms   immediate local visible reaction in Unreal
2-5 sec    non-streaming LLM response, depending on provider/model/network
```

Push-to-talk STT MVP:

```text
record end -> final STT text
final STT text -> LLM Behavior JSON
Behavior JSON -> face preset applied
```

Later voice loop:

```text
speech start
-> VAD detects speech
-> partial STT drives listening reaction
-> EoT decides user finished
-> final STT text
-> LLM Behavior JSON
-> first TTS audio
-> lip-sync / expression timeline
```

## Practical Rule

Do not optimize based on feeling alone.

Every latency improvement should answer:

```text
Which stage got faster?
By how many ms?
Did visible reaction improve, or only backend timing?
Did quality regress?
```

## Implementation Notes

Server should record:

- provider latency
- fallback usage
- model name
- tech profile
- session id
- input mode
- behavior emotion / intent

Unreal should record:

- request id
- request sent time
- response received time
- first local reaction time
- first face preset applied time
- first audio playback time, when TTS exists

The first implementation can append rows to CSV. A dashboard or Excel template can come later.

Recommended `tech_profile` values:

| Value | Meaning |
|---|---|
| text_llm_behavior_json_v1 | text input -> LLM -> Behavior JSON -> Unreal face preset |
| text_fastpath_behavior_json_v1 | rule fast path -> Behavior JSON without LLM |
| sse_reaction_stream_v1 | server sends immediate reaction event before final response |
| push_to_talk_stt_v1 | push-to-talk STT added before LLM |
| tts_speech_timeline_v1 | TTS and Speech Timeline added |
| vad_eot_v1 | VAD and End-of-Turn detection added |
| streaming_response_v1 | streaming LLM/TTS response path added |
