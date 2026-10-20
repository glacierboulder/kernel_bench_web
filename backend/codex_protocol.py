"""Parser for Codex CLI ``codex exec --json`` JSONL events."""
from __future__ import annotations

import json
import uuid


class CodexStream:
    MAX_LINE_BYTES = 1024 * 1024

    def __init__(self):
        self.thread_id = None
        self.events = 0
        self.malformed_lines = 0
        self.output_truncated = False
        self.turns = 0
        self.completed = False
        self.failed = False
        self.failure_type = None
        self.recovery_reason = None
        self.last_message = None
        self.usage = {"input_tokens": 0, "cached_input_tokens": 0,
                      "output_tokens": 0, "reasoning_output_tokens": 0}
        self.usage_observed = False

    def feed(self, line: str | bytes) -> dict | None:
        raw = line.encode("utf-8") if isinstance(line, str) else line
        if len(raw) > self.MAX_LINE_BYTES:
            self.malformed_lines += 1
            self.output_truncated = True
            return None
        try:
            event = json.loads(raw)
        except (json.JSONDecodeError, UnicodeError):
            self.malformed_lines += 1
            return None
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            self.malformed_lines += 1
            return None
        self.events += 1
        event_type = event["type"]
        if event_type == "thread.started":
            identity = event.get("thread_id")
            try:
                parsed = str(uuid.UUID(identity)) if isinstance(identity, str) else None
            except (ValueError, AttributeError):
                parsed = None
            if parsed is None or (self.thread_id and parsed != self.thread_id):
                self.failed = True
                self.failure_type = "invalid_or_changed_session_id"
            else:
                self.thread_id = parsed
        elif event_type == "turn.completed":
            self.turns += 1
            usage = event.get("usage")
            if isinstance(usage, dict):
                self.usage_observed = True
                for key in self.usage:
                    value = usage.get(key)
                    if isinstance(value, int) and value >= 0:
                        self.usage[key] += value
            self.completed = True
        elif event_type == "turn.failed":
            self.failed = True
            self.failure_type = "turn_failed"
            self.recovery_reason=self._recovery_reason(event)
        elif event_type == "error":
            self.failed = True
            self.failure_type = "cli_error"
            self.recovery_reason=self._recovery_reason(event)
        elif event_type == "item.completed":
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message":
                message = item.get("text")
                if isinstance(message, str):
                    self.last_message = message
        return {"type": event_type}

    @staticmethod
    def _recovery_reason(event: dict) -> str | None:
        """Accept only explicit machine-readable transient/refusal categories."""
        value=event.get("recovery_reason")
        if isinstance(value,str) and value in {"rate_limit","server_temporary_failure","tool_review_refusal",
                     "unknown_connection","safety_refusal","authentication_failure",
                     "cancelled","budget_exhausted"}:
            return value
        info=event.get("codexErrorInfo")
        if isinstance(info,dict):
            code=info.get("code")
            status=info.get("httpStatusCode")
            if code in {"rate_limit_exceeded","rate_limited"} or status==429:
                return "rate_limit"
            if code in {"server_error","temporarily_unavailable"} or status in {500,502,503,504}:
                return "server_temporary_failure"
            if code in {"safety_refusal","content_filter"}:
                return "safety_refusal"
            if code in {"invalid_api_key","authentication_error","unauthorized"} or status in {401,403}:
                return "authentication_failure"
        return None

    def finish(self, return_code: int | None) -> dict:
        if return_code is not None and return_code != 0:
            status = "failed"
        elif self.failed:
            status = "failed"
        elif self.malformed_lines:
            status = "protocol_error"
        elif self.completed:
            status = "completed"
        else:
            status = "missing_result"
        return {"status": status, "session_id": self.thread_id,
                "event_count": self.events, "malformed_lines": self.malformed_lines,
                "output_truncated": self.output_truncated, "turns": self.turns,
                "usage": dict(self.usage) if self.usage_observed else None,
                "usage_observed": self.usage_observed,
                # Codex JSONL usage reports token totals by turn; it does not
                # establish an API request count.
                "api_request_count": None, "failure_type": self.failure_type,
                "recovery_reason":self.recovery_reason,"last_message": self.last_message}
