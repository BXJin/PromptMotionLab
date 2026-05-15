# Face Preset Roadmap

Updated: 2026-05-15

## Purpose

This document defines the face preset expansion plan.

It does not duplicate `CHARACTER-MORPH-TARGET-CATALOG.md`.

Use the morph catalog as the low-level morph source.
Use this document as the product-facing preset plan.

## Core Principle

Face presets should express conversation state, not real internal emotion.

Correct framing:

```text
The character visualizes answer state, confidence, and interaction mode.
It does not express real internal emotion.
```

Do not start with too many presets. More presets can make the character look unstable if the transitions, lip-sync conflict rules, and CharacterProfile multipliers are not tuned yet.

For the MVP, the expression library should support both conversation-state expressions and basic human emotion commands.

Examples:

```text
"make a sad face" -> sad
"look surprised" -> surprised
"show an angry expression" -> angry
"make a scared face" -> fearful
```

## Stage 1 - MVP Minimum

Create these first:

```text
neutral
friendly
thinking
uncertain
explaining
concerned
```

Why these six:

- `neutral`: default resting face
- `friendly`: general positive response and greeting
- `thinking`: answer generation / waiting state
- `uncertain`: low confidence answer
- `explaining`: object or exhibit explanation
- `concerned`: careful guidance or mild warning

This is enough to prove:

```text
Behavior JSON -> face preset -> morph blend
```

## Stage 2 - Basic Emotion Expansion

Add the basic emotion presets needed for prompt-driven expression tests:

```text
sad
surprised
angry
fearful
disgusted
confused
serious
apologetic
```

These presets let the MVP respond to explicit expression commands, not only guide-style answers.

| Preset | Use Case |
|---|---|
| `sad` | explicit sad expression, disappointing result, negative information |
| `surprised` | explicit surprise expression, unexpected question, interesting fact |
| `angry` | explicit angry expression command |
| `fearful` | explicit scared/fearful expression command |
| `disgusted` | explicit disgusted expression command |
| `confused` | ambiguous request, needs clarification |
| `serious` | warning, safety, policy, restricted topic |
| `apologetic` | unknown answer, error, refusal, sorry state |

## Stage 3 - Product Candidate

If Stage 1 and Stage 2 are stable, the practical product preset count is around 12-16:

```text
neutral
listening
friendly
happy
sad
angry
fearful
disgusted
surprised
thinking
explaining
curious
uncertain
concerned
confused
serious
apologetic
```

Do not expand beyond this until:

- face blending is stable
- lip-sync and expression mouth controls do not fight
- gaze and head motion layers are stable
- CharacterProfile multipliers work
- transitions look good on the actual character mesh

## Preset Selection Policy

The server does not need to choose every final face preset directly.

Recommended runtime mapping:

```text
emotion + intent + confidence -> FacePresetResolver -> facePreset
```

Examples:

| Runtime State | Face Preset |
|---|---|
| `emotion=friendly`, `intent=greet` | `friendly` |
| `emotion=friendly`, `intent=explain`, high confidence | `explaining` |
| `emotion=uncertain`, low confidence | `uncertain` |
| `intent=clarify` | `confused` or `thinking` |
| `intent=refuse` | `apologetic` or `serious` |
| safety or warning response | `serious` |
| unexpected user question | `surprised` then `thinking` |

This keeps Behavior JSON compact and lets Unreal choose character-specific expression details.

## Expression Mode Policy

For the MVP, do not block basic emotions.

The expression library should support:

```text
happy
sad
surprised
angry
disgusted
fearful
```

The important distinction is not "allowed vs blocked".
The distinction is:

```text
Conversation state:
  the system chooses an expression based on answer intent, confidence, and context.

Explicit expression command:
  the user asks the character to perform a specific facial expression.
```

Later B2B deployment can add policy controls if needed, but the MVP should first prove that the character can express the common emotion set.

## Basic Emotion Coverage

The expression library should eventually cover the common base emotions:

| Basic Emotion | Preset |
|---|---|
| neutral | `neutral` |
| happiness | `happy`, `friendly` |
| sadness | `sad` |
| surprise | `surprised` |
| anger | `angry` |
| fear | `fearful` |
| disgust | `disgusted` |

## Initial Morph Direction

Detailed morph values should live in Unreal DataAssets or DataTables.

High-level direction:

| Preset | Main Morph Families |
|---|---|
| `sad` | inner brow raise, slight brow drop, mild mouth frown |
| `surprised` | brow outer raise, eye wide, small jaw open |
| `confused` | asymmetric brow raise/compress, slight squint, small tilt |
| `serious` | brow compress/drop, reduced smile, stable gaze |
| `apologetic` | inner brow raise, mild frown, gaze down-left, low intensity |
| `angry` | brow compress/drop, eye squint, mouth tighten |
| `fearful` | inner brow raise, eye wide, mouth stretch |
| `disgusted` | nose sneer/crease, upper lip raise, slight squint |

Keep mouth expression mild because lip-sync will later own jaw and viseme morphs.
