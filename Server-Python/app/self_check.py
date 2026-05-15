import asyncio

from app.dependencies import get_motion_generation_service


async def main() -> None:
    service = get_motion_generation_service()
    prompt = "웃으면서 오른손으로 손 흔들어줘"
    motion_spec, gesture = await service.generate_procedural(prompt, "ue5_manny")
    export = await service.generate_enriched_prompt(prompt, "ue5_manny", motion_spec)

    assert motion_spec.gesture == "wave"
    assert gesture.gesture == "wave"
    assert export.original_prompt == prompt
    assert "right hand" in export.enriched_prompt
    print("self-check ok")


if __name__ == "__main__":
    asyncio.run(main())

