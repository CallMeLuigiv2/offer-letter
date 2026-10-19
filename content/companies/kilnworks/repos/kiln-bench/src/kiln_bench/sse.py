"""Minimal Server-Sent Events parsing for OpenAI-style streams."""

from collections.abc import AsyncIterable, AsyncIterator

DONE = "[DONE]"


async def iter_sse_data(lines: AsyncIterable[str]) -> AsyncIterator[str]:
    """Yield the data payload of each event in an SSE stream.

    ``lines`` is the body split into lines without their line endings
    (``httpx.Response.aiter_lines()`` gives exactly that). An event ends at
    a blank line; several ``data:`` lines in one event are joined with a
    newline, as the SSE spec says. Comment lines (starting with ``:``) and
    the ``event``, ``id`` and ``retry`` fields are ignored.
    """
    buf: list[str] = []
    async for raw in lines:
        line = raw.rstrip("\r")
        if not line:
            if buf:
                yield "\n".join(buf)
                buf = []
            continue
        if line.startswith(":"):
            continue
        name, _, value = line.partition(":")
        if name != "data":
            continue
        buf.append(value[1:] if value.startswith(" ") else value)
    if buf:
        yield "\n".join(buf)
