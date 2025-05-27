import logging
import os
import queue
import threading
from time import sleep
from typing import List

import requests
from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse

from streaming_html.templates import templates

log_queue: queue.Queue[str] = queue.Queue()
done_event: threading.Event = threading.Event()

api_key = os.environ.get("OPEN_AI_KEY")


class QueueHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        log_queue.put(self.format(record))


logger = logging.getLogger('streaming_html')
logger.setLevel(logging.DEBUG)
handler = QueueHandler()
logging.basicConfig(level=logging.DEBUG, handlers=[handler, logging.StreamHandler()])

agent_result: List[str] = []


def index_router() -> APIRouter:
    router = APIRouter()

    def get_chat_response(prompt: str):
        logger.info("Getting chat response...")
        response = requests.post(
            url="https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "gpt-4.1", "input": prompt}
        )

        if response.status_code != 200:
            print(response.text)
            raise Exception(f"Status code: {response.status_code}")

        logger.info(f"Received chat response: {response.text}")
        response_json = response.json()
        agent_result.append(response_json)
        logger.info("Stream completed")
        done_event.set()

    def tail_logs():
        while not done_event.is_set() or not log_queue.empty():
            try:
                log = log_queue.get(timeout=.25)
                yield f"{log}<br/>"
            except queue.Empty:
                yield "...\n"
                sleep(.25)

    @router.get("/", response_class=StreamingResponse)
    def index(request: Request) -> StreamingResponse:
        prompt = "Why is the sky blue?"

        done_event.clear()
        threading.Thread(target=get_chat_response, args=(prompt,), daemon=True).start()

        template = templates.env.get_template("index.html")

        stream = template.stream(
            request=request,
            prompt=prompt,
            logs=tail_logs(),
            agent_result=agent_result
        )

        return StreamingResponse(stream, media_type="text/html")

    return router
