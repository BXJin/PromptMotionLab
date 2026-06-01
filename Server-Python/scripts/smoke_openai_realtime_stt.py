import asyncio
import argparse
import os
import wave

from app.providers.stt.openai_realtime_streaming_provider import OpenAiRealtimeStreamingSttProvider


async def main(wav_path: str | None = None) -> None:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("openai_api_key")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    provider = OpenAiRealtimeStreamingSttProvider(
        api_key=api_key,
        endpoint=os.getenv("OPENAI_REALTIME_STT_ENDPOINT", "wss://api.openai.com/v1/realtime?intent=transcription"),
        model=os.getenv("OPENAI_REALTIME_STT_MODEL", "gpt-4o-mini-transcribe"),
        delay=os.getenv("OPENAI_REALTIME_STT_DELAY", "low"),
    )
    sample_rate = 24000
    pcm = b""
    if wav_path:
        with wave.open(wav_path, "rb") as wav:
            if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
                raise RuntimeError("WAV must be mono PCM16")
            sample_rate = wav.getframerate()
            pcm = wav.readframes(wav.getnframes())

    session = provider.create_session(language="ko-KR", sample_rate=sample_rate)
    await session.start()
    if pcm:
        for offset in range(0, len(pcm), 3200):
            await session.write(pcm[offset : offset + 3200])
            await asyncio.sleep(0.02)
    await session.stop()
    final_text = ""
    while True:
        event = await session.next_event(timeout_seconds=0.1)
        if event is None:
            break
        if event.type == "final":
            final_text = event.text
        if event.type == "error":
            raise RuntimeError(event.error)
    if pcm and not final_text:
        raise RuntimeError("OpenAI realtime STT returned no final transcript")
    print("openai realtime stt websocket ok")
    if final_text:
        print(f"final transcript: {final_text}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wav", help="Optional mono PCM16 WAV path for real transcription smoke test")
    args = parser.parse_args()
    asyncio.run(main(args.wav))
