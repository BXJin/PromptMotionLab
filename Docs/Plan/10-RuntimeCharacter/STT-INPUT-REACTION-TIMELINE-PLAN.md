# STT Input Reaction Timeline Plan

Updated: 2026-05-15

## Purpose

This document defines how the character reacts while the user is still speaking.

This is separate from the answer timeline:

```text
User speaking
-> STT partial text / pause / filler events
-> Input Reaction Planner
-> Listening Timeline
-> facial preset + gaze + blink + head motion

User finished speaking
-> final STT text
-> text cleanup / question extraction
-> LLM / RAG / Memory
-> answer Behavior JSON + Speech Timeline
-> TTS + lip-sync + response gestures
```

The character may react to hesitation, realization, or confusion during user input, but the assistant should answer from the final normalized user intent.

## Core Rule

```text
Partial STT = listening reactions only
Final STT = answer generation
```

Do not generate multiple LLM answers for every filler phrase.

## VAD And EoT Goal

VAD and EoT are part of the latency goal, but they are not first-step requirements.

Definitions:

- VAD: Voice Activity Detection. Detect whether the user is speaking, silent, or only making noise.
- EoT: End of Turn. Decide when the user has actually finished speaking and the answer pipeline should start.

MVP direction:

```text
Push-to-talk STT first
-> record STT / LLM / TTS / visible reaction latency
-> add VAD for automatic listening start/stop
-> add EoT for natural turn-taking
-> add interruption / barge-in only after the basic loop is stable
```

Why this order:

- VAD/EoT improves perceived latency only if the downstream LLM/TTS loop is already measured.
- Bad EoT is worse than no EoT because it starts answering while the user is still speaking.
- Push-to-talk creates a clean baseline for measuring ASR-to-character latency.

Target signals to record later:

- speech_start_detected_at
- speech_end_detected_at
- final_stt_ready_at
- eot_decision_at
- silence_duration_ms
- stt_confidence

Example input:

```text
음... 어.. 아! 맞다 그거였지 그 뭐야 그 덤블링! 그거 어떻게 하는거야?
```

Runtime reaction:

```text
음...       -> thinking expression, gaze down
어..        -> uncertain expression, small head tilt
아!         -> realization / surprised expression
그 뭐야     -> searching / thinking expression
어떻게 하는거야? -> curious / attentive expression
```

Final answer target:

```text
덤블링 어떻게 하는거야?
```

## Input Reaction Timeline Contract

MVP shape:

```json
{
  "utteranceId": "input_001",
  "source": "stt_partial",
  "events": [
    {
      "start": 0.0,
      "duration": 0.8,
      "trigger": "filler",
      "text": "음...",
      "facePreset": "Thinking",
      "intensity": 0.45,
      "gaze": "down_left",
      "headMotion": "small_tilt"
    },
    {
      "start": 1.1,
      "duration": 0.4,
      "trigger": "realization",
      "text": "아!",
      "facePreset": "Surprised",
      "intensity": 0.6,
      "gaze": "user",
      "headMotion": "snap_attention"
    }
  ],
  "finalUserText": "덤블링 어떻게 하는거야?"
}
```

This timeline should not include TTS audio or visemes. It is a listening-state animation timeline.

## Trigger Mapping

| Input signal | Reaction | Face preset | Gaze | Head motion |
|---|---|---|---|---|
| `음`, `음...`, long pause | User is thinking | `Thinking` | `down_left` | `small_tilt` |
| `어`, `어...`, `그 뭐야` | Searching for words | `Uncertain` | `side` | `small_tilt` |
| `아!`, `맞다` | Realization | `Surprised` or `Curious` | `user` | `snap_attention` |
| Repeated correction | Following user clarification | `Listening` | `user` | `small_nod` |
| Question ending | Ready to answer | `Curious` | `user` | `small_nod` |

## Planner Responsibility

The Input Reaction Planner should be deterministic and lightweight for MVP.

Recommended MVP inputs:

- STT partial text
- final STT text
- partial timestamp
- silence duration
- confidence if available

Recommended MVP outputs:

- face preset
- intensity
- gaze target
- head motion
- optional short listening gesture

Avoid sending every partial transcript to the main LLM. Rule-based mapping is enough for first implementation, with a small local classifier as a later option.

## Text Cleanup

The final STT text should be normalized before answer generation.

```text
Raw:
음... 어.. 아! 맞다 그거였지 그 뭐야 그 덤블링! 그거 어떻게 하는거야?

Normalized:
덤블링 어떻게 하는거야?
```

Cleanup rules:

- remove filler words that do not change intent
- preserve corrected keywords
- preserve the final question form
- keep domain words even if they appear after hesitation
- keep uncertainty if it changes the request

## Runtime Layering

Input reactions use only listening layers:

- Face Preset Layer
- Gaze Layer
- Blink / Idle Layer
- Head Motion Layer
- optional short listening gesture

Input reactions should not use:

- TTS
- viseme timeline
- answer gesture timeline
- full-body generated motion

## MVP Scope

Phase 1:

- detect filler / pause / realization keywords
- play facial presets while user speaks
- normalize final STT text for LLM answer

Phase 2:

- add STT confidence and silence duration
- add language-specific filler dictionaries
- add user interruption handling

Phase 3:

- add small local intent/reaction classifier if rule-based mapping becomes too limited
- synchronize with streaming STT providers
