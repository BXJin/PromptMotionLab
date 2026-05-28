# TTS-LIPSYNC-TIMELINE-PLAN - PromptMotionLab

Updated: 2026-05-13

---

## 0. 결론

TTS와 립싱크는 가능하다. 하지만 MVP의 어려운 지점은 "음성을 재생한다"가 아니라 아래 요소를 하나의 시간축에 맞추는 것이다.

```text
voice audio
lip sync / viseme
facial expression
gaze
head motion
pause
filler / backchannel
short gesture
```

따라서 이 기능은 단순 TTS 기능이 아니라 **Speech Timeline** 기능으로 설계한다.

---

## 1. 권장 MVP 선택

1차 MVP는 Azure Speech TTS + Azure viseme event를 우선 사용한다.

이유:

```text
- Python SDK로 서버에서 호출 가능
- SSML로 pause, rate, pitch 같은 발화 제어 가능
- TTS 결과와 함께 viseme id + audio offset을 받을 수 있음
- 입모양 timing을 별도 추정하지 않아도 됨
- MVP에서 음성/입모양 정합성을 가장 빠르게 검증 가능
```

ElevenLabs는 2차 품질 개선 후보로 둔다.

```text
- 음성 자연스러움과 캐릭터성은 강점
- streaming TTS와 저지연 모델이 있음
- 단, Azure처럼 viseme event가 바로 붙는 구조는 아니므로 립싱크는 별도 엔진이 필요할 수 있음
```

Audio2Face는 고품질 후보지만 MVP 기본 경로는 아니다.

```text
- 오디오 기반 facial animation 품질이 강점
- Unreal ACE plugin / Audio2Face 경로가 있음
- GPU, 플러그인, 세팅 의존성이 커서 초기 MVP에는 무거움
```

---

## 2. Provider 비교

| 항목 | Azure Speech TTS | ElevenLabs | NVIDIA Audio2Face | OVR LipSync |
|---|---|---|---|---|
| 역할 | TTS + viseme timing | 고품질/저지연 TTS | 오디오 기반 facial animation | 오디오 기반 lightweight lip sync |
| Python 서버 호출 | 가능 | 가능 | 서비스/SDK 구성 필요 | 보통 클라이언트/플러그인 중심 |
| 립싱크 데이터 | viseme id + audio offset | 별도 처리 필요 | facial animation/blendshape 생성 | viseme 추정 |
| MVP 적합도 | 높음 | 중간 | 낮음 | 중간 |
| 고품질 확장 | 중간 | 높음 | 높음 | 중간 |
| 주요 리스크 | voice 품질/스타일 한계 | 립싱크 별도 파이프라인 | 세팅/성능/의존성 | 표정 전체 표현력 낮음 |

---

## 3. Speech Timeline Contract

서버는 단순 audio file만 반환하지 않는다. 음성과 캐릭터 반응이 같은 시간축에 올라간 결과를 반환한다.

```json
{
  "utteranceId": "utt_001",
  "audio": {
    "url": "/api/audio/utt_001.wav",
    "durationSeconds": 3.2,
    "format": "wav"
  },
  "segments": [
    {
      "start": 0.0,
      "duration": 0.8,
      "text": "음...",
      "pauseAfter": 0.25,
      "expression": { "preset": "thinking", "intensity": 0.55 },
      "gaze": { "target": "down_left", "stability": 0.5 },
      "head": { "tilt": 0.12, "nod": 0.0 },
      "gesture": { "name": "hesitate_small", "intensity": 0.25 }
    }
  ],
  "visemes": [
    { "time": 0.12, "id": 1, "weight": 1.0 },
    { "time": 0.21, "id": 5, "weight": 1.0 }
  ]
}
```

`segments`는 Behavior Planner가 만든다. `visemes`는 TTS/lip-sync provider가 만든다.

---

## 4. Layer Responsibility

TTS가 표정 전체를 결정하면 안 된다. 각 layer의 책임을 분리한다.

```text
LLM / Behavior Planner
- 답변 텍스트
- 감정
- 의도
- 확신도
- 표정 preset
- 시선
- 고개 반응
- pause / filler
- 짧은 gesture

TTS Provider
- 실제 음성 생성
- 말의 속도, 톤, pause
- audio file 또는 stream

Lip Sync Provider
- 입모양 timing
- viseme id 또는 morph target weight

Unreal Runtime
- audio playback
- viseme -> mouth morph 적용
- expression morph blending
- eye/head/gaze 적용
- gesture layer 적용
- 모든 layer의 우선순위와 blending 처리
```

---

## 5. Unreal 합성 우선순위

Unreal에서는 얼굴 제어가 서로 충돌할 수 있으므로 우선순위를 둔다.

```text
1. Lip sync layer
   - jaw, mouth open/close, V_ viseme morph

2. Expression layer
   - smile, thinking, concern, surprise
   - mouth corner/cheek/brow 계열
   - lip sync와 같은 morph를 직접 덮어쓰지 않도록 weight 제한

3. Eye/Gaze layer
   - eye bone rotation
   - blink morph
   - look target

4. Head layer
   - nod, tilt, look follow

5. Body/Gesture layer
   - small_ack, explain_small, hesitate, point_soft
```

표정 layer와 립싱크 layer가 같은 mouth morph를 동시에 강하게 제어하면 입모양이 깨진다. CC4 캐릭터에서는 morph 이름별 역할 분리가 반드시 필요하다.

---

## 6. 단계별 구현 계획

### Phase 1 - Offline Azure TTS + Viseme

```text
서버:
- Azure Speech SDK 연결
- SSML 입력 생성
- wav 파일 저장
- viseme event 수집
- SpeechTimeline JSON 반환

Unreal:
- audio file 다운로드/재생
- viseme id -> CC4 V_ morph mapping
- time offset 기준으로 SetMorphTarget 적용
```

완료 기준:

```text
"음... 다시 생각해보니까 아니네요."
-> 음성이 재생됨
-> 입모양이 audio offset 기준으로 움직임
-> pause에서 입이 닫힘
```

### Phase 2 - Behavior Segment Sync

```text
서버:
- answer text를 의미 단위 segment로 분리
- filler/pause 삽입
- expression/gaze/head를 segment에 배치
- TTS용 SSML과 Behavior Timeline을 같은 segment 기준으로 생성

Unreal:
- segment start/duration 기준으로 표정/시선/고개 layer 실행
- viseme는 audio offset 기준으로 별도 실행
```

완료 기준:

```text
말하는 내용이 바뀔 때 표정과 시선도 같이 바뀜
pause 구간에서 thinking expression과 gaze away가 유지됨
```

### Phase 3 - Streaming 검토

```text
목표:
- 긴 답변에서 첫 음성 시작 지연을 줄임

검토:
- Azure streaming 가능 범위
- ElevenLabs streaming TTS
- segment 단위 prefetch
- 자주 쓰는 filler audio cache
```

완료 기준:

```text
첫 segment는 빠르게 재생되고,
뒤 segment는 생성/다운로드 중에도 끊기지 않게 이어짐
```

### Phase 4 - ElevenLabs 품질 비교

```text
서버:
- ElevenLabsTTSProvider 추가
- 같은 Behavior Timeline에 Azure 음성과 ElevenLabs 음성을 교체 적용

립싱크:
- Azure viseme를 계속 사용할 수 있는지 검토
- 아니면 OVR LipSync / Audio2Face로 별도 추출
```

완료 기준:

```text
Azure 대비 ElevenLabs가 캐릭터성/자연스러움에서 이득이 있는지 비교 가능
```

### Phase 5 - Audio2Face 고품질 실험

```text
목표:
- 고품질 facial animation이 필요한 데모용 옵션 검토

작업:
- NVIDIA ACE / Audio2Face Unreal 경로 조사
- CC4 morph target과 출력 blendshape 매핑 가능성 확인
- GPU/성능/배포 리스크 기록
```

완료 기준:

```text
Audio2Face가 MVP 기본 경로보다 품질 이득이 충분한지 판단
```

---

## 7. TTS 기계 느낌 줄이는 원칙

```text
- 너무 긴 문장을 한 번에 보내지 않는다.
- 의미 단위 segment로 나눈다.
- 너무 잘게 쪼개서 억양이 끊기지 않게 previous/next context를 준다.
- SSML로 pause, rate, pitch를 조절한다.
- "음...", "아", "그렇죠" 같은 filler를 캐릭터별 style로 제한해서 쓴다.
- 자주 쓰는 filler audio는 cache한다.
- 말하지 않는 동안에도 blink/gaze/head idle layer를 유지한다.
- TTS 감정만 믿지 않고 Behavior JSON의 expression layer를 별도로 유지한다.
```

---

## 8. 공식 참고

```text
Azure Speech TTS Python quickstart:
https://learn.microsoft.com/en-us/azure/ai-services/speech-service/get-started-text-to-speech

Azure Speech viseme events:
https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-speech-synthesis-viseme

Azure Python viseme event args:
https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.speechsynthesisvisemeeventargs

ElevenLabs Text to Speech:
https://elevenlabs.io/docs/overview/capabilities/text-to-speech

ElevenLabs streaming API:
https://elevenlabs.io/docs/api-reference/text-to-speech/stream

NVIDIA ACE Unreal Plugin:
https://docs.nvidia.com/ace/ace-unreal-plugin/
```

## Current Server Implementation

Implemented server endpoints:

```text
POST /api/runtime/tts/synthesize
GET /api/runtime/audio/{utteranceId}.wav
```

Current provider structure:

```text
TtsProvider
- AzureSpeechTtsProvider
- MockTtsProvider
```

Azure is selected only when these environment variables are present:

```text
AZURE_SPEECH_KEY
AZURE_SPEECH_REGION
AZURE_TTS_VOICE
```

Without Azure credentials or SDK support, the server returns a silent mock WAV.
This is intentional so Unreal audio download/playback and lip-sync code can be
implemented before cloud credentials are available.

Current response shape:

```json
{
  "speechTimeline": {
    "utteranceId": "utt_001",
    "audio": {
      "url": "/api/runtime/audio/utt_001.wav",
      "durationSeconds": 1.2,
      "format": "wav"
    },
    "visemes": [
      { "time": 0.12, "id": 1, "weight": 1.0 }
    ],
    "provider": "AzureSpeechTtsProvider",
    "model": "en-US-JennyNeural",
    "ttsLatencyMs": 420
  }
}
```

Next Unreal task:

```text
download wav
-> play with AudioComponent
-> use audio playback time to drive viseme morph targets
```
