from time import sleep
from typing import List

from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse

from streaming_html.templates import templates


def index_router() -> APIRouter:
    router = APIRouter()

    def stream_content(request: Request, messages: List[str]):
        template = templates.env.get_template("index.html")

        yield template.module.layout(request)

        for message in messages:
            sleep(1)
            yield template.module.message(message)

        yield template.module.close_messages()
        yield template.module.end_page()

    @router.get("/", response_class=StreamingResponse)
    def index(request: Request) -> StreamingResponse:
        messages = [
            "This is a FastAPI app",
            "It uses Jinja2 templating",
            "It's streaming HTML without using Javascript",
            "Pretty cool!"
        ]

        return StreamingResponse(stream_content(request, messages), media_type="text/html; charset=utf-8")

    return router