from kiln_bench._platform import run
from kiln_bench.sse import iter_sse_data


async def _lines(*lines):
    for line in lines:
        yield line


def collect(*lines):
    async def go():
        return [event async for event in iter_sse_data(_lines(*lines))]

    return run(go())


def test_one_data_line_per_event():
    assert collect("data: a", "", "data: b", "") == ["a", "b"]


def test_multi_line_data_is_joined_with_newlines():
    assert collect("data: first", "data: second", "") == ["first\nsecond"]


def test_comments_and_other_fields_are_ignored():
    assert collect(": keep-alive", "event: message", "id: 7", "data: x", "") == ["x"]


def test_crlf_endings_and_missing_final_blank_line():
    assert collect("data: a\r", "\r", "data: b") == ["a", "b"]


def test_space_after_colon_is_optional():
    assert collect("data:x", "", "data:  y", "") == ["x", " y"]
