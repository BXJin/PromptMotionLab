# MVP Development Roadmap

Updated: 2026-05-15

## Goal

첫 MVP의 목표는 완성형 디지털휴먼이 아니다.

목표는 아래 흐름이 실제로 동작한다는 것을 증명하는 것이다.

```text
User text
-> FastAPI runtime server
-> reply + Behavior JSON
-> Unreal client receives JSON
-> character changes expression / gaze / head motion / short gesture
```

TTS, lip-sync, STT, RAG는 중요하지만 1차 구현의 핵심 증명은 아니다.

1차 구현에서 반드시 보여줘야 하는 것은:

```text
AI answer state -> structured behavior -> Unreal character reaction
```

## Development Rule

기존 서버를 버리지 않는다.

현재 `Server-Python`은 motion authoring 중심 구조다.

```text
prompt -> MotionSpec -> ProceduralGestureJson
```

MVP에서는 이 구조 옆에 runtime character API를 추가한다.

```text
message + scene context
-> RuntimeCharacterService
-> reply + Behavior JSON
```

즉 기존 motion generation API는 나중 `20-MotionAuthoring`용으로 유지하고, 새로운 runtime API를 병렬로 둔다.

## Phase 0 - Baseline Check

### Purpose

개발 시작 전 현재 서버와 Unreal 프로젝트가 깨지지 않았는지 확인한다.

### Commands

```powershell
cd Server-Python
python -m compileall app
python -m pytest
```

Unreal C++ 빌드:

```powershell
& "C:\Program Files\Epic Games\UE_5.7\Engine\Build\BatchFiles\Build.bat" PromptMotionClientEditor Win64 Development -Project="C:\Portfolio\PromptMotionLab\Client-Unreal\PromptMotionClient\PromptMotionClient.uproject" -WaitMutex -NoHotReload
```

### Success Criteria

- Python compile passes
- server tests pass
- Unreal module builds

## Phase 1 - Server Runtime API

### Purpose

Unreal이 호출할 수 있는 최소 런타임 응답 API를 만든다.

### New Endpoint

```text
POST /api/runtime/respond
```

### Request Shape

```json
{
  "sessionId": "demo_session",
  "characterId": "default_guide",
  "message": "이 전시물 설명해줘",
  "sceneContext": {
    "locationId": "demo_hall",
    "focusedObjectId": "exhibit_01",
    "nearbyObjectIds": ["exhibit_01", "exhibit_02"],
    "interactionMode": "object_selected"
  }
}
```

### Response Shape

```json
{
  "reply": "이 전시물은 AI 캐릭터가 공간 안에서 사용자와 상호작용하는 방식을 보여주는 데모입니다.",
  "behavior": {
    "emotion": "friendly",
    "intensity": 0.6,
    "confidence": 0.86,
    "intent": "explain",
    "gaze": "focused_object",
    "gestureKey": "explain_small",
    "headMotion": "small_nod",
    "ttsStyle": "warm"
  }
}
```

### Files To Add

```text
Server-Python/app/contracts/runtime_behavior.py
Server-Python/app/services/runtime_character_service.py
```

### Files To Update

```text
Server-Python/app/contracts/requests.py
Server-Python/app/contracts/responses.py
Server-Python/app/contracts/__init__.py
Server-Python/app/services/__init__.py
Server-Python/app/dependencies.py
Server-Python/app/api/routes.py
Server-Python/tests/test_api.py
```

### Implementation Detail

`runtime_behavior.py` defines small enum-like Literal types:

```text
emotion:
  neutral, friendly, happy, thinking, curious, concerned, uncertain, apologetic

intent:
  greet, explain, answer, clarify, refuse, fallback

gaze:
  user, focused_object, down_left, side, none

gestureKey:
  none, small_ack, explain_small, point_soft, hesitate, greet_small

headMotion:
  none, small_nod, small_tilt, thinking_tilt

ttsStyle:
  neutral, warm, careful, energetic
```

`RuntimeCharacterService` should not call a real LLM first.

First implementation should be deterministic:

```text
message contains "모르" or "확실" -> uncertain / careful / hesitate
message contains "설명" or focusedObjectId exists -> explain / focused_object / explain_small
message contains "안녕" -> friendly / user / greet_small
default -> friendly / user / small_ack
```

This gives stable tests and lets Unreal integration begin before provider work.

### Tests

Add tests for:

- `/api/runtime/respond` returns 200
- response has `reply`
- response has schema-valid `behavior`
- object-selected context returns `gaze = focused_object`
- uncertain message returns `emotion = uncertain` and lower confidence

### Success Criteria

- API works without external API key
- output is stable across repeated calls
- existing motion API tests still pass

## Phase 2 - Unreal HTTP Integration

### Purpose

Unreal에서 서버 응답을 받아오는 최소 네트워크 경로를 만든다.

이 단계에서는 캐릭터를 움직이지 않아도 된다.
먼저 JSON을 Unreal 로그와 Blueprint에서 확인할 수 있어야 한다.

### Unreal Modules

Recommended file split:

```text
Source/PromptMotionClient/Public/Runtime/PromptMotionRuntimeTypes.h
Source/PromptMotionClient/Public/Runtime/PromptMotionApiClient.h
Source/PromptMotionClient/Public/Runtime/PromptMotionRuntimeComponent.h

Source/PromptMotionClient/Private/Runtime/PromptMotionApiClient.cpp
Source/PromptMotionClient/Private/Runtime/PromptMotionRuntimeComponent.cpp
```

### Build.cs Update

Add Unreal modules:

```text
HTTP
Json
JsonUtilities
```

### Data Types

`PromptMotionRuntimeTypes.h` should define:

```text
FPromptMotionSceneContext
FPromptMotionBehavior
FPromptMotionRuntimeResponse
```

Keep fields close to server JSON:

```text
Emotion
Intensity
Confidence
Intent
Gaze
GestureKey
HeadMotion
TtsStyle
Reply
```

### Api Client

`UPromptMotionApiClient` or plain helper class should:

- build JSON request
- send HTTP POST to `http://127.0.0.1:8010/api/runtime/respond`
- parse response JSON
- return success/failure callback

### Runtime Component

`UPromptMotionRuntimeComponent` should:

- be attachable to an Actor or Character
- expose `SendRuntimeMessage(Message, FocusedObjectId)` to Blueprint
- store last reply and last behavior
- broadcast `OnRuntimeResponseReceived`

### Success Criteria

- pressing a test input in Unreal sends request to FastAPI
- Unreal log prints reply
- Unreal log prints behavior keys
- no character animation required yet

## Phase 3 - Behavior Preview Without Real Character

### Purpose

캐릭터 연결 전에 Behavior JSON이 Unreal 안에서 제대로 분기되는지 확인한다.

### Implementation

Add a simple debug executor:

```text
UPromptMotionDebugBehaviorExecutor
```

It receives `FPromptMotionBehavior` and prints:

```text
Emotion=friendly, Gaze=focused_object, Gesture=explain_small
```

Optional:

- change actor material color by emotion
- show reply in a debug widget
- draw a line toward focused object when `gaze = focused_object`

### Success Criteria

- server behavior changes are visible in Unreal debug output
- focused object context affects gaze/gesture
- uncertain prompt triggers uncertain behavior

## Phase 4 - Face Preset MVP

### Purpose

`child_test_2` 캐릭터의 facial morph를 직접 조작해 3~4개 표정만 먼저 연결한다.

### Initial Presets

Start with:

```text
neutral
friendly
thinking
uncertain
explaining
concerned
```

Do not start with all production presets. The first implementation should prove stable blending before adding subtle emotional variations.

Recommended expansion after the first preset path works:

```text
sad
surprised
confused
serious
apologetic
```

These are not for strong emotional acting. They are for conversation-state expression:

- `sad`: disappointing or negative result
- `surprised`: unexpected question or interesting fact
- `confused`: ambiguous user request
- `serious`: warning, policy, or safety guidance
- `apologetic`: unknown answer, error, or refusal

Avoid strong `angry`, `disgusted`, or `fearful` presets in the MVP because they are risky for B2B guide use cases and can make the character feel unstable.

### Unreal Structure

Recommended files:

```text
Public/Runtime/Face/PromptMotionFacePreset.h
Public/Runtime/Face/PromptMotionExpressionAdapter.h

Private/Runtime/Face/PromptMotionExpressionAdapter.cpp
```

### Implementation Detail

`UPromptMotionExpressionAdapter` should:

- reference the character skeletal mesh
- keep a table of preset name -> morph target weights
- interpolate current weights toward target weights
- apply intensity multiplier
- expose `ApplyEmotionPreset(Emotion, Intensity)`

Initial morph values can be rough.

The goal is not perfect face quality. The goal is proving:

```text
Behavior JSON emotion changes visible face preset
```

### Success Criteria

- friendly produces visible smile/soft face
- thinking produces brow/eye/mouth change
- uncertain produces different expression from thinking
- transition is blended, not snapping instantly

## Phase 5 - Gaze, Head, Blink

### Purpose

캐릭터가 답변 전에도 살아있는 것처럼 보이게 만든다.

### Layers

Add lightweight layers:

```text
Gaze:
  user, focused_object, down_left, side

Head:
  small_nod, small_tilt, thinking_tilt

Blink:
  idle random blink
```

### Implementation Direction

First implementation can be simple:

- gaze target as Actor reference or world location
- head motion as small additive rotation
- blink as morph target pulse

Control Rig can come later if needed.

### Success Criteria

- focused object behavior turns gaze toward object
- uncertain behavior can look down-left briefly
- idle blink continues while no answer is playing

## Phase 6 - Short Gesture Keys

### Purpose

LLM/Behavior JSON은 `gestureKey`만 선택하고, Unreal은 안정적인 gesture를 실행한다.

### Initial Gesture Keys

```text
small_ack
explain_small
hesitate
point_soft
```

### Implementation Direction

For first MVP, choose the fastest available method:

- existing animation montage if available
- Control Rig if already easy on the character
- temporary procedural upper-body rotation if no asset exists

Do not block MVP on perfect hand animation.

### Success Criteria

- `explain_small` visibly differs from `small_ack`
- `point_soft` can indicate focused object direction
- no full-body generated motion is required

## Phase 7 - Speech Timeline And TTS

### Purpose

After visual behavior works, add voice.

TTS is phase 7 because the product story can already be demonstrated with text + face/gaze.

### Server Additions

Later endpoint or service:

```text
TtsService
SpeechTimeline
```

Possible endpoint:

```text
POST /api/tts/synthesize
```

or extend:

```text
POST /api/runtime/respond
-> reply + behavior + speechTimeline
```

### Provider Order

Recommended:

1. local/mock audio or no audio first
2. Azure Speech TTS with viseme timing
3. ElevenLabs later if voice quality is more important than viseme convenience

### Success Criteria

- Unreal plays generated audio
- viseme or simple mouth movement follows audio
- face emotion and lip-sync do not fight too badly

## Phase 8 - Demo Scene

### Purpose

지원사업/포트폴리오/회사 지원용으로 볼 수 있는 장면을 만든다.

### Demo Scene Scope

```text
small Unreal exhibition room
one AI guide character
3-5 objects
simple selection or proximity trigger
text input panel or keyboard shortcut
server response
character expression/gaze/gesture
```

### Demo Flow

1. User selects exhibit 01
2. Character looks at exhibit 01
3. User asks: "이거 설명해줘"
4. Server returns explain behavior
5. Character smiles softly, points or gestures, replies
6. User asks uncertain question
7. Character switches to uncertain/thinking expression

### Success Criteria

- demo can be recorded in a short video
- the user can understand why the character expression changed
- Behavior JSON can be shown next to Unreal output for technical explanation

## Phase 9 - Real LLM Provider

### Purpose

Mock planner를 실제 LLM provider로 교체한다.

Do this after Unreal behavior path works.

### Reason

If real LLM is added too early, debugging becomes unclear:

```text
Is the problem the prompt?
Is the JSON invalid?
Is Unreal parsing wrong?
Is the face preset wrong?
```

Mock first, real provider later keeps debugging clean.

### Implementation

Add provider interface for runtime:

```text
RuntimeBehaviorProvider
  plan_response(message, scene_context, character_profile)
```

Providers:

```text
MockRuntimeBehaviorProvider
OpenAiRuntimeBehaviorProvider later
LocalRuntimeBehaviorProvider later
```

### Success Criteria

- real provider returns schema-valid JSON
- fallback to mock or safe behavior works if provider fails
- behavior values remain within allowed enum keys

## Do Not Build Yet

Avoid these in the first MVP:

- runtime text-to-motion generation
- full-body locomotion agent
- multi-agent conversations
- mobile AR/WebAR adapter
- full RAG admin dashboard
- production safety system
- perfect facial realism

These are valid later, but they will slow the first proof.

## First Coding Sprint

The first coding sprint should be only server-side.

Scope:

```text
contracts/runtime_behavior.py
services/runtime_character_service.py
/api/runtime/respond
tests for runtime response
README note if needed
```

Verification:

```powershell
cd Server-Python
python -m compileall app
python -m pytest
```

Expected output:

```text
existing tests pass
new runtime API tests pass
```

After this sprint, Unreal integration can begin with a stable JSON contract.
