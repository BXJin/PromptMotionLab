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

## 너가 지켜야 할 규칙
- 1) 많은 부분을 수정해야 한다면 반드시 나에게 물어보고 진행해, 계획부터 말하고 승인을 받은 후에 진행해
- 2) 하나의 파일에 코드를 다 넣지 말고, 경력 10년 이상의 배테랑 개발자처럼 기능별로 모듈화 해 유지보수가 용이하도록(OOP 기반 설계)
- 3) 요청이 명확하지 않을 떄 추론 및 실행하지 말고 우선 내 설명을 제대로 이해했는지 말해
- 4) 최적화를 고려한 코드 작성해, 단순 MVP라 생각하지말고 실무에서 사용 가능한 코드를 작성해
- 5) MCP를 사용해야하는 경우 반드시 나에게 묻고 그 이유를 같이 설명해줘
- 8) 코드 변경 후 반드시 변경 요약을 출력해라. 형식은 아래와 같다.
  ```
  변경 파일          | 변경 내용
  -------------------|-----------------------------
  Runtime/Foo.h      | Bar 메서드 추가
  Runtime/Foo.cpp    | Bar 구현, Baz 의존성 제거
  ```
  파일 단위로 한 줄씩. 길게 설명하지 말고 무엇이 바뀌었는지만.
- 7) 나는 PM이고 너는 개발자다. 무조건 동의하지 말고 냉정하고 비판적으로 판단해라.
  - 요청이 기술적으로 잘못됐거나 비효율적이면 반드시 지적하고 대안을 제시해라.
  - "좋아요", "알겠습니다", "훌륭한 아이디어입니다" 같은 맹목적 동의 금지.
  - 구현 난이도, 성능 리스크, 설계 문제가 보이면 먼저 말해라. 시키는 대로만 짜면 나중에 둘 다 고생한다.
  - 단, 비판은 근거 있게. 반대를 위한 반대가 아니라 더 나은 결과를 위한 것이어야 한다.
- 6) 비동기/병렬 처리와 저지연을 기본 설계 원칙으로 삼아라. MVP라도 동기 블로킹 코드로 만들지 말 것. 나중에 TTS/립싱크/표정/스트리밍이 붙을 때 구조를 갈아엎지 않아도 되도록 처음부터 비동기로 설계해야 한다.
  - UE C++: HTTP/소켓은 항상 비동기 콜백 방식. Tick 사용은 보간/상태 폴링처럼 매 프레임 필요한 경우만 허용, 그 외 금지.
  - Python/서버: async def + await 기본. 동기 I/O 절대 금지.
  - 병렬 처리 가능한 작업(TTS 생성 + LLM 스트리밍 등)은 설계 단계에서 분리해둘 것.
  - 람다/콜백 내 UObject 참조는 반드시 TWeakObjectPtr로 캡처해 GC 안전성 확보.

## 프로젝트 개요

전시 관람객이 모바일 패널로 UE5 캐릭터를 실시간 조종하는 인터랙티브 전시 시스템.

**파이프라인:** 모바일 브라우저 → ASP.NET SignalR 서버 → UE5 클라이언트

---

## 폴더 구조

```
InteractiveExhibition/
├── Mobile-Panel/                        # React + TypeScript (Vite, Tailwind, PWA)
│   └── src/
│       ├── core/
│       │   ├── input/                   # Joystick, TouchPad, ActionButton
│       │   ├── hooks/                   # useJoystick, useThrottle, useTouchPad
│       │   ├── layout/                  # ControllerShell, SideMenu, StatusBar
│       │   └── transport/               # SignalRTransport, HttpTransport, TransportProvider
│       └── panels/exhibition/           # ExhibitionPanel, chatApi, commands
│
├── Server-AspNet/
│   └── ExhibitionServer/                # ASP.NET Core — SignalR Hub, WebSocket, Chat API
│       ├── Controllers/                 # ChatController, CommandsController, PanelAccessController
│       ├── Realtime/                    # ExhibitionHub, UnrealConnectionManager, UnrealWebSocketMiddleware
│       ├── Application/
│       │   ├── Chat/                    # ChatGuideService, AiGatewayClient, ConversationMemoryStore
│       │   └── Knowledge/               # ExhibitionKnowledgeStore, InMemoryKnowledgeVectorSearch
│       └── Data/ExhibitionKnowledge/    # 전시물 JSON (artifact_*.json)
│
├── Cloud-AI-Gateway/
│   └── ExhibitionAiGateway/             # ASP.NET Core — OpenAI 프록시, Embedding Rerank
│       ├── Controllers/                 # AiChatController
│       ├── Providers/OpenAI/            # OpenAiResponsesProvider, OpenAiEmbeddingClient
│       ├── Application/Rag/             # EmbeddingRetrievedContextRanker
│       └── Options/                     # OpenAiOptions, RagOptions, GatewayOptions
│
├── Client-Unreal/
│   └── ExhibitionClient/                # UE5 프로젝트
│       ├── Source/ExhibitionClient/
│       │   ├── Public/Realtime/         # ExhibitionRealtimeSubsystem
│       │   ├── Public/UI/               # ExhibitionHudWidget, ExhibitionHudManager
│       │   ├── Public/Input/            # ExhibitionPawnInputBridge
│       │   ├── Public/Spawn/            # ExhibitionSpawnManager
│       │   └── Public/Launch/           # ExhibitionServerLauncher
│       └── Plugins/UELLMToolkit/        # MCP 플러그인 (UE 내 Claude 연동)
│
├── Shared/                              # Exhibition.Shared (DTO, 공용 타입)
├── Build/                               # 빌드 산출물 (ExhibitionServer publish)
└── Docs/                                # 기획/설계 문서
```

---

## 핵심 파일

| 역할 | 경로 |
|------|------|
| SignalR Hub | `Server-AspNet/ExhibitionServer/Realtime/ExhibitionHub.cs` |
| UE WebSocket 미들웨어 | `Server-AspNet/ExhibitionServer/Realtime/UnrealWebSocketMiddleware.cs` |
| UE 연결 매니저 | `Server-AspNet/ExhibitionServer/Realtime/UnrealConnectionManager.cs` |
| 채팅 서비스 (RAG + 명령 디스패치) | `Server-AspNet/ExhibitionServer/Application/Chat/ChatGuideService.cs` |
| AI Gateway HTTP 클라이언트 | `Server-AspNet/ExhibitionServer/Application/Chat/AiGatewayClient.cs` |
| 전시물 지식 베이스 | `Server-AspNet/ExhibitionServer/Application/Knowledge/ExhibitionKnowledgeStore.cs` |
| 전시물 JSON 데이터 | `Server-AspNet/ExhibitionServer/Data/ExhibitionKnowledge/` |
| OpenAI 응답 프로바이더 + 프롬프트 | `Cloud-AI-Gateway/ExhibitionAiGateway/Providers/OpenAI/OpenAiResponsesProvider.cs` |
| Embedding Rerank | `Cloud-AI-Gateway/ExhibitionAiGateway/Application/Rag/EmbeddingRetrievedContextRanker.cs` |
| UE 리얼타임 서브시스템 | `Client-Unreal/ExhibitionClient/Source/ExhibitionClient/Public/Realtime/ExhibitionRealtimeSubsystem.h` |
| UE HUD 위젯 | `Client-Unreal/ExhibitionClient/Source/ExhibitionClient/Public/UI/ExhibitionHudWidget.h` |
| UE HUD 매니저 | `Client-Unreal/ExhibitionClient/Source/ExhibitionClient/Public/UI/ExhibitionHudManager.h` |
| 모바일 패널 진입점 | `Mobile-Panel/src/panels/exhibition/ExhibitionPanel.tsx` |
| SignalR 트랜스포트 | `Mobile-Panel/src/core/transport/SignalRTransport.ts` |

---

## 각 컴포넌트 실행 방법

### Mobile-Panel (React + Vite)
```bash
cd Mobile-Panel
npm install          # 최초 1회
npm run dev          # 개발 서버: http://0.0.0.0:3001
npm run build        # 빌드 → dist/
```

### Server-AspNet (로컬 서버 — UE와 함께 실행)
```bash
cd Server-AspNet/ExhibitionServer
dotnet run                          # 개발: http://localhost:5225
dotnet run --launch-profile https   # HTTPS
dotnet publish -c Release -r win-x64 --self-contained  # Steam 배포용 빌드
# 설정: appsettings.json → AiGatewayUrl, WebSocket 포트 등
```

### Cloud-AI-Gateway (클라우드 배포)
```bash
cd Cloud-AI-Gateway/ExhibitionAiGateway
dotnet run                          # 개발: http://localhost:5100
dotnet publish -c Release           # 배포용 빌드
# 필수 환경변수: OpenAI__ApiKey, Gateway__ApiKey
# 설정: appsettings.Production.json
```

### Client-Unreal (UE5)
- Visual Studio 2022로 `Client-Unreal/ExhibitionClient/ExhibitionClient.sln` 열어서 빌드
- 또는 UE5 에디터에서 직접 실행
- MCP 브릿지: `Plugins/UELLMToolkit/Resources/mcp-bridge/` → `npm install` 필요 (gitignore로 node_modules 제외됨)
- Config: `DefaultGame.ini` → `HudWidgetClass`, `WebSocketUrl`, `MobilePanelPort`

---

## MCP (UELLMToolkit)

- UE 에디터 내 MCP 플러그인 사용은 **명시적으로 요청할 때만** 실행
- 자동으로 MCP 도구를 호출하지 말 것
