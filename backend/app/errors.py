"""统一异常：业务代码只抛 AppError，由 main.py 的 handler 转成 {code,message,trace_id}。"""

from __future__ import annotations


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def not_found(what: str, key: str) -> AppError:
    return AppError(f"{what.upper()}_NOT_FOUND", f"{what} 不存在：{key}", 404)


def state_conflict(current: str, allowed: str) -> AppError:
    return AppError(
        "ALERT_STATE_CONFLICT",
        f"当前状态为 {current}，只允许从 {allowed} 流转",
        409,
    )
