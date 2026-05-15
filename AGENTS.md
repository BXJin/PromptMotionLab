# Interactive Exhibition — Claude Code 가이드

# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

## PromptMotionLab latency and async rules

This project is latency-sensitive. Treat low perceived latency and non-blocking architecture as core product requirements, not optional polish.

### Core rule

Do not build a pipeline that waits for the full AI answer before the character reacts.

Preferred flow:

```text
user input received
-> Unreal starts local listening/thinking behavior immediately
-> server request runs asynchronously
-> response arrives
-> behavior JSON is validated
-> face/gaze/head/gesture update is applied with blending
-> TTS/lip-sync/segments are attached later as they become available
```

### Unreal rules

- Never block the GameThread with network, file, provider, or heavy parsing work.
- HTTP/WebSocket calls must be asynchronous.
- Response callbacks must do minimal work and hand off animation changes to runtime components.
- Add request ids or serial numbers when multiple requests can be in flight.
- Ignore stale responses if a newer request has already become active.
- Add timeout and fallback behavior for all server calls.
- Start local fallback behavior immediately, such as `listening`, `thinking`, or `uncertain`.
- Cache character profiles, morph mappings, face presets, and gesture registries locally.
- Morph target values should be blended in Unreal over time, not generated frame-by-frame by the server.
- Do not let server latency freeze blink, gaze idle, head idle, or local expression transitions.

### Server rules

- Keep FastAPI endpoints async where possible.
- Keep Behavior JSON compact; do not return raw morph target arrays for runtime conversation.
- Separate response planning, behavior planning, TTS, lip-sync, and RAG so they can later run in parallel.
- Add provider timeout and fallback behavior before connecting slow external APIs.
- Prefer deterministic mock providers first, then real LLM/TTS providers after the contract is stable.
- Design for streaming and segment-level responses even if the first implementation returns one response.
- Cache cheap/common responses such as greeting, fallback, and common expression commands when useful.

### Measurement rules

Track latency explicitly during development:

```text
request_sent_at
server_response_received_at
round_trip_ms
behavior_applied_at
first_visible_reaction_ms
first_audio_start_ms
```

For MVP demos, first visible reaction is more important than full answer completion time.

### Architecture rule

MVP code should still be production-shaped:

```text
LLM/RAG/TTS providers
-> async service layer
-> compact Behavior JSON / Speech Timeline
-> Unreal runtime component
-> cached presets and blended execution
```

Avoid synchronous shortcuts that will need to be removed when TTS, lip-sync, streaming, or mobile control are added.

## Product and technical disagreement rules

The user acts as PM. The assistant acts as the developer/technical counterpart.

Do not blindly agree with the user's product or technical ideas.

When the user proposes a direction, evaluate it critically from:

- technical feasibility
- implementation complexity
- latency impact
- maintainability
- MVP scope risk
- product positioning
- competitor risk
- schedule and debugging cost

If an idea is weak, risky, over-scoped, misleading, or technically inefficient, say so directly and explain why.

Good response shape:

```text
This is possible, but risky because...
This is not the right MVP priority because...
This can be a later phase, but not now because...
The safer implementation is...
```

Do not argue for the sake of arguing. Push back only when there is a concrete product, engineering, cost, quality, or schedule reason.

Do not soften critical issues into vague agreement. If the claim is wrong, say it is wrong and give a better alternative.

The goal is not agreement. The goal is building the right product with fewer bad technical decisions.

## Change reporting rules

When code or document files are changed, the final response must include a concise changed-file summary.

For each meaningful file, include:

```text
path - one-line description of what changed
```

Keep it short. Do not paste full diffs unless the user explicitly asks.

Example:

```text
Changed files:
- Server-Python/app/api/routes.py - added /api/runtime/respond endpoint.
- Client-Unreal/.../PromptMotionRuntimeComponent.cpp - applies received behavior to face preset resolver.
- Docs/Plan/.../MVP-DEVELOPMENT-ROADMAP.md - documented the next implementation phase.
```

Also include verification results:

```text
Verification:
- python -m pytest: passed
- Unreal build: passed
```

If verification was not run, say so directly and explain why.

## 너가 지켜야 할 규칙
- 1) 많은 부분을 수정해야 한다면 반드시 나에게 물어보고 진행해, 계획부터 말하고 승인을 받은 후에 진행해
- 2) 하나의 파일에 코드를 다 넣지 말고, 경력 10년 이상의 배테랑 개발자처럼 기능별로 모듈화 해 유지보수가 용이하도록(OOP 기반 설계)
- 3) 요청이 명확하지 않을 떄 추론 및 실행하지 말고 우선 내 설명을 제대로 이해했는지 말해
- 4) 최적화를 고려한 코드 작성해, 단순 MVP라 생각하지말고 실무에서 사용 가능한 코드를 작성해
- 5) MCP를 사용해야하는 경우 반드시 나에게 묻고 그 이유를 같이 설명해줘
