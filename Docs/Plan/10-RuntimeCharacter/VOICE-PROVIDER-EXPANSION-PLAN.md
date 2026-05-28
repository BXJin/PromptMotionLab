# Voice Provider Expansion Plan

Updated: 2026-05-18

## Decision

Use Azure first.

The MVP needs a working spoken character loop before optimizing for local-only inference.

```text
MVP:
Azure STT / Azure TTS
-> Speech Timeline JSON
-> Unreal audio playback
-> Azure viseme events drive lip-sync
```

Local providers are still part of the architecture, but they are not the first implementation path.

## Provider Layers

Keep ASR, LLM, and TTS replaceable.

```text
AsrProvider
- AzureSpeechAsrProvider
- WhisperProvider
- Qwen3AsrProvider

RuntimeBehaviorProvider
- OpenAiRuntimeBehaviorProvider
- LocalRuntimeBehaviorProvider

TtsProvider
- AzureSpeechTtsProvider
- ElevenLabsTtsProvider
- FishSpeechProvider
```

The Unreal client should not care which provider is used. It should receive normalized runtime events:

```text
STT final text
Behavior JSON
Speech Timeline JSON
audio URL or stream
viseme timeline
latency metadata
```

## ASR Direction

### Phase 1 - Azure STT

Use Azure first because it reduces integration risk.

Goals:

- working push-to-talk transcription
- stable final transcript
- latency metrics
- later VAD/EoT integration

### Phase 2 - Local ASR Candidate: Qwen3-ASR

Qwen3-ASR-1.7B is a valid future candidate.

Why it is interesting:

- Apache-2.0 model license
- supports many languages
- supports offline and streaming inference in the upstream model
- 1.7B size is plausible for local GPU or optimized serving

Why it should not be the first MVP path:

- `Qwen3-ASR-1.7B-8bit` MLX builds are mainly useful for Apple/MLX environments
- Windows + Unreal + local streaming ASR adds infrastructure before the basic voice loop is proven
- streaming support depends on the serving backend
- VAD/EoT still has to be solved separately
- local ASR latency must be measured on the target machine, not assumed from model size

Use Qwen3-ASR later only behind `AsrProvider`.

## TTS Direction

### Phase 1 - Azure TTS

Use Azure first because viseme events and audio offsets are useful for Unreal lip-sync.

Goals:

- generate audio
- return viseme id + audio offset
- build Speech Timeline JSON
- drive mouth morphs in Unreal

### Phase 2 - Higher Naturalness Providers

If Azure voice quality is not good enough, compare:

- ElevenLabs for expressive hosted voices
- Fish Speech for self-hosted expressive voice generation

Do not switch until Azure proves the end-to-end audio/lip-sync path.

## Local LLM Direction

Local LLM is a latency/cost/privacy option, not an immediate requirement.

Add later when:

- cloud LLM latency is the main bottleneck
- offline demo is required
- privacy-sensitive deployment is required
- cost becomes a real constraint

Local LLM should use the same `RuntimeBehaviorProvider` contract and must still return schema-valid Behavior JSON.

## Latency Metrics

Every provider swap must be measured with the same fields:

```text
stt_ms
llm_ms
tts_ms
total_server_ms
unreal_round_trip_ms
first_visible_reaction_ms
first_audio_start_ms
provider
model
tech_profile
```

Recommended `tech_profile` examples:

```text
azure_stt_openai_azure_tts_v1
azure_stt_local_llm_azure_tts_v1
qwen3_asr_openai_azure_tts_v1
qwen3_asr_local_llm_fish_tts_v1
```

Do not claim a provider is faster until these numbers are recorded on the target PC.

## Cold Assessment

Qwen3-ASR can be a good Whisper replacement candidate later.

It should not block the current milestone.

The next implementation should remain:

```text
Azure TTS + viseme timeline
-> Unreal lip-sync
-> Azure STT push-to-talk
-> VAD/EoT
-> local ASR/LLM/TTS provider experiments
```
