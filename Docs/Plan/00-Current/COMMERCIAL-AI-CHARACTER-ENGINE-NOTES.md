# Commercial AI Character Engine Notes

Updated: 2026-05-27

This document summarizes the common engine layers behind commercial AI character chat products and evaluates whether each layer is useful for PromptMotionLab.

The goal is not to copy a subscription character-chat app. PromptMotionLab is currently positioned as a real-time Unreal character system for short exhibition/mobile sessions. The useful commercial ideas are the ones that improve short-session impact without damaging latency.

## Product Context Difference

| Area | Commercial Character Chat App | PromptMotionLab Current Target |
|---|---|---|
| Session length | Days to months | 3-10 minutes |
| Main business goal | Retention and subscription | Immediate demo impact and technical proof |
| User return rate | Core product loop | Uncertain or low |
| Relationship progression | Important | Usually not meaningful |
| Latency tolerance | Higher, especially for text chat | Low; voice response should feel immediate |
| Differentiator | Emotional continuity and attachment | UE5 avatar, voice, expression, lip sync, low-latency pipeline |

The key implication:

```text
Do not overbuild long-term retention systems before the real-time avatar loop is stable.
```

## Baseline Engine Layers

PromptMotionLab already has most of the baseline runtime engine:

```text
Character profile
-> short session memory
-> state machine / voice status
-> response planner
-> style control
-> safety guard
-> Behavior JSON
-> Speech Timeline
-> Unreal expression / gesture / lip-sync execution
```

These layers are enough to support a convincing short-session AI character if they are reliable, low-latency, and visually expressive.

## Commercial Layers

### 1. Relationship / Affinity System

What commercial apps use it for:

- Closeness, trust, affection, distance, jealousy, interest, relationship level.
- User returns over days or weeks and sees relationship progression.
- The product creates a sense that the character remembers and values the user.

Example state:

```json
{
  "closeness": 42,
  "trust": 31,
  "tone": "slightly_warmer",
  "relationshipStage": "familiar"
}
```

PromptMotionLab judgment:

- Not needed for the current exhibition/mobile MVP.
- A visitor will not stay long enough for relationship progression to matter.
- If implemented now, it adds product confusion and persistence/privacy concerns.

Decision:

```text
Defer.
```

Possible later use:

- If PromptMotionLab becomes a daily companion app, add a small relationship state.
- If used, keep it explicit and inspectable rather than hidden emotional manipulation.

### 2. Daily Life / Autonomous Character Simulation

What commercial apps use it for:

- The character appears to have a life when the user is away.
- Examples:
  - "I listened to the song you mentioned yesterday."
  - "I just came back from a walk."
  - "I was thinking about what you said."

Why it works commercially:

- It supports retention.
- It makes the character feel persistent beyond the current chat window.

PromptMotionLab judgment:

- Not useful for a short exhibition flow.
- Can feel fake or distracting if the user has no prior relationship with the character.
- Requires time simulation, memory, and consistency rules.

Decision:

```text
Defer.
```

Possible later use:

- Add only if there is a daily-return product loop.
- For exhibitions, use scenario-specific idle lines instead of full daily-life simulation.

### 3. Event / Scenario System

What commercial apps use it for:

- Trigger special dialogue or scenes under specific conditions.
- Examples:
  - 3 consecutive days of use.
  - High affinity.
  - Night-time login.
  - User repeatedly expresses sadness.
  - Birthday or anniversary.

PromptMotionLab judgment:

- This is the most useful commercial layer for the current project.
- It works even in short sessions.
- It can make the character feel context-aware without requiring long-term retention.
- It maps naturally to Unreal expression, gesture, camera, and TTS style changes.

Recommended MVP shape:

```json
{
  "id": "comfort_repeated_sadness",
  "priority": 80,
  "cooldownSeconds": 120,
  "conditions": {
    "keywords": ["sad", "tired", "lonely"],
    "minMatchesInSession": 2
  },
  "responseHint": "Acknowledge the repeated emotional theme and offer gentle support.",
  "behaviorOverride": {
    "emotion": "concerned",
    "gestureKey": "small_ack",
    "ttsStyle": "careful"
  }
}
```

Decision:

```text
Adopt, but keep it small.
```

Good exhibition scenarios:

- First greeting.
- Repeated sadness / comfort mode.
- User asks about the character.
- User asks about a specific exhibit.
- User repeats the same topic.
- Closing-time or night-time tone.
- No-speech timeout / idle prompt.

### 4. Lorebook / World Info

What commercial apps use it for:

- Larger setting database beyond the character card.
- Contains places, people, past events, world rules, speech rules, and roleplay facts.
- Relevant entries are retrieved and inserted into the prompt.

PromptMotionLab judgment:

- This already exists conceptually through knowledge/RAG layers.
- For the current project, lorebook should mean curated exhibit/world/character facts, not unlimited roleplay lore.

Decision:

```text
Already covered in principle. Improve retrieval quality later if needed.
```

Recommended rule:

- Keep retrieved context compact.
- Prefer facts that affect the current answer.
- Do not dump full character lore into every prompt.

### 5. Dialogue Act Planner

What commercial apps use it for:

- The system plans the conversational act before generating the final reply.
- This moves the product from "answer machine" to "character interaction."

Example:

```json
{
  "act": "tease",
  "emotion": "playful",
  "relationshipMove": "increase_closeness",
  "topicStrategy": "ask_followup"
}
```

PromptMotionLab judgment:

- Already partially implemented through `BehaviorJson`.
- Current fields such as `intent`, `emotion`, `gaze`, `gestureKey`, `headMotion`, `ttsStyle`, and `confidence` are the core of a dialogue-act planner.

Decision:

```text
Do not build a separate planner yet. Strengthen BehaviorJson usage first.
```

Future improvement:

- Add a small `dialogueAct` field only if current `intent` becomes too coarse.
- Keep it compact to avoid extra latency and prompt complexity.

### 6. Memory Extraction / Memory Ranking

What commercial apps use it for:

- Extract durable facts from conversation.
- Rank memory by importance, recency, emotional intensity, and relevance.

Examples:

- "The user dislikes horror games."
- "The user is preparing for an interview."
- "The user prefers playful replies."

PromptMotionLab judgment:

- Valuable for daily companion products.
- Overkill for a short exhibition MVP.
- Adds privacy and retention obligations.

Decision:

```text
Defer long-term memory.
Keep short session memory only.
```

Current acceptable version:

- Keep recent turns in memory for session continuity.
- Do not persist personal facts by default.
- If persistent memory is added later, make retention and deletion explicit.

### 7. User Modeling

What commercial apps use it for:

- Build a per-user preference model.
- Same character responds differently to each user.

Example:

```json
{
  "preferredTone": "casual",
  "likes": ["anime", "comforting replies"],
  "sensitiveTopics": ["family"],
  "conversationPace": "short"
}
```

PromptMotionLab judgment:

- Not useful unless the same user returns repeatedly.
- Creates privacy obligations.
- Hard to validate in a short demo.

Decision:

```text
Defer.
```

Short-session substitute:

- Infer only temporary session preferences.
- Example: if the user asks for short answers, keep replies shorter for that session.

### 8. Response Reranking / Regeneration

What commercial apps use it for:

- Generate or validate multiple candidates.
- Check:
  - character consistency
  - length
  - contradiction
  - safety
  - emotional tone

PromptMotionLab judgment:

- Useful for quality, bad for latency.
- Current voice UX depends on fast first audio.
- Full reranking is not a good MVP tradeoff.

Decision:

```text
Do not add full reranking now.
Use lightweight validation only.
```

Recommended substitute:

- Validate the Behavior JSON schema.
- Keep response length constrained in the prompt.
- Add deterministic safety guards for high-risk topics.
- Use fallback only when provider output is invalid.

### 9. Voice / Avatar / Multimodal Embodiment

What commercial apps use it for:

- Voice synthesis, image generation, animated avatars, and richer presence.

PromptMotionLab judgment:

- This is the project's strongest differentiator.
- Unreal expression, gaze, gesture, segmented TTS, and lip sync matter more than deep relationship mechanics for the current product.

Decision:

```text
Invest here first.
```

Current strength:

- UE runtime avatar control.
- STT input.
- Async turn pipeline.
- Segmented TTS.
- Azure viseme-based lip sync.
- Expression/gesture Behavior JSON.
- Latency measurement.

## Adopt / Defer Matrix

| Layer | Value For PromptMotionLab | Decision |
|---|---:|---|
| Character profile | High | Keep improving |
| Short session memory | High | Keep |
| State machine | High | Keep |
| Response planner | High | Keep |
| Style control | High | Keep |
| Safety guard | High | Improve before public release |
| Event / Scenario system | High | Adopt next, small scope |
| Lorebook / world info | Medium | Already covered by RAG/knowledge layer |
| Dialogue act planner | Medium | Covered by BehaviorJson for now |
| Voice/avatar embodiment | Very high | Core differentiator |
| Relationship / affinity | Low for MVP | Defer |
| Daily life simulation | Low for MVP | Defer |
| Long-term memory extraction | Low for MVP | Defer |
| User modeling | Low for MVP | Defer |
| Response reranking | Medium quality, high latency cost | Defer full version |

## Recommended Next Product Layer

The next character-engine feature should be:

```text
Small Event / Scenario System
```

Minimum implementation:

```text
Scenario definitions
-> trigger matching
-> cooldown
-> responseHint injection
-> BehaviorJson override
-> latency-safe logging
```

It should not include:

- persistent affection points
- daily-life simulation
- long-term personal memory
- multi-candidate regeneration
- heavy vector memory

Current MVP implementation:

```text
RuntimeScenarioService
-> detect repeated emotional disclosure inside the current session
-> detect focused-object explanation requests
-> inject compact scenarioHint into the provider input
-> apply small BehaviorJson overrides after provider response
```

This keeps the scenario layer latency-safe. It does not call another model, does not persist long-term user state, and does not block the existing turn/async flow.

## Why This Direction Fits The Portfolio

For portfolio positioning, the strongest claim is not:

```text
"I made another AI companion app."
```

The stronger claim is:

```text
"I designed a latency-aware real-time AI character runtime that connects LLM intent, TTS, viseme timing, expression presets, gesture keys, and Unreal execution."
```

Commercial character-chat systems are useful as reference, but the project should stay focused on embodied real-time interaction.

## Final Decision

For the current MVP:

```text
Implement: scenario/event layer.
Keep: profile, session memory, BehaviorJson planner, style control, safety guard, voice/avatar pipeline.
Defer: relationship, daily life, long-term memory, user modeling, full reranking.
```

This keeps the project differentiated without turning it into a retention-heavy character-chat product.
