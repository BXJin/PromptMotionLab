from fastapi import FastAPI

from app.api.routes import router


app = FastAPI(
    title="PromptMotionLab Server",
    version="0.1.0",
    description="MotionSpec, procedural gesture, and prompt export backend.",
)

app.include_router(router)

