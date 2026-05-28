# PromptMotionLab Runtime Realtime Technique

Updated: 2026-05-26

## 목적

이 문서는 PromptMotionLab의 실시간 대화형 3D 캐릭터 런타임 구조를 정리한다.

초기 MVP는 "텍스트 입력 -> LLM 응답 -> TTS 재생 -> 얼굴 표정 적용"을 빠르게 연결하는 것이 목표였다. 지금 구조는 그 MVP에서 출발했지만, 실제 모바일 앱과 배포를 고려하면서 다음 요구를 만족하도록 점진적으로 바뀌었다.

- 사용자가 기다리는 동안 캐릭터가 멈춰 보이지 않아야 한다.
- LLM, STT, TTS 지연이 있어도 첫 반응은 즉시 보여야 한다.
- 음성 입력, 음성 출력, 립싱크, 표정이 서로 충돌하지 않아야 한다.
- Android 실기기, Play Store 배포, 서버 운영을 고려해야 한다.
- provider를 바꿔도 Unreal 쪽 구조가 크게 무너지면 안 된다.

현재 방향은 단순 데모가 아니라 **배포 가능한 실시간 대화형 캐릭터 런타임**이다.

## MVP에서 배포형 구조로 바뀐 이유

초기 MVP 흐름은 단순했다.

```text
텍스트 입력
-> POST /api/runtime/respond
-> LLM 응답 대기
-> POST /api/runtime/tts/synthesize
-> WAV 다운로드
-> 오디오 재생 + 립싱크
```

이 방식은 구현은 빠르지만 실제 제품 기준으로 문제가 있었다.

- LLM이 3~5초 걸리면 캐릭터가 멈춰 보인다.
- TTS 전체 합성이 끝나야 첫 음성이 나와 체감 지연이 크다.
- 사용자가 마이크로 말하는 구조에서는 STT 시간이 그대로 추가된다.
- TTS 중 마이크가 열리면 자기 목소리를 다시 인식할 수 있다.
- 표정 preset과 lip-sync가 같은 mouth morph를 동시에 건드려 어색해질 수 있다.
- Android에서는 권한, WebSocket, 오디오 재생, 네트워크 URL이 PIE와 다르게 동작한다.

그래서 현재 구조는 다음 원칙으로 바뀌었다.

```text
사용자 입력 수신
-> Unreal이 즉시 local reaction 적용
-> 서버 작업은 async job으로 진행
-> LLM 응답이 준비되면 표정/행동 먼저 적용
-> TTS segment가 준비되는 대로 오디오와 립싱크를 붙임
-> blink, idle, micro-expression은 서버 지연과 무관하게 계속 동작
```

## 현재 런타임 흐름

```text
PTT / VAD / text input
-> PromptMotionRuntimeComponent
-> local thinking/listening face preset
-> FastAPI runtime server
-> character profile + routing LLM provider
-> compact Behavior JSON
-> async turn response
-> sentence-level Azure TTS segments
-> viseme-based WAV trim
-> Unreal speech playback queue
-> face preset + lip-sync + blink + speech micro-expression
```

핵심 파일:

```text
Server-Python/app/api/routes.py
Server-Python/app/services/runtime_character_service.py
Server-Python/app/services/runtime_turn_async_job_service.py
Server-Python/app/services/tts_service.py
Server-Python/app/providers/tts/azure_provider.py
Server-Python/app/providers/stt/azure_streaming_provider.py

Client-Unreal/PromptMotionClient/Source/PromptMotionClient/Runtime/Core
Client-Unreal/PromptMotionClient/Source/PromptMotionClient/Runtime/Face
Client-Unreal/PromptMotionClient/Config/PromptMotion
```

## 1. Compact Behavior JSON

서버는 morph target 배열을 직접 내려주지 않는다. LLM은 high-level behavior만 반환한다.

```json
{
  "emotion": "friendly",
  "intensity": 0.72,
  "intent": "answer",
  "gaze": "user",
  "gestureKey": "greet_small",
  "headMotion": "small_nod",
  "ttsStyle": "warm"
}
```

이 방식으로 바꾼 이유:

- LLM이 `Jaw_Open`, `Mouth_Smile_L` 같은 morph를 직접 만들면 결과가 불안정하다.
- 캐릭터 mesh마다 morph 이름과 강도가 다르다.
- 표정 튜닝은 Unreal/CSV 쪽에서 하는 것이 디버깅하기 쉽다.
- 서버 응답 계약이 작아져 latency와 validation 비용이 줄어든다.
- 나중에 Unity/Web 클라이언트를 붙여도 같은 behavior contract를 재사용할 수 있다.

## 2. Async Turn API

초기 HTTP 2단계 체인은 전체 LLM과 TTS를 기다리는 구조였다. 현재는 `/api/runtime/turn/async`를 사용한다.

```text
POST /api/runtime/turn/async
-> turnJobId + reaction 즉시 반환
-> Unreal polling
-> responseReady: behavior/reply 적용
-> ttsReady: speech timeline segment 재생
```

이 방식으로 바꾼 이유:

- 캐릭터가 즉시 생각하는 표정을 보여줄 수 있다.
- LLM 완료와 TTS 완료를 분리할 수 있다.
- LLM은 끝났지만 TTS가 아직인 상태에서도 얼굴/상태를 먼저 갱신할 수 있다.
- 서버 작업 timeout, fallback, job cleanup을 중앙에서 관리할 수 있다.
- WebSocket/SSE로 가기 전에도 안정적인 fallback path가 된다.

## 3. Sentence-Level TTS Queue

초기에는 답변 전체를 한 번에 TTS로 합성했다. 현재는 문장 단위 segment queue를 사용한다.

```text
LLM reply
-> sentence split
-> segment 1 TTS ready
-> Unreal segment 1 재생
-> segment 2, 3은 뒤에서 다운로드/큐잉
```

이 방식으로 바꾼 이유:

- 전체 답변 TTS를 기다리지 않아도 첫 음성이 나온다.
- 첫 오디오 시작 시간이 줄어든다.
- 긴 답변도 자연스럽게 이어 말하는 느낌을 줄 수 있다.
- TTS segment별 viseme timeline을 따로 적용할 수 있다.

Unreal 쪽에서는 `FPromptMotionSpeechPlaybackController`가 segment append, WAV 다운로드, sequential playback을 담당한다.

## 4. Azure TTS, Viseme Timeline, WAV Trim

Azure TTS는 WAV와 viseme id/audio offset을 제공한다. 서버는 이를 `SpeechTimeline`으로 정규화한다.

```json
{
  "utteranceId": "utt_xxx",
  "durationSeconds": 2.8,
  "audio": {
    "url": "/api/runtime/audio/utt_xxx.wav",
    "durationSeconds": 2.8,
    "format": "wav"
  },
  "visemes": [
    { "time": 0.12, "id": 1, "weight": 1.0 }
  ]
}
```

운영 중 발견된 문제:

- Azure가 문장별 WAV 끝에 약 780ms trailing silence를 붙였다.
- 입은 마지막 viseme에서 멈추는데 오디오는 더 길게 남아 싱크가 어긋났다.
- segment 3개면 약 2초 이상의 불필요한 지연이 생겼다.

해결:

```text
last_viseme_time + TTS_VISEME_TRIM_TAIL_SECONDS
기본값: 0.15s
```

서버에서 amplitude 기반 silence trim은 쓰지 않는다. 조용한 자음이나 decay를 잘라낼 위험이 있기 때문이다. 대신 Azure viseme timeline을 기준으로 결정론적으로 WAV를 trim한다.

이 방식으로 바꾼 이유:

- threshold 튜닝이 필요 없다.
- TTS provider가 주는 timing metadata를 활용하므로 재현 가능하다.
- segment queue의 체감 지연을 직접 줄인다.
- Unreal fallback timer와 lip-sync duration도 더 정확해진다.

## 5. Lip-Sync Layer

초기 lip-sync는 `1 viseme -> 1 morph`에 가까웠다. 현재는 CSV 기반으로 `1 viseme -> N morphs`를 지원한다.

```text
Client-Unreal/PromptMotionClient/Config/PromptMotion/lipsync_visemes_default_girl.csv
```

이 방식으로 바꾼 이유:

- 실제 입 모양은 하나의 morph로 만들어지지 않는다.
- A, E, M/B/P 같은 소리는 jaw, lip open, wide, close 계열이 조합되어야 한다.
- 캐릭터 mesh마다 자연스러운 값이 다르므로 CSV로 반복 튜닝해야 한다.
- C++ 재컴파일 없이 디버그 UI에서 수정/저장할 수 있어야 한다.

추가로 post-last-viseme release를 넣었다.

```text
마지막 viseme 이후 LipSyncPostLastVisemeReleaseSeconds 동안 weight fade-out
기본값: 0.18s
```

이유:

- 마지막 입 모양이 tail 구간에서 굳어 보이는 문제를 줄인다.
- 서버 trim이 실패하거나 provider가 바뀌어도 클라이언트에서 방어한다.

## 6. Face Preset, Lip Sync, Idle Layer 분리

초기에는 표정과 립싱크가 같은 morph를 덮어쓸 위험이 컸다. 현재는 레이어를 나누었다.

```text
FacePresetLayer
-> emotion preset

FaceLipSyncLayer
-> viseme mouth shape

FaceIdleLayer
-> blink / idle expression

FaceSpeechMicroLayer
-> speaking 중 미세 표정
```

이 방식으로 바꾼 이유:

- 말하는 중 표정이 완전히 멈추면 캐릭터가 죽어 보인다.
- 반대로 emotion mouth와 lip-sync mouth가 동시에 강하게 들어가면 입이 망가진다.
- `lip_sync_mask`로 말하는 중 mouth expression을 일부 억제한다.
- blink, idle, micro-expression은 서버 latency와 무관하게 로컬에서 돌아야 한다.

## 7. Character Profile Routing

초기에는 한 캐릭터 톤으로만 응답했다. 현재는 8개 성격 preset을 지원한다.

```text
E/I: 밝고 쾌활함 <-> 차분함
F/T: 공감 우선 <-> 분석 우선
N/S: 상상력 풍부 <-> 현실감 우선
```

서버는 character profile을 prompt로 변환하고, 짧은 social input은 nano 모델로 라우팅한다.

이 방식으로 바꾼 이유:

- 같은 질문이라도 캐릭터별 답변 차이가 있어야 한다.
- 짧은 일상 대화는 고성능 모델보다 저지연 모델이 더 적합하다.
- session consistency를 유지하면서 latency를 줄여야 한다.
- matrix test로 캐릭터별 응답 차이와 fallback rate를 검증할 수 있다.

## 8. STT: Batch에서 Streaming으로 확장

초기 음성 입력은 batch STT였다.

```text
PTT 종료
-> PCM을 WAV로 묶음
-> POST /api/runtime/stt/transcribe
-> STT 완료 후 LLM 시작
```

이 방식은 안정적이지만 PTT를 뗀 뒤 STT 시간이 그대로 체감 지연에 포함된다.

현재는 Phase 1 streaming STT 경로를 추가했다.

```text
PTT 시작
-> /ws/stt 연결
-> PCM chunk를 binary WebSocket으로 전송
-> Azure streaming STT partial/final 수신
-> final transcript로 기존 turn/async 실행
```

현재 streaming STT는 final-only다.

- partial transcript는 로그/UI 관측용이다.
- partial 기반 LLM 선시작은 아직 하지 않는다.
- 기존 batch STT는 fallback/비교용으로 유지한다.

이 방식으로 바꾼 이유:

- PTT release 이후 STT 대기 시간을 줄일 수 있다.
- 기존 turn/async, TTS segment queue, lip-sync 구조를 유지할 수 있다.
- OpenAI Realtime API처럼 전체 아키텍처를 갈아엎지 않아도 된다.
- Azure TTS를 이미 사용 중이므로 Azure Speech streaming STT가 현실적인 1차 provider다.

주의할 점:

- WebSocket 연결 전 PCM chunk가 유실되지 않도록 pending chunk buffer를 둔다.
- WebSocket close 중 in-flight 상태면 error event로 UI 상태를 복구한다.
- VAD는 Thinking/Transcribing 중 자동 재입력을 차단한다.

## 9. Input Guard와 Barge-In 정책

초기에는 중복 입력을 stale response guard로만 막았다. 현재는 입력 단계에서 중복 submit을 줄인다.

현재 정책:

```text
Transcribing / Thinking 중 새 PTT submit 차단
Streaming STT in-flight 중 새 submit 차단
VAD는 Idle/Listening 상태에서만 새 발화 시작
TTS 중 barge-in은 별도 정책으로 분리
```

이 방식으로 바꾼 이유:

- stale guard는 크래시는 막지만 서버 비용은 이미 발생한다.
- 모바일 사용자는 버튼을 연타하거나 실수로 두 번 누를 수 있다.
- VAD는 주변 소리나 스피커 잔향을 입력으로 오인할 수 있다.
- 배포 기준에서는 "버려지는 요청"보다 "애초에 받지 않는 요청"이 더 안전하다.

## 10. Android 배포 관점

Android에서는 PIE와 다른 문제가 생긴다.

- `localhost`는 PC가 아니라 폰 자기 자신이다.
- `RECORD_AUDIO` 권한이 실제로 떠야 한다.
- `INTERNET` 권한과 서버 URL이 맞아야 한다.
- `IVoiceCapture`가 Android에서 정상 PCM을 주는지 확인해야 한다.
- `USoundWaveProcedural + SpawnSound2D`가 실기기에서 안정적으로 재생되는지 확인해야 한다.
- WebSocket이 모바일 네트워크에서 끊겼을 때 상태 복구가 되어야 한다.

따라서 Play Store 전에 다음 순서가 필요하다.

```text
1. PC PIE에서 batch PTT 테스트
2. PC PIE에서 streaming STT 테스트
3. Android Development APK 빌드
4. 실기기에서 batch PTT 테스트
5. 실기기에서 streaming STT 테스트
6. Play Console internal testing
7. Closed testing
8. Production release
```

## 현재 남은 주요 리스크

### 1. 실제 마이크 end-to-end 미검증

debug WAV로 STT/TTS/립싱크 체인은 검증했지만 실제 마이크는 별도 검증이 필요하다.

확인해야 할 것:

- PTT press/release 이벤트가 한 번만 들어오는지
- 실제 PCM이 충분히 수집되는지
- Android에서 권한 이후 capture가 정상 동작하는지
- streaming STT가 초반 음절을 잃지 않는지

### 2. Android 오디오 재생 미검증

PC PIE에서 segment queue가 동작해도 Android에서 같은 방식으로 재생된다고 보장할 수 없다.

확인해야 할 것:

- WAV segment 순차 재생
- lip-sync timeline start timing
- TTS 중 mic cooldown
- 스피커 출력이 마이크로 다시 들어오는 echo loop

### 3. Streaming STT provider 실측

Azure streaming STT 구조는 붙었지만 실제 latency와 recognition quality는 현장 테스트가 필요하다.

측정해야 할 것:

```text
speech_start_ms
speech_end_ms
streaming_final_ms
llm_ready_ms
tts_first_segment_ready_ms
audio_play_start_ms
```

### 4. 립싱크 세부 품질

trailing silence는 해결했다. 남은 것은 캐릭터별 튜닝이다.

필요할 때만 진행할 것:

- consecutive same ID dip
- per-ID scale
- jaw/open 계열 CSV weight 조정
- viseme provider 변경 대응

## 다음 단계

우선순위:

```text
1. 실제 마이크 PTT end-to-end 테스트
2. Android Development 패키징
3. Android 실기기 smoke test
4. batch STT와 streaming STT latency 비교
5. Play Console internal testing 업로드
6. 모바일 UI 정리
7. 립싱크 세부 튜닝
8. partial transcript 기반 prewarm/speculative LLM 검토
```

지금 프로젝트의 핵심은 더 이상 "LLM 응답을 받아 말하게 하는 것"이 아니다. 현재의 핵심은 **입력, 반응, 음성, 얼굴, 모바일 실행을 끊김 없이 연결해 실제 대화처럼 느끼게 하는 것**이다.
