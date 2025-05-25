import os

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from streaming_html.index_router import index_router


def create_app() -> FastAPI:
    app = FastAPI()

    app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
    app.include_router(index_router())
    return app
