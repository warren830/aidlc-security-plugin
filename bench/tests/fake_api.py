"""A local stand-in for the Anthropic Messages API, so the real CLI runs offline.

Each request that offers tools is a main-loop turn and gets the next scripted
reply; any other request (a title, a summary) gets a short text. Every request
body is kept for the test to read.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def text(value: str) -> list[dict]:
    return [{"type": "text", "text": value}]


def tool_use(name: str, tool_input: dict, tool_id: str) -> list[dict]:
    return [{"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}]


class FakeApi:
    def __init__(self, replies: list[list[dict]]) -> None:
        self.replies = list(replies)
        self.requests: list[dict] = []
        self._lock = threading.Lock()
        api = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: object) -> None:
                pass

            def do_POST(self) -> None:
                body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
                if self.path.startswith("/v1/messages/count_tokens"):
                    self._json({"input_tokens": 10})
                    return
                content = api.next_reply(body)
                if body.get("stream"):
                    self._stream(body, content)
                else:
                    self._json(api.message(body, content))

            def do_GET(self) -> None:
                self.send_error(404)

            def _json(self, payload: dict) -> None:
                data = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _stream(self, body: dict, content: list[dict]) -> None:
                self.send_response(200)
                self.send_header("content-type", "text/event-stream")
                self.end_headers()
                message = api.message(body, [])
                self._event("message_start", {"type": "message_start", "message": message})
                for index, block in enumerate(content):
                    if block["type"] == "text":
                        self._event("content_block_start", {"type": "content_block_start", "index": index, "content_block": {"type": "text", "text": ""}})
                        delta = {"type": "text_delta", "text": block["text"]}
                    else:
                        start = {**block, "input": {}}
                        self._event("content_block_start", {"type": "content_block_start", "index": index, "content_block": start})
                        delta = {"type": "input_json_delta", "partial_json": json.dumps(block["input"])}
                    self._event("content_block_delta", {"type": "content_block_delta", "index": index, "delta": delta})
                    self._event("content_block_stop", {"type": "content_block_stop", "index": index})
                stop = "tool_use" if any(block["type"] == "tool_use" for block in content) else "end_turn"
                self._event("message_delta", {"type": "message_delta", "delta": {"stop_reason": stop, "stop_sequence": None}, "usage": {"output_tokens": 20}})
                self._event("message_stop", {"type": "message_stop"})

            def _event(self, name: str, payload: dict) -> None:
                self.wfile.write(f"event: {name}\ndata: {json.dumps(payload)}\n\n".encode())
                self.wfile.flush()

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def next_reply(self, body: dict) -> list[dict]:
        with self._lock:
            main_loop = bool(body.get("tools"))
            self.requests.append({"main_loop": main_loop, "body": body})
            if not main_loop:
                return text("ok")
            return self.replies.pop(0) if self.replies else text("Nothing more is scripted.")

    @staticmethod
    def message(body: dict, content: list[dict]) -> dict:
        return {
            "id": "msg_fake",
            "type": "message",
            "role": "assistant",
            "model": body.get("model", "fake"),
            "content": content,
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 1000, "output_tokens": 20, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
        }

    def main_loop_requests(self) -> list[dict]:
        return [request["body"] for request in self.requests if request["main_loop"]]

    def close(self) -> None:
        self.server.shutdown()
