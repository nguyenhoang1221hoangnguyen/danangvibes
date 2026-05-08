from __future__ import annotations

from fastapi import FastAPI

from processing_web.routes import router

app = FastAPI(title="DaNang Vibes Processing App")
app.include_router(router)
