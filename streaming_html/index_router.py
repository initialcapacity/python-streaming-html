import logging
import os
import queue
import threading
from time import sleep
from typing import Annotated

import requests
from fastapi import APIRouter, Request, Form
from starlette.responses import StreamingResponse, HTMLResponse

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
logging.basicConfig(level=logging.INFO, handlers=[handler, logging.StreamHandler()])

class Agent:
    def __init__(self, api_key: str, logs: queue.Queue, done: threading.Event):
        self.api_key = api_key
        self.logs = logs
        self.done = done
        self.result = None

    def reset(self):
        self.logs.queue.clear()
        self.done.clear()
        self.result = None

    def get_chat_response(self, prompt: str):
        self.logs.put("Getting chat response...")
        response = requests.post(
            url="https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "gpt-4.1", "input": prompt}
        )

        if response.status_code != 200:
            print(response.text)
            raise Exception(f"Status code: {response.status_code}")

        self.logs.put(f"Received chat response: {response.text}")
        response_json = response.json()
        print(response_json)
        self.result = response_json["output"][0]["content"][0]["text"]
        self.logs.put("Stream completed")
        self.done.set()



def index_router() -> APIRouter:
    router = APIRouter()

    @router.get("/")
    def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request=request, name="index.html" )

    @router.post("/", response_class=StreamingResponse)
    def query(user_query: Annotated[str, Form()]) -> StreamingResponse:
        agent = Agent(api_key=api_key, logs=log_queue, done=done_event)
        agent.reset()

        threading.Thread(target=agent.get_chat_response, args=(user_query,), daemon=True).start()

        template = templates.env.get_template("response.html")

        def stream():
            yield template.module.page_start(query=user_query)

            while not agent.done.is_set() or not agent.logs.empty():
                try:
                    log = agent.logs.get(timeout=.25)
                    yield template.module.log_lines(log=log)
                except queue.Empty:
                    yield template.module.log_lines(log="...")
                    sleep(.25)

            yield template.module.result(result=agent.result)

            yield template.module.page_end()

        return StreamingResponse(stream(), media_type="text/html")

    return router
