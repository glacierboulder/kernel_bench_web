"""Bounded, inspect-first recovery policy shared by CLI adapters."""
from dataclasses import dataclass


STOP_REASONS = {"safety_refusal", "authentication_failure", "cancelled",
                "budget_exhausted", "unknown_error", "repeated_tool_refusal"}


@dataclass
class RecoveryBudget:
    total_limit: int = 2
    tool_refusal_limit: int = 1
    used_total: int = 0
    used_tool_refusal: int = 0

    def decide(self, reason: str, *, process_exited: bool, session_id: str | None,
               result_known: bool = True) -> dict:
        if reason in STOP_REASONS:
            return {"action":"stop","reason":reason}
        if not process_exited:
            return {"action":"wait_for_exit","reason":"original_process_still_running"}
        if reason == "unknown_connection" or not result_known:
            return {"action":"inspect","reason":"result_may_be_unknown"}
        if not session_id:
            return {"action":"stop","reason":"session_id_missing"}
        if reason == "tool_review_refusal":
            if self.used_tool_refusal >= self.tool_refusal_limit:
                return {"action":"stop","reason":"repeated_tool_refusal"}
            self.used_tool_refusal += 1
        elif reason not in {"rate_limit", "server_temporary_failure"}:
            return {"action":"stop","reason":"unknown_error"}
        if self.used_total >= self.total_limit:
            return {"action":"stop","reason":"recovery_budget_exhausted"}
        self.used_total += 1
        return {"action":"resume_session","session_id":session_id,
                "recovery_number":self.used_total,"reason":reason}
