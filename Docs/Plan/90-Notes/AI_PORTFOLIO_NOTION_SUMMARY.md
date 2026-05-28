# PromptMotionLab 포트폴리오 정리 노트

Updated: 2026-05-26

## 한 문장 요약

PromptMotionLab은 사용자의 음성/텍스트 입력을 받아 LLM 응답, TTS 음성, viseme 립싱크, 표정 레이어를 실시간으로 연결하는 **모바일 디지털 휴먼 런타임 프로젝트**다.

단순히 "AI 캐릭터가 대답한다"가 아니라, 실제 대화처럼 느껴지도록 다음 문제를 직접 다뤘다.

- STT, LLM, TTS 지연을 어떻게 줄일 것인가
- 답변이 늦는 동안 캐릭터가 멈춰 보이지 않게 할 것인가
- 음성, 립싱크, 표정이 서로 충돌하지 않게 할 것인가
- PC PIE가 아니라 Android 실기기와 Play Store 배포까지 고려할 것인가
- AI가 만든 코드/설계를 그대로 쓰지 않고 어떻게 검증하고 개선할 것인가

## 왜 이 주제인가

AI 캐릭터 앱은 겉으로 보기에는 "질문하면 답하는 챗봇"처럼 보일 수 있다. 하지만 사용자가 실제로 대화한다고 느끼려면 다음 요소가 동시에 맞아야 한다.

```text
음성 입력
-> 빠른 이해
-> 자연스러운 답변
-> 빠른 첫 음성
-> 립싱크
-> 표정 변화
-> 모바일에서 안정적인 동작
```

이 중 하나라도 어긋나면 디지털 휴먼은 바로 어색해진다.

예를 들어:

- 답변이 5초 늦으면 실제 대화 느낌이 사라진다.
- 입은 멈췄는데 음성이 계속 나오면 립싱크가 어색하다.
- 표정이 계속 고정되어 있으면 캐릭터가 살아있지 않다.
- Android에서 마이크 권한이나 오디오 재생이 깨지면 제품으로 쓸 수 없다.

그래서 이 프로젝트의 문제 정의는 다음이다.

```text
실시간 대화형 디지털 휴먼에서 입력, 응답, 음성, 립싱크, 표정을 지연과 충돌 없이 연결하는 런타임을 만든다.
```

## 이미지 기준 1: "AI가 해줄 수 있는 것"과 "본인이 해야 하는 것"

이 프로젝트에서 AI가 도와준 것은 다음에 가깝다.

- C++/Python 코드 초안 작성
- FastAPI endpoint 설계 보조
- Unreal component 구조 제안
- CSV schema 초안
- 테스트 케이스 초안
- 오류 원인 후보 정리
- 문서 초안 작성

하지만 핵심 판단은 직접 해야 했다.

- LLM이 morph target을 직접 내려주는 구조가 맞는가
- TTS 전체 합성을 기다릴 것인가, 문장 단위로 쪼갤 것인가
- amplitude 기반 silence trim을 쓸 것인가, viseme 기반 trim을 쓸 것인가
- OpenAI Realtime API로 갈 것인가, Azure streaming STT로 갈 것인가
- VAD 중 Thinking 상태 입력을 받을 것인가 차단할 것인가
- 표정과 립싱크가 충돌할 때 어느 layer가 mouth를 소유해야 하는가

즉, 이 프로젝트는 AI를 코드 생성 도구로만 쓴 것이 아니라, **AI가 제안한 구현을 실제 제품 기준으로 검증하고 수정한 과정**이 핵심이다.

## 이미지 기준 2: AI 시대 포트폴리오 4가지 방향성과 프로젝트 적용

### 1. 도메인 관심과 문제의식

질문:

```text
왜 이 문제를 풀고 싶었는가?
```

PromptMotionLab의 문제의식:

```text
디지털 휴먼은 단순히 답변을 생성하는 것만으로는 자연스럽지 않다.
사람과 대화하는 느낌을 내려면 답변 지연, 음성 출력, 얼굴 표정, 립싱크, 모바일 입력이 모두 맞아야 한다.
```

이 프로젝트는 일반적인 CRUD나 챗봇이 아니라, **실시간 인터랙션 품질**이 핵심인 문제를 다룬다.

주요 도메인 요소:

- 실시간 대화
- 음성 인식 STT
- 음성 합성 TTS
- viseme 기반 립싱크
- 3D 캐릭터 표정
- Android 모바일 앱
- 서버 provider latency

### 2. 문제 설정과 해결 흐름

초기 MVP:

```text
텍스트 입력
-> LLM 응답
-> TTS 합성
-> WAV 재생
-> 립싱크
```

문제:

- 응답이 올 때까지 캐릭터가 멈춰 보임
- TTS 전체가 끝나야 첫 음성이 나옴
- 한글/영어 TTS provider 설정 차이
- 립싱크가 어색함
- 표정 preset과 mouth morph가 충돌함
- 모바일 마이크 입력 구조가 없음

개선 흐름:

```text
1. Behavior JSON 계약 정의
2. Unreal face preset layer 구현
3. Azure TTS + viseme timeline 연결
4. CSV 기반 face/lipsync tuning 구조 도입
5. turn/async API로 responseReady / ttsReady 분리
6. sentence-level TTS queue 구현
7. viseme 기반 WAV trailing silence trim
8. PTT/VAD/STT 입력 구조 추가
9. 중복 submit guard 추가
10. Azure streaming STT Phase 1 추가
11. Android 배포 설정 준비
```

이 흐름은 "AI가 코드를 만들어줬다"가 아니라, **실제 테스트에서 문제를 발견하고 구조를 바꾼 과정**이다.

### 3. 소프트웨어 기술과 공학적 접근

이 프로젝트에서 공학적으로 다룬 부분:

- FastAPI async endpoint
- async job service
- provider timeout/fallback
- STT/TTS/LLM provider abstraction
- Unreal HTTP/WebSocket async client
- GameThread blocking 방지
- sentence-level audio queue
- viseme timeline parsing
- morph target layer 분리
- CSV-driven face/lipsync config
- latency CSV logging
- character matrix regression test
- Android microphone permission
- WebSocket streaming STT

단순 기능 구현보다 중요한 것은 다음이었다.

```text
어떤 작업을 서버에서 하고,
어떤 작업을 Unreal 클라이언트에서 하며,
어떤 데이터만 네트워크로 주고받을 것인가?
```

그래서 서버는 compact behavior와 speech timeline만 내려주고, morph blending은 Unreal에서 처리한다.

### 4. 실행 가능한 결과물

현재 결과물:

- Unreal 클라이언트
- Python FastAPI 서버
- OpenAI LLM provider routing
- OpenAI batch STT
- Azure TTS + viseme
- Azure streaming STT Phase 1
- sentence-level TTS queue
- face/lipsync CSV config
- debug face UI
- latency/matrix report output
- Android package 설정 일부

포트폴리오에 보여줄 수 있는 것:

- GitHub 코드
- README
- 아키텍처 문서
- 동작 영상
- matrix test 결과 CSV/JSON
- latency before/after 수치
- Android internal test 과정

## 이미지 기준 3: 일상의 문제에서 출발

이미지의 메시지:

```text
평범한 주제라도 측정 기준과 공학적 관심을 추가하면 완전히 달라진다.
```

PromptMotionLab의 일상 문제:

```text
사람이 AI 캐릭터에게 말을 걸었는데, 대답이 늦고 입모양과 표정이 어색하면 실제 대화처럼 느껴지지 않는다.
```

공학적 주제화:

```text
실시간 대화형 디지털 휴먼 런타임 설계
```

기술 포인트:

| 문제 | 공학적 주제 | 기술 포인트 |
|---|---|---|
| 답변이 늦음 | latency pipeline 최적화 | STT, LLM routing, async turn, sentence TTS |
| 첫 음성이 늦음 | TTS first audio start 개선 | sentence-level queue, first segment playback |
| 입모양이 어색함 | viseme lip-sync mapping | Azure viseme id, CSV morph mapping |
| 음성과 입이 안 맞음 | audio/viseme timing sync | viseme-based WAV trim |
| 표정이 굳어 보임 | local face runtime | idle blink, micro-expression |
| 말하는 중 표정 충돌 | layered morph ownership | lip_sync_mask, face/lipsync 분리 |
| 모바일에서 불안정 | Android runtime validation | RECORD_AUDIO, WebSocket, procedural audio |

## 이미지 기준 4: AI 코딩 한계를 실험하고 개선하기

이 프로젝트에서 실제로 드러난 AI/초기 구현의 한계와 개선 사례.

### 사례 1. 전체 TTS를 기다리는 구조

초기 구조:

```text
LLM 완료
-> 전체 답변 TTS
-> WAV 다운로드
-> 재생
```

문제:

- 답변이 길면 첫 음성 시작이 늦다.
- 사용자는 캐릭터가 생각만 하고 있다고 느낀다.

개선:

```text
sentence-level TTS queue
-> 첫 문장 segment부터 재생
-> 나머지는 뒤에서 큐잉
```

결과:

- 전체 TTS 완료를 기다리지 않고 첫 segment 재생 가능
- 긴 답변에서도 대화 템포 개선

### 사례 2. Azure TTS trailing silence

실제 로그:

```text
Before
Hi! duration=1.30s
last viseme=0.521s
gap=779ms

After
Hi! duration=0.67s
last viseme=0.521s
gap=149ms
```

문제:

- Azure TTS segment 끝에 약 780ms 무음이 붙음
- 입은 멈추는데 오디오는 계속 재생됨
- segment 3개면 2초 이상 불필요한 공백 발생

처음 고려한 방법:

```text
amplitude 기반 silence trim
```

기각한 이유:

- s, t, h 같은 quiet phoneme을 silence로 오탐할 수 있음
- threshold 튜닝이 provider/voice/language마다 달라짐
- 배포용으로 fragile함

최종 해결:

```text
last_viseme_time + 0.15s 기준으로 WAV trim
```

왜 이게 더 나은가:

- Azure가 이미 실제 발화 타이밍을 viseme으로 제공
- threshold가 필요 없음
- deterministic함
- segment queue latency를 직접 줄임

### 사례 3. 1 viseme -> 1 morph 한계

초기 문제:

```text
viseme 하나에 morph 하나만 켬
나머지는 0
```

문제:

- 실제 입 모양은 여러 morph 조합으로 만들어짐
- A, E, M/B/P 소리가 모두 어색해짐

개선:

```text
1 viseme -> N morphs
CSV 기반 lipsync_visemes_default_girl.csv
```

예시:

```text
ID 2:
Mouth_Close -0.30
V_Lip_Open 0.38
V_Open 0.12

ID 18:
V_Dental_Lip 0.30~0.40
```

결과:

- 캐릭터별 튜닝 가능
- C++ 재컴파일 없이 CSV/debug UI로 조정 가능

### 사례 4. 표정과 립싱크 충돌

문제:

- friendly/happy 표정은 mouth smile을 사용
- lip-sync도 mouth/jaw를 사용
- 둘이 동시에 강하게 들어가면 입이 과장됨

개선:

```text
lip_sync_mask 도입
face preset / lipsync / idle / speech micro layer 분리
```

결과:

- 말하는 중 mouth expression을 일부 억제
- 눈/눈썹/볼 중심 emotion은 유지
- lip-sync는 mouth 중심으로 동작

### 사례 5. PTT/VAD 중복 submit

실제 로그:

```text
TurnAsync request #1
TurnAsync request #2
request #1 stale
```

문제:

- stale guard는 크래시를 막지만 서버 비용은 이미 발생
- 사용자는 응답이 중간에 바뀌는 것처럼 느낄 수 있음

개선:

```text
STT in-flight guard
Debug WAV in-flight guard
Thinking/Transcribing 중 submit block
VAD는 Idle/Listening에서만 시작
```

결과:

- 중복 STT/LLM 요청 감소
- 상태 꼬임 감소
- 모바일 UX 안정성 증가

### 사례 6. Batch STT 지연

초기 구조:

```text
PTT release
-> WAV POST
-> STT 완료
-> LLM 시작
```

문제:

- PTT를 뗀 뒤 STT 1~2초가 그대로 체감 지연으로 들어감

개선 방향:

```text
Azure streaming STT Phase 1
```

현재 구조:

```text
PTT 시작
-> PCM chunk를 /ws/stt로 전송
-> Azure streaming STT
-> final transcript 수신
-> 기존 turn/async 실행
```

왜 OpenAI Realtime API가 아니라 Azure streaming STT인가:

- 현재 turn/async, TTS segment queue, viseme trim 구조를 유지할 수 있음
- 이미 Azure TTS 리소스를 사용 중
- OpenAI Realtime은 STT/LLM/audio를 통합하므로 아키텍처 변경 폭이 큼

## 이미지 기준 5: 빅테크 기술 발표/장애 사례 재현 관점

이 프로젝트는 직접적으로 Slack이나 Uber 사례를 재현한 것은 아니지만, 비슷한 기술 축을 가진다.

| 빅테크 사례 주제 | PromptMotionLab 대응 |
|---|---|
| 실시간 메시지 지연 | WebSocket STT, async turn, audio segment queue |
| 위치/이벤트 stream 처리 | PCM audio chunk streaming |
| 장애/timeout 대응 | provider timeout, fallback, stale guard |
| queue 기반 처리 | sentence-level TTS segment queue |
| latency budget | STT/LLM/TTS/audio start 측정 |
| client/server sync | speech timeline, viseme timing, local face runtime |

노션에 쓸 수 있는 표현:

```text
이 프로젝트는 대규모 분산 시스템은 아니지만, 실시간 시스템에서 중요한 event streaming, queueing, timeout, fallback, latency measurement 문제를 작은 디지털 휴먼 런타임 안에서 다뤘다.
```

## 이미지 기준 6: GitHub, 블로그, YouTube로 확장

### GitHub에서 보여줄 것

- 서버/클라이언트 분리 구조
- FastAPI endpoint
- Unreal runtime component
- provider abstraction
- async job service
- speech playback controller
- face/lipsync layer
- CSV config
- matrix test script/result
- 문서화된 tradeoff

### 기술 블로그 주제 후보

1. **디지털 휴먼의 첫 음성 지연을 줄이기 위한 sentence-level TTS queue**
2. **Azure TTS trailing silence를 amplitude가 아니라 viseme timeline으로 trim한 이유**
3. **LLM이 morph target을 직접 만들지 않게 한 이유**
4. **Unreal에서 face preset과 lip-sync layer를 분리한 이유**
5. **Batch STT에서 Streaming STT로 확장한 과정**
6. **모바일 AI 캐릭터 앱에서 PTT/VAD 중복 입력을 막는 방법**

### YouTube / 영상에서 보여줄 것

- PTT 누르고 말하는 장면
- 캐릭터가 즉시 thinking/listening 표정으로 반응하는 장면
- 첫 음성 재생까지의 시간
- 립싱크와 표정이 같이 움직이는 장면
- debug log overlay:
  - STT latency
  - LLM latency
  - TTS segment duration
  - first audio start
- Before/After:
  - trailing silence trim 전후
  - 전체 TTS vs sentence queue

## 이미지 기준 7: 유저 없어도 성능 수치 만들기

현재 프로젝트에서 이미 만들었거나 만들 수 있는 수치:

### 이미 관측한 수치

```text
STT Debug WAV latency: 약 0.9~1.8s
LLM nano route latency: 약 1.0~2.3s
Azure TTS segment trailing silence before: 약 780ms
Azure TTS segment trailing silence after: 약 150ms
```

### 현재 CSV/로그로 측정 가능한 것

- responseReadyMs
- ttsReadyMs
- sttLatencyMs
- providerLatencyMs
- firstVisibleReactionMs
- audioPlayStartMs
- fallback rate
- route distribution
- character-specific pass/fail

### 추가하면 좋은 기준

```text
first visible reaction p95 <= 300ms
STT final after speech end p95 <= 800ms
LLM response ready p95 <= 2.5s
first audio start p95 <= 3.0s
TTS segment trailing gap <= 200ms
fallback rate <= 5%
```

### 부하 테스트 후보

- `/api/runtime/turn/async`
- `/api/runtime/turn/jobs/{id}`
- `/api/runtime/tts/synthesize`
- `/ws/stt`
- audio file serving
- cleanup loop

도구 후보:

- k6
- Locust
- JMeter
- nGrinder

## PromptMotionLab 포트폴리오 구조 제안

### 1. 프로젝트 개요

```text
실시간 음성 대화형 3D 캐릭터 런타임.
사용자의 음성을 STT로 변환하고, LLM으로 응답과 behavior를 생성하며,
TTS/viseme timeline을 Unreal에서 재생해 표정과 립싱크를 동기화한다.
```

### 2. 문제 정의

```text
AI 캐릭터는 답변 생성만으로 자연스럽지 않다.
실제 대화처럼 느끼려면 latency, 음성, 립싱크, 표정, 입력 상태가 함께 맞아야 한다.
```

### 3. 핵심 설계

- compact Behavior JSON
- Unreal-side face/lipsync layer
- async turn API
- sentence-level TTS queue
- Azure viseme timeline
- viseme-based WAV trim
- CSV-driven morph tuning
- PTT/VAD input guard
- streaming STT Phase 1

### 4. 대표 개선 사례

| 문제 | 측정/원인 | 해결 | 결과 |
|---|---|---|---|
| TTS segment 공백 | WAV tail 약 780ms | viseme 기반 trim | 약 150ms로 감소 |
| 첫 음성 지연 | 전체 TTS 완료 대기 | sentence queue | 첫 segment 우선 재생 |
| 립싱크 어색함 | 1 viseme -> 1 morph | 1 viseme -> N morphs CSV | 캐릭터별 튜닝 가능 |
| 표정 충돌 | mouth morph 동시 제어 | lip_sync_mask/layer 분리 | 말하는 중 표정 유지 |
| 중복 입력 | PTT/VAD submit 반복 | in-flight guard | stale/비용 감소 |
| STT 대기 | batch STT | streaming STT Phase 1 | 지연 감소 기대 |

### 5. 아키텍처 요약

```text
Unreal Mobile Client
  - PTT / VAD / Streaming STT
  - RuntimeComponent
  - SpeechPlaybackController
  - FacePreset / LipSync / Idle / Micro layers

FastAPI Server
  - Runtime behavior service
  - Character profile routing
  - Async turn job service
  - TTS service
  - STT service
  - Provider timeout/fallback

Providers
  - OpenAI LLM
  - OpenAI batch STT
  - Azure streaming STT
  - Azure TTS + viseme
```

### 6. 트레이드오프 정리

| 선택지 | 선택 | 이유 |
|---|---|---|
| morph를 서버에서 직접 생성 vs Behavior JSON | Behavior JSON | 캐릭터별 morph 차이를 클라이언트/CSV에서 관리 |
| 전체 TTS vs sentence queue | sentence queue | first audio latency 감소 |
| amplitude trim vs viseme trim | viseme trim | threshold 없이 결정론적 |
| OpenAI Realtime vs Azure streaming STT | Azure streaming STT | 기존 구조 유지, Azure 리소스 재사용 |
| hardcoded morph vs CSV | CSV | 기획/튜닝 반복 가능 |
| VAD 중 Thinking 입력 허용 vs 차단 | 차단 | 자동 입력 오인식/상태 꼬임 방지 |

### 7. 남은 검증

- 실제 마이크 PTT end-to-end
- Android Development APK 실기기 테스트
- batch STT vs streaming STT latency 비교
- Android `USoundWaveProcedural` 재생 안정성
- Play Console internal testing
- 모바일 UI safe area / mic button UX

## 제출 전 셀프 체크리스트에 대한 현재 상태

| 체크 항목 | 현재 상태 |
|---|---|
| 왜 이 주제인지 설명 가능 | 가능 |
| 직접 설정한 품질 기준/측정 수치 | 일부 있음, Android 실측 필요 |
| GitHub 소스코드 | 준비 가능 |
| README/아키텍처 문서 | 추가 정리 필요 |
| 동작 영상 | 필요 |
| AI 활용/직접 검증 설명 | 가능 |
| 핵심 코드/설계 구두 설명 | 가능 |
| 트레이드오프 근거 | 문서화 가능 |
| 나만의 관점 | latency + face/lipsync/mobile runtime 관점 |

## 노션에 넣을 최종 메시지

```text
PromptMotionLab은 단순히 AI 캐릭터를 만든 프로젝트가 아니다.
실시간 대화형 디지털 휴먼에서 실제 제품 품질을 가르는 latency, STT, TTS, lip-sync, face layer, mobile deployment 문제를 직접 정의하고 개선한 프로젝트다.

AI는 구현 속도를 높이는 데 활용했지만, 핵심 설계 판단과 품질 기준은 직접 세웠다.
특히 sentence-level TTS queue, viseme 기반 WAV trim, layered face runtime, streaming STT 확장 과정은 AI 시대 포트폴리오에서 보여줘야 하는 "문제 정의 -> 실험 -> 측정 -> 개선" 흐름을 담고 있다.
```
