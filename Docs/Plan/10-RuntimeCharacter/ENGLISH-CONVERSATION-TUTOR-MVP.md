# Conversation Mode MVP

## Product Goal

The runtime should not be hardcoded as an English tutor.

The client should select a conversation mode and the runtime should map that mode to a server-side `characterId`.

Initial modes:

| Client mode | characterId | Purpose |
| --- | --- | --- |
| Casual | `default_girl` | everyday conversation |
| English Tutor | `default_english_tutor` | beginner English conversation practice |
| Guide | `default_guide` | exhibit/showroom guide |

English Tutor is one selectable mode, not the default product identity.

## English Tutor Behavior

The character should:

- speak simple, natural English
- keep turns short enough for STT/TTS conversation
- react immediately with facial expression before the LLM final reply arrives
- provide small feedback when the learner makes a clear mistake
- remember enough recent turns to continue the same conversation naturally

## Current Implementation Status

Implemented:

- client-side conversation mode enum
- mode-to-`characterId` mapping in Unreal
- `default_english_tutor` CharacterProfile
- session-based recent conversation memory
- configurable session memory length through `RUNTIME_MAX_SESSION_TURNS`
- WebSocket `reaction` then `final` flow
- local thinking face reaction while waiting for server response
- HTTP fallback when WebSocket connection fails
- latency CSV logging on server and Unreal client

Not implemented yet:

- STT input
- VAD / end-of-turn detection
- TTS audio playback
- viseme timeline lip-sync
- grammar feedback as a separate structured field
- long-term persisted learner memory

## Conversation Policy

The LLM should follow this behavior for the English tutor profile:

- answer first in beginner-friendly English
- keep each reply short
- ask a natural follow-up question often enough to keep conversation moving
- correct only obvious learner mistakes
- give one tiny Korean correction when helpful
- avoid long grammar lectures during spoken conversation

Good:

```text
That sounds fun. What kind of music do you like?
Tip: "I like listen music"보다 "I like listening to music"가 자연스러워요.
```

Bad:

```text
Your sentence contains a gerund usage error. Here is a full explanation of gerunds, infinitives, and verb patterns...
```

## Memory Policy

The runtime keeps recent conversation turns by `sessionId`.

Default:

```text
RUNTIME_MAX_SESSION_TURNS=40
```

This is enough for a short practice session, but it is still not long-term memory.

Future long-term learner memory should be separate from short-term turn memory:

- learner level
- recurring grammar mistakes
- preferred topics
- recent vocabulary
- session summaries

Do not put long-term memory directly into every LLM prompt as raw chat history. Summarize it first, otherwise latency and token cost will grow.

## Realtime Interaction Policy

For conversation quality, the runtime should not wait for the final LLM response before reacting.

Target flow:

```text
User speaks
-> VAD/EoT detects the turn end
-> Unreal immediately shows listening/thinking expression
-> WebSocket sends reaction
-> LLM returns final reply + behavior
-> TTS starts
-> viseme timeline drives lip-sync
```

Current text-only flow:

```text
User sends text
-> Unreal immediately applies thinking expression
-> WebSocket queues if not connected
-> server sends reaction
-> server sends final reply
-> Unreal applies final face preset
```

## Cold Assessment

The design is partially ready for an English tutor, but not complete.

Ready enough for text-based prototype:

- short-term memory
- behavior JSON
- low-latency visible reaction
- WebSocket reaction/final architecture

Not ready for true spoken tutor:

- no STT yet
- no TTS playback yet
- no lip-sync timeline yet
- no VAD/EoT, so turn-taking cannot feel natural yet

The next serious milestone should be TTS + lip-sync if visual speaking quality matters most, or STT + VAD/EoT if hands-free conversation quality matters most.
