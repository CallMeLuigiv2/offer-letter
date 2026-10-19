"""One error type for the API: a status code and a plain sentence that says what to do."""

from __future__ import annotations


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message
