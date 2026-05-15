# Unreal Reference Reuse Notes

Updated: 2026-05-15

## Purpose

This document records reusable Unreal C++ references from:

```text
C:\Portfolio\InteractiveExhibition\Client-Unreal\ExhibitionClient\Source
```

Do not copy these systems into PromptMotionLab immediately.

Use them as reference material when PromptMotionLab needs:

- WebSocket realtime command push
- mobile/web panel control
- QR-based panel connection
- debug HUD
- spatial input bridge
- multi-agent or dynamic actor spawn

## Current PromptMotionLab Direction

The current MVP should remain simple:

```text
FastAPI HTTP request
-> /api/runtime/respond
-> Unreal RuntimeComponent receives reply + Behavior JSON
-> face/gaze/head/gesture execution
```

Do not introduce WebSocket or QR panel code before the basic HTTP behavior path and face preset blending are stable.

## High-Value Reference

### 1. Realtime WebSocket Subsystem

Reference files:

```text
C:\Portfolio\InteractiveExhibition\Client-Unreal\ExhibitionClient\Source\ExhibitionClient\Public\Realtime\ExhibitionRealtimeSubsystem.h
C:\Portfolio\InteractiveExhibition\Client-Unreal\ExhibitionClient\Source\ExhibitionClient\Private\Realtime\ExhibitionRealtimeSubsystem.cpp
```

Reuse value: high.

Useful patterns:

- `UGameInstanceSubsystem` for app-level realtime connection
- auto connect on initialize
- auto reconnect with timer
- WebSocket delegate handle cleanup
- game-thread dispatch via `AsyncTask(ENamedThreads::GameThread, ...)`
- raw JSON message broadcast
- `type` based command dispatch
- Blueprint multicast events for commands

Existing command concepts:

```text
setEmotion
playAnimation
triggerStageEvent
moveToPoint
moveDirection
rotate
panelConnected
panelDisconnected
switchStyle
chatReply
```

Possible PromptMotionLab mapping:

| Exhibition Command | PromptMotionLab Equivalent |
|---|---|
| `setEmotion` | `setFacePreset` or `applyBehavior` |
| `playAnimation` | `playGesture` |
| `chatReply` | `runtimeReply` |
| `moveToPoint` | spatial agent move target |
| `moveDirection` | mobile/web panel movement input |
| `rotate` | agent or camera rotation |
| `panelConnected` | mobile controller connected |
| `panelDisconnected` | mobile controller disconnected |

Recommended future name:

```text
UPromptMotionRealtimeSubsystem
```

Do not port blindly. Extract only the connection/reconnect/message-dispatch structure and rewrite command names around Behavior JSON.

## Medium-Value References

### 2. HUD / QR Panel UI

Reference files:

```text
C:\Portfolio\InteractiveExhibition\Client-Unreal\ExhibitionClient\Source\ExhibitionClient\Public\UI\ExhibitionHudManager.h
C:\Portfolio\InteractiveExhibition\Client-Unreal\ExhibitionClient\Source\ExhibitionClient\Private\UI\ExhibitionHudManager.cpp
C:\Portfolio\InteractiveExhibition\Client-Unreal\ExhibitionClient\Source\ExhibitionClient\Public\UI\ExhibitionHudWidget.h
C:\Portfolio\InteractiveExhibition\Client-Unreal\ExhibitionClient\Source\ExhibitionClient\Private\UI\ExhibitionHudWidget.cpp
```

Reuse value: medium.

Useful patterns:

- `UGameInstanceSubsystem` managing UMG widget lifecycle
- configured widget class through `DefaultGame.ini`
- panel URL display
- connection count display
- QR PNG download via HTTP
- PNG to `UTexture2D` conversion through `ImageWrapper`
- chat reply text display and timed hide

Possible PromptMotionLab uses:

- debug HUD showing latest `reply`
- debug HUD showing `emotion`, `intent`, `gaze`, `gestureKey`
- QR panel for mobile controller later
- operator panel connection status

Do not add this before the runtime behavior path is working.

### 3. Mobile / Panel Input Bridge

Reference files:

```text
C:\Portfolio\InteractiveExhibition\Client-Unreal\ExhibitionClient\Source\ExhibitionClient\Public\Input\ExhibitionPawnInputBridge.h
C:\Portfolio\InteractiveExhibition\Client-Unreal\ExhibitionClient\Source\ExhibitionClient\Private\Input\ExhibitionPawnInputBridge.cpp
```

Reuse value: medium.

Useful patterns:

- mobile/web panel input mapped into Unreal pawn or actor control
- connection to realtime subsystem events
- debug screen messages for panel-driven input

Possible PromptMotionLab uses:

- mobile app controls user camera or avatar movement
- panel selects focused object
- panel sends text prompt to AI agent
- panel triggers expression command such as `sad`, `surprised`, `angry`

### 4. Spawn Manager

Reference files:

```text
C:\Portfolio\InteractiveExhibition\Client-Unreal\ExhibitionClient\Source\ExhibitionClient\Public\Spawn\ExhibitionSpawnManager.h
C:\Portfolio\InteractiveExhibition\Client-Unreal\ExhibitionClient\Source\ExhibitionClient\Private\Spawn\ExhibitionSpawnManager.cpp
```

Reuse value: medium to low for current MVP.

Possible later uses:

- dynamically spawn AI agents
- spawn demo objects or guide markers
- react to panel connection state

Not needed for the single-character MVP.

## Low-Value References

### Messaging Placeholder Classes

Reference files:

```text
C:\Portfolio\InteractiveExhibition\Client-Unreal\ExhibitionClient\Source\ExhibitionClient\Public\Messaging\ExhibitionCommandDtos.h
C:\Portfolio\InteractiveExhibition\Client-Unreal\ExhibitionClient\Source\ExhibitionClient\Public\Messaging\ExhibitionCommandParser.h
C:\Portfolio\InteractiveExhibition\Client-Unreal\ExhibitionClient\Source\ExhibitionClient\Public\Realtime\ExhibitionWsClient.h
```

Reuse value: low.

These are mostly placeholder-style classes. The useful command parsing currently lives inside `UExhibitionRealtimeSubsystem::TryDispatchCommand`.

PromptMotionLab should not copy these directly.

## Build.cs Reference

InteractiveExhibition uses:

```csharp
"WebSockets"
"Json"
"JsonUtilities"
"UMG"
"Sockets"
"HTTP"
"ImageWrapper"
```

PromptMotionLab currently needs only:

```csharp
"HTTP"
"Json"
"JsonUtilities"
```

Add more only when needed:

| Module | Add When |
|---|---|
| `UMG` | debug HUD or operator UI |
| `WebSockets` | realtime server push or mobile panel command channel |
| `Sockets` | local IP detection or low-level networking |
| `ImageWrapper` | QR PNG download and conversion |

## Recommended Reuse Timeline

### Now

Do not port InteractiveExhibition C++ yet.

Continue with:

```text
HTTP RuntimeComponent
Behavior JSON receive
Face preset blend
Gaze/head/blink
Gesture key debug
```

### After Face Preset Works

Consider a small debug HUD:

```text
Latest reply
emotion
intent
gaze
gestureKey
confidence
```

Reference `ExhibitionHudManager` and `ExhibitionHudWidget`.

### After Demo Scene Works

Consider WebSocket/mobile panel:

```text
mobile panel -> prompt / focused object / expression command
server push -> applyBehavior / playGesture
```

Reference `UExhibitionRealtimeSubsystem`.

## Key Decision

InteractiveExhibition is a useful reference, but PromptMotionLab should not become a copy of it.

PromptMotionLab's runtime core remains:

```text
Behavior JSON
-> Renderer/Character Adapter
-> face, gaze, head, gesture, speech timeline
```

InteractiveExhibition code is mostly useful for transport, panel, and spatial control infrastructure.

