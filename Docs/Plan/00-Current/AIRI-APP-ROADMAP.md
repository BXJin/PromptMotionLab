# Airi App Roadmap

Updated: 2026-05-27

This document summarizes what is already done, what must be finished before APK testing, and what should be added later if Airi grows from a portfolio demo into a commercial AI character app.

## Current Product Shape

Airi is a realtime 3D AI character app:

```text
voice input
-> STT
-> LLM behavior planning
-> Behavior JSON
-> Unreal facial expression / gesture / gaze
-> TTS + viseme lip sync
```

The first release target is not a full commercial companion platform. The target is a stable Android demo that proves the realtime voice-to-character pipeline.

## Already Done

| Area | Status |
|---|---|
| FastAPI production server | Deployed to Azure App Service |
| Production endpoint config | UE profile points to Azure production URL |
| STT | Batch STT and streaming STT implemented |
| TTS | Azure TTS with segmented playback |
| Lip sync | Azure viseme timeline, WAV trim, sequential segment playback |
| Character behavior | Behavior JSON with emotion, intent, gaze, gesture, tts style |
| Character profiles | Multiple profile presets exist |
| Short-term memory | Session-based recent conversation memory exists |
| Basic event/scenario layer | Small scenario hint layer exists |
| Security basics | Docs disabled, input validation, rate limit, log redaction |
| Cost guard | Azure monthly 10 USD budget alerts at 50/80/100% |
| Android basics | Portrait orientation, RECORD_AUDIO permission |
| Mobile cleanup | Default virtual joystick disabled, four-finger console disabled |

## Before APK Test

These are required before spending time on Play Store setup.

| Priority | Task | Why |
|---|---|---|
| P0 | Package Android APK/AAB | Confirms the project can actually build for device |
| P0 | Test on real Android device | PIE success does not prove Android mic/WebSocket/audio works |
| P0 | Confirm production URL in device logs | Avoid accidentally shipping localhost |
| P0 | Confirm microphone permission prompt | Required for STT |
| P0 | Confirm no virtual joystick overlay | App should not look like an unfinished UE template |
| P0 | Confirm TTS/lip sync playback | Core product value |
| P1 | Add loading overlay | Hide level load delay and avoid a blank/unfinished first impression |
| P1 | Add Android back/exit handling | Needed for app-like UX |
| P1 | Test 10-20 minute continuous session | Catch crashes, memory pressure, audio failures |

Recommended loading behavior:

```text
show loading overlay on launch
minimum display: 1.5-2.0s
maximum display: 10s
close when level/runtime/UI are ready
fallback close after max wait with status message
```

No separate Start button is required. The mic button is the real interaction trigger.

## Before Play Store Internal Test

| Area | Required Work |
|---|---|
| Store listing | App name, icon, screenshots, short/long description |
| Privacy | Privacy policy URL |
| Data Safety | Declare audio/microphone, network transfer, AI processing |
| AI disclosure | Explain that responses are AI-generated and may be inaccurate |
| Safety UX | Add at least a simple feedback/report path for bad AI responses |
| Build config | Release signing, debuggable off, production endpoint |
| Stability | Real-device smoke script/checklist passed |

Recommended Play Store positioning:

```text
Airi
Realtime 3D AI Character
Talk with an expressive 3D AI character using your voice.
```

Avoid:

```text
AI girl
girlfriend
dating
romance
flirty
relationship
```

The character currently looks young, so the product should be positioned as a voice-driven 3D AI character, not a romance or companion-girl app.

## Commercial Expansion Later

These are not required before the first APK, but they are the right expansion path if Airi becomes a real service.

### 1. Airi CharacterProfile

Purpose:

- Reduce "AI assistant / guide" tone.
- Make Airi sound like a consistent character.
- Keep replies short, warm, and conversational.

Add:

- personality summary
- speech style
- forbidden tone
- response length rules
- example dialogues
- emotion/gesture tendencies

### 2. Response Evaluation Set

Purpose:

- Test if Airi responds like Airi.
- Catch regressions after prompt/model changes.
- Compare prompt changes and fine-tuning results.

Example categories:

- greeting
- sadness/comfort
- compliments
- jokes/teasing
- memory questions
- games/movies/hobbies
- unsafe requests
- STT misrecognition recovery

This does not improve responses by itself. It is a test set used to measure whether prompt, planner, memory, or fine-tuning changes helped.

### 3. Persistent CharacterState

Purpose:

- Store per-user character state across sessions.

Example:

```json
{
  "userId": "device_or_account_id",
  "characterId": "airi",
  "mood": "warm",
  "closeness": 12,
  "trust": 5,
  "lastTopic": "movie",
  "updatedAt": "..."
}
```

Recommended storage path:

| Stage | Storage |
|---|---|
| APK demo | in-memory session only |
| Closed beta | server SQLite or PostgreSQL |
| Public service | PostgreSQL + authenticated user/device ID |

### 4. Long-Term Memory

Purpose:

- Remember important user facts without storing every raw conversation forever.

Recommended approach:

```text
conversation turn
-> memory extraction
-> save important memory item
-> retrieve relevant memory on future turns
-> include retrieved memory in prompt
```

Do not store every raw conversation turn by default. It increases privacy risk and prompt cost.

Preferred memory item:

```json
{
  "type": "event",
  "text": "The user watched Avengers: Endgame at CGV.",
  "importance": 0.5,
  "topics": ["movie", "daily_life"],
  "createdAt": "..."
}
```

### 5. Memory Retrieval / RAG

Start simple:

```text
keyword + recency + importance
```

Then upgrade later:

```text
PostgreSQL + pgvector
or
dedicated vector DB
or
OpenAI vector store for static lore/docs
```

Use cases:

- user memory retrieval
- Airi lorebook retrieval
- character/world facts

OpenAI vector stores/file search are useful for relatively stable knowledge. Frequently changing per-user memory is often easier to control in the app database first.

### 6. Fine-Tuning

Use only after prompt/profile/memory work is not enough.

Good use cases:

- JSON output stability
- shorter character-chat style
- less "AI guide" tone
- consistent Airi response rhythm

Recommended approach:

```text
one Airi fine-tuned model
+ personalityMode in prompt/state
```

Avoid creating one fine-tuned model per personality mode at first. It multiplies training, testing, routing, and maintenance cost.

## Recommended Order

```text
1. APK build and real-device stability
2. Loading overlay + exit UX
3. Play Store internal test requirements
4. Airi CharacterProfile cleanup
5. Airi response evaluation set
6. Persistent CharacterState
7. Memory extraction + memory store
8. Memory retrieval/RAG
9. Fine-tuning only if still needed
```

## Current Decision

For the first Android APK:

```text
Do not add long-term RAG, DB, or fine-tuning yet.
Focus on packaging, device stability, loading UX, and Play Store readiness.
```

For the commercial service path:

```text
Add Airi profile and eval first, then persistent state and memory, then RAG, then fine-tuning.
```
