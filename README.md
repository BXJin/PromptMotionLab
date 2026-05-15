# PromptMotionLab

PromptMotionLab is an Unreal-focused prompt-to-motion authoring tool.

The first MVP priority is:

```text
User Prompt
-> LLM MotionSpec / Procedural Gesture JSON
-> UE Control Rig Preview
-> Enriched Prompt generation and export
```

Commercial text-to-motion comparison, DeepMotion integration, imported motion retargeting, and local LLM inference are later phases.

## Repository Layout

```text
Server-Python/      FastAPI backend, contracts, mock LLM pipeline, prompt exports
Shared/contracts/   JSON Schema contracts shared with Unreal and docs
Docs/               planning docs and architecture diagrams
scripts/            local helper scripts
```

## Backend

```powershell
cd Server-Python
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --reload --port 8010
```

Verify:

```powershell
scripts\verify-server.bat
```

## MVP API

```text
GET  /health
POST /api/analyze-intent
POST /api/generate/procedural
POST /api/generate/enriched-prompt
GET  /api/prompt-exports/{export_id}
```

The current implementation uses `MockLlmProvider` so the pipeline is deterministic and can be developed before API keys or a UE project exist.

## Unreal Editor Plugin

The UE project lives at:

```text
Client-Unreal/PromptMotionClient/PromptMotionClient.uproject
```

The editor plugin lives at:

```text
Client-Unreal/PromptMotionClient/Plugins/PromptMotionEditor/
```

Open the panel from:

```text
Window -> Prompt Motion Lab
```

Current plugin scope:

```text
- Prompt input
- Server URL and skeleton preset fields
- /api/generate/procedural request
- /api/generate/enriched-prompt request
- MotionSpec / ProceduralGesture / EnrichedPrompt JSON display
- Selected Actor preview target resolution
- Manny Control Rig adapter entry point
```

Current preview scope:

```text
- Select an Actor with a Manny/Quinn SkeletalMeshComponent in the level
- Resolve Target validates that it matches ue5_manny
- Apply Preview builds the Manny wave preview plan from the last ProceduralGestureJson
```

Actual Control Rig control mapping is the next step. That requires confirming the control or variable names inside `CR_Mannequin_Procedural`.
