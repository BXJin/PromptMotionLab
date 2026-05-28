import asyncio
import logging
import wave
from pathlib import Path

from app.contracts.runtime_behavior import RuntimeTtsStyle
from app.contracts.speech_timeline import SpeechViseme
from app.providers.tts.base import TtsProvider, TtsResult
from app.providers.tts.wav_trim import trim_wav_file_to_duration

logger = logging.getLogger(__name__)


class AzureSpeechTtsProvider(TtsProvider):
    provider_name = "AzureSpeechTtsProvider"

    def __init__(
        self,
        *,
        speech_key: str,
        speech_region: str,
        default_voice: str = "en-US-JennyNeural",
        korean_voice: str = "ko-KR-SunHiNeural",
        viseme_trim_tail_seconds: float = 0.15,
    ) -> None:
        if not speech_key.strip():
            raise ValueError("speech_key is required")
        if not speech_region.strip():
            raise ValueError("speech_region is required")
        self._speech_key = speech_key
        self._speech_region = speech_region
        self._default_voice = default_voice
        self._korean_voice = korean_voice
        self._viseme_trim_tail_seconds = max(0.0, viseme_trim_tail_seconds)

    @property
    def model_name(self) -> str:
        return self._default_voice

    async def synthesize(
        self,
        *,
        text: str,
        output_path: Path,
        tts_style: RuntimeTtsStyle,
        voice: str | None = None,
    ) -> TtsResult:
        return await asyncio.to_thread(
            self._synthesize_sync,
            text,
            output_path,
            tts_style,
            voice or self._select_voice(text),
        )

    def _synthesize_sync(
        self,
        text: str,
        output_path: Path,
        tts_style: RuntimeTtsStyle,
        voice: str,
    ) -> TtsResult:
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError as exc:
            raise RuntimeError("azure-cognitiveservices-speech is not installed") from exc

        output_path.parent.mkdir(parents=True, exist_ok=True)
        speech_config = speechsdk.SpeechConfig(subscription=self._speech_key, region=self._speech_region)
        speech_config.speech_synthesis_voice_name = voice
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
        )
        audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_path))
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        visemes: list[SpeechViseme] = []

        def on_viseme(event) -> None:
            visemes.append(
                SpeechViseme(
                    time=event.audio_offset / 10_000_000,
                    id=int(event.viseme_id),
                    weight=1.0,
                )
            )

        synthesizer.viseme_received.connect(on_viseme)
        result = synthesizer.speak_ssml_async(self._build_ssml(text, tts_style, voice)).get()

        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            cancellation = speechsdk.SpeechSynthesisCancellationDetails.from_result(result)
            raise RuntimeError(f"Azure TTS failed: {cancellation.reason} {cancellation.error_details}")

        duration_seconds = self._duration_from_wav(output_path)
        if visemes and self._viseme_trim_tail_seconds > 0.0:
            trim_at_seconds = visemes[-1].time + self._viseme_trim_tail_seconds
            try:
                trim_result = trim_wav_file_to_duration(output_path, trim_at_seconds)
                duration_seconds = trim_result.trimmed_duration_seconds
                if trim_result.trimmed:
                    logger.info(
                        "Azure TTS WAV viseme trim applied. original=%.3fs trimmed=%.3fs last_viseme=%.3fs tail=%.3fs path=%s",
                        trim_result.original_duration_seconds,
                        trim_result.trimmed_duration_seconds,
                        visemes[-1].time,
                        self._viseme_trim_tail_seconds,
                        output_path,
                    )
            except (OSError, EOFError, wave.Error) as exc:
                logger.warning("Azure TTS WAV viseme trim skipped. path=%s error=%s", output_path, exc)

        return TtsResult(
            audio_path=output_path,
            duration_seconds=duration_seconds,
            visemes=visemes,
            provider=self.provider_name,
            model=voice,
        )

    def _build_ssml(self, text: str, tts_style: RuntimeTtsStyle, voice: str) -> str:
        rate, pitch = self._style_to_prosody(tts_style)
        escaped = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )
        xml_lang = self._voice_to_locale(voice)
        return (
            f"<speak version='1.0' xml:lang='{xml_lang}' "
            "xmlns='http://www.w3.org/2001/10/synthesis'>"
            f"<voice name='{voice}'>"
            f"<prosody rate='{rate}' pitch='{pitch}'>{escaped}</prosody>"
            "</voice></speak>"
        )

    def _select_voice(self, text: str) -> str:
        if any("\uac00" <= char <= "\ud7a3" for char in text):
            return self._korean_voice
        return self._default_voice

    def _voice_to_locale(self, voice: str) -> str:
        parts = voice.split("-")
        if len(parts) >= 2:
            return f"{parts[0]}-{parts[1]}"
        return "en-US"

    def _style_to_prosody(self, tts_style: RuntimeTtsStyle) -> tuple[str, str]:
        if tts_style == RuntimeTtsStyle.CAREFUL:
            return "-8%", "-2%"
        if tts_style == RuntimeTtsStyle.ENERGETIC:
            return "+5%", "+2%"
        if tts_style == RuntimeTtsStyle.NEUTRAL:
            return "0%", "0%"
        return "-2%", "+0%"

    def _duration_from_wav(self, path: Path) -> float:
        with wave.open(str(path), "rb") as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
        return frames / float(rate)
