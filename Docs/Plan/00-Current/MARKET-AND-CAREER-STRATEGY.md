# Market And Career Strategy

Updated: 2026-05-14

## Purpose

This note keeps the market analysis separate from the startup application draft.

Use it for:

- startup grant/application positioning
- competitor analysis
- future job applications to related AI avatar, digital human, game AI, and spatial computing companies
- interview talking points

## Short Conclusion

The market already exists. That is good.

PromptMotionLab should not claim:

```text
No one is building AI characters.
```

The safer claim is:

```text
Conversational AI avatar and digital human companies already exist.
PromptMotionLab focuses on a narrower runtime layer: converting LLM response state into controllable character behavior, starting with Unreal-based spatial AI agents.
```

## Market Signal

The market is moving in several directions at the same time:

- real-time video digital humans
- AI avatar SDKs for web/app/kiosk
- game NPC AI platforms
- browser/VRM 3D avatar engines
- virtual idol and digital artist experiences
- spatial exhibitions, showrooms, education spaces, and digital twins

This means the idea is not isolated. Companies are already spending money on conversational characters, digital humans, and avatar agents.

The important point is not "there are no competitors." The important point is:

```text
The market confirms demand, but many products are still split by renderer, deployment channel, or use case.
```

## Spatial AI Agent Framing

The strongest direction for PromptMotionLab is not a generic talking head.

The stronger framing is:

```text
An Unreal-based spatial AI agent runtime for exhibitions, brand showrooms, education spaces, and virtual worlds.
```

In this model, the AI character is not just a face on a screen. It exists inside a 3D space and can react to:

- where the user is
- what object or exhibit the user is looking at
- what the user selected
- what the character should point at
- whether the answer is confident or uncertain
- what tone the guide should use
- what persona and behavior policy the venue wants

This is the reason Unreal remains a valid first renderer.

If the product were only a webcam-style talking face, Unreal would be too heavy. For a spatial guide, showroom assistant, virtual world NPC, or open-world helper, a game engine is a reasonable technical foundation.

## Competitor Categories

| Category | Examples | Strength | Weakness / Gap |
|---|---|---|---|
| Video digital humans | Klleon, DeepBrain AI, ESTsoft, D-ID, Tavus, Beyond Presence | face realism, web/video deployment, fast demos | often screen-face oriented, limited spatial staging |
| Browser/VRM avatar engines | GoodGang Labs and similar engines | lightweight, web/mobile friendly, fast deployment | less suited for high-end Unreal scenes and spatial installations |
| Game NPC AI platforms | Convai, Inworld AI | strong game-engine NPC integration | usually game developer focused, not exhibition/showroom operation first |
| Enterprise digital people | Soul Machines and similar platforms | mature enterprise story, digital human quality | expensive, platform-bound, less controllable as a custom runtime layer |
| Metaverse/spatial avatar tools | Pixel Canvas, Metastar, Determinant AI, Spatial Agents, Tridot | spatial or 3D avatar direction | fragmented between platform, SDK, event solution, or custom project |

## Positioning Against Competitors

PromptMotionLab should avoid competing on the wrong axis.

Do not compete mainly on:

- most realistic human face
- fastest video avatar
- first AI digital human
- fully human-like emotional AI
- fully generated motion in MVP

Compete on:

- Behavior JSON as a controllable behavior layer
- Unreal-first spatial AI character runtime
- object-aware gaze, pointing, and guide behavior
- CharacterProfile for persona, expression strength, gaze style, forbidden topics, and guide policy
- renderer-agnostic expansion later: Unreal first, then video avatar, web/VRM, MetaHuman, Live2D, or mobile renderers

## Behavior JSON Position

Most avatar systems can be described as:

```text
LLM / STT / TTS -> avatar renderer
```

PromptMotionLab should be described as:

```text
LLM / RAG / memory
-> Behavior Planner
-> Behavior JSON + Speech Timeline
-> Renderer Adapter
-> Unreal spatial AI character first
```

The product value is not only the character asset. It is the control layer that decides:

- answer text
- emotional tone
- confidence
- gaze target
- gesture key
- TTS style
- safety state
- interaction mode

This is also why the same JSON can later drive other renderers.

## Startup Application Angle

For startup support, the message should be:

```text
We are building a runtime system that turns AI answer state into visible character behavior.
The first MVP proves this with an Unreal-based spatial AI guide for exhibitions, showrooms, and education spaces.
```

Use careful language:

- AI does not feel emotion.
- The system estimates conversational tone, intent, confidence, and state.
- The character expresses those signals through facial presets, gaze, lip-sync, short gestures, and voice style.
- "Human-like" should be replaced with "more responsive, understandable, and believable than a text or voice-only chatbot."

## Job Application Angle

For future applications to related companies, this project can be positioned as practical experience across three areas.

### AI Avatar / Digital Human Companies

Relevant strengths:

- LLM response structuring
- avatar behavior design
- TTS and lip-sync timeline design
- expression policy and safety-aware wording
- competitor understanding of video avatars and digital humans

Resume-friendly wording:

```text
Designed a Behavior JSON pipeline that maps LLM response intent, confidence, and emotional tone into avatar facial expression, gaze, lip-sync, and gesture commands.
```

### Game AI / Unreal Companies

Relevant strengths:

- Unreal runtime character control
- Control Rig / Animation Blueprint direction
- spatial NPC interaction design
- object-aware guide behavior
- separation between AI reasoning and runtime execution

Resume-friendly wording:

```text
Designed an Unreal-first spatial AI agent architecture where LLM output is converted into runtime-safe character behavior through preset facial expressions, gaze control, lip-sync timing, and gesture keys.
```

### Spatial Computing / Exhibition / Digital Twin Companies

Relevant strengths:

- kiosk and exhibition use case understanding
- mobile companion app possibility
- QR/session-based interaction
- local Unreal rendering plus cloud AI services
- spatial guide and object explanation flow

Resume-friendly wording:

```text
Planned a spatial AI guide system for exhibitions and showrooms, combining 3D scene context, conversational AI, and real-time character behavior control.
```

## MVP Does Not Change

The current MVP should still start with Unreal.

MVP scope:

- one small 3D space
- one AI character
- text or voice input
- RAG or fixed knowledge base
- Behavior JSON
- Speech Timeline
- facial expression presets
- gaze, blink, head motion
- TTS and lip-sync
- short gesture keys
- simple object-aware explanation

Do not put text-to-motion into the first runtime MVP.

Later expansion:

- CC4/CC5 character customization
- MetaHuman adapter
- video avatar adapter
- web/VRM adapter
- mobile companion app
- Pixel Streaming or native mobile Unreal exploration
- text-to-motion as offline gesture authoring

## Useful One-Line Positioning

For startup application:

```text
PromptMotionLab is a Behavior JSON-based AI character runtime that makes an Unreal 3D agent respond with facial expression, gaze, lip-sync, and gestures inside spatial environments such as exhibitions, showrooms, and education spaces.
```

For job applications:

```text
I built and researched an AI avatar runtime architecture that connects LLM response state to real-time character behavior across Unreal, TTS/lip-sync, facial presets, and future multi-renderer adapters.
```

For competitor comparison:

```text
Existing digital human services prove market demand; PromptMotionLab differentiates by focusing on a controllable spatial character runtime rather than only a realistic talking-face avatar.
```

