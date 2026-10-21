// Sample Kilnworks data for the in-memory mock. All fictional.
import type { Outline, OutlineSymbol, Persona, Severity } from './types';

export const PERSONAS: Persona[] = [
  { id: 'kilnworks.dana', company_id: 'kilnworks', name: 'Dana Whitfield', role: 'Engineering manager', color: '#a6e3a1', pronouns: 'she/her' },
  { id: 'kilnworks.kenji', company_id: 'kilnworks', name: 'Kenji Mori', role: 'Tech lead', color: '#89b4fa', pronouns: 'he/him' },
  { id: 'kilnworks.ines', company_id: 'kilnworks', name: 'Ines Duarte', role: 'Senior engineer, GPU serving', color: '#f38ba8', pronouns: 'she/her' },
  { id: 'kilnworks.theo', company_id: 'kilnworks', name: 'Theo Lindqvist', role: 'Engineer', color: '#f9e2af', pronouns: 'he/him' },
  { id: 'kilnworks.amara', company_id: 'kilnworks', name: 'Amara Osei', role: 'Product manager', color: '#fab387', pronouns: 'she/her' },
  { id: 'kilnworks.leo', company_id: 'kilnworks', name: 'Leo Park', role: 'Intern', color: '#94e2d5', pronouns: 'he/him' },
];

// ---- the KLN-01 pull request -------------------------------------------------

type L = ['c' | 'a' | 'd', string];
const c = (t: string): L => ['c', t];
const a = (t: string): L => ['a', t];
const d = (t: string): L => ['d', t];

function hunk(oldStart: number, newStart: number, lines: L[]): string {
  const oldCount = lines.filter((l) => l[0] !== 'a').length;
  const newCount = lines.filter((l) => l[0] !== 'd').length;
  const body = lines.map(([k, t]) => (k === 'c' ? ' ' : k === 'a' ? '+' : '-') + t).join('\n');
  return `@@ -${oldStart},${oldCount} +${newStart},${newCount} @@\n${body}`;
}

const STATS_HUNK = hunk(1, 1, [
  c('"""Latency statistics for kiln-bench."""'),
  c(''),
  a('import math'),
  a(''),
  c(''),
  d('def summarize(latencies):'),
  d('    return {"mean": sum(latencies) / len(latencies)}'),
  a('def percentile(values, q):'),
  a('    """Return the q-th percentile (0-100) of values."""'),
  a('    ordered = sorted(values)'),
  a('    idx = int(len(ordered) * q / 100)'),
  a('    return ordered[idx]'),
  a(''),
  a(''),
  a('def summarize(latencies):'),
  a('    return {'),
  a('        "mean": sum(latencies) / len(latencies),'),
  a('        "p50": percentile(latencies, 50),'),
  a('        "p99": percentile(latencies, 99),'),
  a('    }'),
]);

const LOADGEN_HUNK = hunk(0, 1, [
  a('"""Load generator: send requests at a target rate and report latency."""'),
  a('import asyncio'),
  a('import time'),
  a(''),
  a('import httpx'),
  a(''),
  a('from .stats import summarize'),
  a(''),
  a('WARMUP_REQUESTS = 20'),
  a(''),
  a(''),
  a('async def one_request(client, url, payload):'),
  a('    start = time.time()'),
  a('    try:'),
  a('        resp = await client.post(url, json=payload, timeout=30)'),
  a('        resp.raise_for_status()'),
  a('    except httpx.HTTPError:'),
  a('        return None'),
  a('    return time.time() - start'),
  a(''),
  a(''),
  a('async def run(url, payload, rate, duration_s):'),
  a('    results = []'),
  a('    async with httpx.AsyncClient() as client:'),
  a('        end = time.time() + duration_s'),
  a('        while time.time() < end:'),
  a('            results.append(await one_request(client, url, payload))'),
  a('            await asyncio.sleep(1 / rate)'),
  a('    latencies = [r for r in results if r is not None]'),
  a('    return summarize(latencies)'),
]);

const TEST_HUNK = hunk(0, 1, [
  a('from kiln_bench.stats import summarize'),
  a(''),
  a(''),
  a('def test_summarize_mean():'),
  a('    assert summarize([1.0, 3.0])["mean"] == 2.0'),
]);

export const DIFF_FILES = [
  { path: 'kiln_bench/stats.py', old_path: 'kiln_bench/stats.py', status: 'modified', hunks_text: STATS_HUNK },
  { path: 'kiln_bench/loadgen.py', old_path: null, status: 'added', hunks_text: LOADGEN_HUNK },
  { path: 'tests/test_stats.py', old_path: null, status: 'added', hunks_text: TEST_HUNK },
];

export interface MockIssue {
  id: string;
  title: string;
  path: string;
  marker: string; // text of the first added line the issue sits on
  severity: Severity;
  explanation: string;
}

export const ISSUES: MockIssue[] = [
  {
    id: 'closed-loop',
    title: 'The loop waits for each reply, so slow replies hide themselves',
    path: 'kiln_bench/loadgen.py',
    marker: 'results.append(await one_request',
    severity: 'blocker',
    explanation:
      'The loop awaits each request before sending the next, so when the server slows down the generator slows down with it and the slow period is under-sampled. The target rate is never held. This is coordinated omission, and it makes p99 look better than a real user would see.',
  },
  {
    id: 'percentile-index',
    title: 'The percentile index runs off the end and is the max for small samples',
    path: 'kiln_bench/stats.py',
    marker: 'idx = int(len(ordered) * q / 100)',
    severity: 'major',
    explanation:
      'With q=100 the index equals len(ordered) and raises IndexError. With 50 samples, p99 gives index 49, which is just the maximum. Use the nearest-rank form: ceil(n * q / 100) - 1.',
  },
  {
    id: 'dropped-failures',
    title: 'Failed requests are dropped from the latency numbers',
    path: 'kiln_bench/loadgen.py',
    marker: 'return None',
    severity: 'major',
    explanation:
      'Errors return None and are filtered out before summarize, so a server that fails its slowest requests gets a better p99. Count errors separately and report an error rate next to the latency.',
  },
  {
    id: 'warmup-unused',
    title: 'WARMUP_REQUESTS is defined but never used',
    path: 'kiln_bench/loadgen.py',
    marker: 'WARMUP_REQUESTS = 20',
    severity: 'minor',
    explanation:
      'The first requests hit a cold server (model load, connection setup) and are included in the percentiles. The constant suggests the author meant to drop them.',
  },
  {
    id: 'wall-clock',
    title: 'time.time() is not monotonic',
    path: 'kiln_bench/loadgen.py',
    marker: 'start = time.time()',
    severity: 'minor',
    explanation:
      'time.time() can jump if the clock is adjusted. Durations should use time.perf_counter() or time.monotonic().',
  },
];

export const QUIZ = [
  {
    id: 'q1',
    kind: 'mcq' as const,
    prompt_md: 'In `run`, why can the reported p99 be **better** than what users would see?',
    options: [
      'The percentile function sorts the list in the wrong direction.',
      'The loop waits for each reply before sending the next, so slow periods are sampled less often.',
      'httpx caches responses between requests.',
      'asyncio.sleep adds latency to every sample.',
    ],
    answer: 'The loop waits for each reply before sending the next, so slow periods are sampled less often.',
    explanation_md:
      'The generator is closed-loop: a slow reply delays the next request, so the slow window gets few samples. An open-loop generator sends on a schedule no matter what the server is doing.',
  },
  {
    id: 'q2',
    kind: 'predict_output' as const,
    prompt_md: 'What does this print?',
    code: 'values = [10, 20, 30, 40]\nprint(percentile(values, 99))',
    answer: '40',
    explanation_md: '`int(4 * 99 / 100)` is `int(3.96)`, which is 3, and `ordered[3]` is 40. For small samples p99 is always the max.',
  },
  {
    id: 'q3',
    kind: 'which_test' as const,
    prompt_md: 'Which test would have caught the dropped failures?',
    options: [
      'test_summarize_mean',
      'test_percentile_of_one_value',
      'test_errors_are_counted_in_the_report',
      'test_rate_is_respected',
    ],
    answer: 'test_errors_are_counted_in_the_report',
    explanation_md: 'Only a test that makes some requests fail and then checks the report mentions them touches the filter on `None`.',
  },
];

// ---- the Plan stage (§8): KLN-01 context, outline, worked plan ------------------------


const sym = (qualname: string, kind: OutlineSymbol['kind'], line: number, signature: string, doc: string): OutlineSymbol => ({
  name: qualname.split('.').pop() ?? qualname,
  qualname,
  kind,
  line,
  signature,
  doc,
});

/** kiln-bench at Theo's PR head: names and signatures from src/kiln_bench/*.py (main + the PR overlay). */
export const KILN_OUTLINE: Outline = {
  ref: 'theo/open-loop-arrivals',
  files: [
    { path: "src/kiln_bench/_platform.py", symbols: [
      sym("precise_timers", "function", 25, "def precise_timers() -> Iterator[None]", "Ask Windows for 1 ms timer resolution while the block runs."),
      sym("new_event_loop", "function", 64, "def new_event_loop() -> asyncio.AbstractEventLoop", ""),
      sym("run", "function", 70, "def run(coro: Coroutine[Any, Any, T]) -> T", "``asyncio.run`` with precise timers on every platform."),
    ] },
    { path: "src/kiln_bench/cli.py", symbols: [
      sym("build_parser", "function", 26, "def build_parser() -> argparse.ArgumentParser", ""),
      sym("main", "function", 63, "def main(argv: list[str] | None=None) -> int", ""),
      sym("_cmd_run", "function", 76, "def _cmd_run(args: argparse.Namespace) -> int", ""),
      sym("_run", "async_function", 90, "async def _run(args: argparse.Namespace, prompts: PromptSource) -> list[RequestRecord]", ""),
      sym("_cmd_report", "function", 127, "def _cmd_report(args: argparse.Namespace) -> int", ""),
      sym("_print_summary", "function", 136, "def _print_summary(records: list[RequestRecord], fmt: str, url: str | None=None) -> int", ""),
      sym("_cmd_fake_server", "function", 146, "def _cmd_fake_server(args: argparse.Namespace) -> int", ""),
    ] },
    { path: "src/kiln_bench/client.py", symbols: [
      sym("StreamClient", "class", 14, "class StreamClient", "Sends streaming chat completions and timestamps every content chunk."),
      sym("StreamClient.__init__", "method", 23, "def __init__(self, base_url: str, *, model: str, clock: Callable[[], float], max_tokens: int=32, max_connections: int=64, api_key: str | None=None) -> None", ""),
      sym("StreamClient.aclose", "method", 49, "async def aclose(self) -> None", ""),
      sym("StreamClient.__aenter__", "method", 52, "async def __aenter__(self) -> StreamClient", ""),
      sym("StreamClient.__aexit__", "method", 55, "async def __aexit__(self, *exc_info: object) -> None", ""),
      sym("StreamClient.stream_chat", "method", 58, "async def stream_chat(self, prompt: str, rec: RequestRecord) -> RequestRecord", "Send one request and fill in ``rec`` as the stream arrives."),
    ] },
    { path: "src/kiln_bench/fake_server.py", symbols: [
      sym("FakeServerConfig", "class", 42, "class FakeServerConfig", ""),
      sym("_Request", "class", 63, "class _Request", ""),
      sym("FakeServer", "class", 70, "class FakeServer", "Use as ``async with FakeServer(config) as server: ... server.url``."),
      sym("FakeServer.__init__", "method", 73, "def __init__(self, config: FakeServerConfig | None=None) -> None", ""),
      sym("FakeServer.url", "method", 86, "def url(self) -> str", ""),
      sym("FakeServer.start", "method", 92, "async def start(self) -> None", ""),
      sym("FakeServer.close", "method", 101, "async def close(self) -> None", ""),
      sym("FakeServer.__aenter__", "method", 115, "async def __aenter__(self) -> FakeServer", ""),
      sym("FakeServer.__aexit__", "method", 119, "async def __aexit__(self, *exc_info: object) -> None", ""),
      sym("FakeServer._pause_loop", "method", 124, "async def _pause_loop(self) -> None", ""),
      sym("FakeServer._prefill", "method", 135, "async def _prefill(self, extra_s: float) -> None", ""),
      sym("FakeServer._next_token", "method", 139, "async def _next_token(self) -> None", ""),
      sym("FakeServer._handle_connection", "method", 145, "async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None", ""),
      sym("FakeServer._route", "method", 164, "async def _route(self, req: _Request, writer: asyncio.StreamWriter, keep_alive: bool) -> None", ""),
      sym("FakeServer._chat", "method", 173, "async def _chat(self, req: _Request, writer: asyncio.StreamWriter, keep_alive: bool) -> None", ""),
      sym("_delta", "function", 232, "def _delta(rid: str, model: str, delta: dict, finish_reason: str | None=None) -> dict", ""),
      sym("_sse", "function", 242, "def _sse(payload: dict) -> bytes", ""),
      sym("_read_request", "async_function", 246, "async def _read_request(reader: asyncio.StreamReader) -> _Request | None", "Read one request. Returns None when the client closed the connection."),
      sym("_connection_header", "function", 264, "def _connection_header(keep_alive: bool) -> str", ""),
      sym("_send_json", "async_function", 268, "async def _send_json(writer: asyncio.StreamWriter, status: int, payload: dict, keep_alive: bool) -> None", ""),
      sym("_start_stream", "async_function", 281, "async def _start_stream(writer: asyncio.StreamWriter, keep_alive: bool, request_id: str) -> None", ""),
      sym("_send_chunk", "async_function", 295, "async def _send_chunk(writer: asyncio.StreamWriter, data: bytes) -> None", ""),
      sym("_end_stream", "async_function", 300, "async def _end_stream(writer: asyncio.StreamWriter) -> None", ""),
      sym("add_arguments", "function", 308, "def add_arguments(parser: argparse.ArgumentParser) -> None", ""),
      sym("config_from_args", "function", 327, "def config_from_args(args: argparse.Namespace) -> FakeServerConfig", ""),
      sym("serve_forever", "async_function", 343, "async def serve_forever(config: FakeServerConfig) -> None", ""),
      sym("main", "function", 350, "def main(argv: list[str] | None=None) -> int", ""),
    ] },
    { path: "src/kiln_bench/loadgen.py", symbols: [
      sym("ClosedLoopRunner", "class", 22, "class ClosedLoopRunner", "``concurrency`` workers, each with at most one request in flight."),
      sym("ClosedLoopRunner.__init__", "method", 25, "def __init__(self, client: StreamClient, prompts: PromptSource, *, concurrency: int, duration_s: float | None=None, requests: int | None=None, rate: float | None=None, timeout_s: float=30.0) -> None", ""),
      sym("ClosedLoopRunner.clock", "method", 54, "def clock(self) -> Callable[[], float]", ""),
      sym("ClosedLoopRunner.run", "method", 57, "async def run(self) -> list[RequestRecord]", ""),
      sym("ClosedLoopRunner._claim", "method", 65, "def _claim(self) -> int | None", "Return the next request id, or None when the run is over."),
      sym("ClosedLoopRunner._worker", "method", 74, "async def _worker(self) -> None", ""),
      sym("ClosedLoopRunner._one", "method", 85, "async def _one(self, req_id: int) -> RequestRecord", ""),
    ] },
    { path: "src/kiln_bench/metrics.py", symbols: [
      sym("_label", "function", 15, "def _label(q: float) -> str", ""),
      sym("percentile", "function", 19, "def percentile(sorted_values: Sequence[float], q: float) -> float", "Nearest-rank percentile of values that are already sorted."),
      sym("percentiles", "function", 32, "def percentiles(values: Sequence[float], qs: Sequence[float]=PERCENTILES) -> dict[str, float]", "Percentiles keyed \"p50\", \"p90\", \"p99\", \"p99.9\". See decision 0005."),
      sym("Summary", "class", 39, "class Summary", ""),
      sym("Summary.to_json", "method", 51, "def to_json(self) -> dict", ""),
      sym("summarize", "function", 55, "def summarize(records: Sequence[RequestRecord]) -> Summary", "Summarize a run."),
    ] },
    { path: "src/kiln_bench/openloop.py", symbols: [
      sym("PoissonArrivals", "class", 27, "class PoissonArrivals", "Exponential gaps between sends: what many independent users look like."),
      sym("PoissonArrivals.next_gap", "method", 33, "def next_gap(self) -> float", ""),
      sym("ConstantArrivals", "class", 38, "class ConstantArrivals", "One request every 1/rate seconds. Easier to reason about in tests."),
      sym("ConstantArrivals.next_gap", "method", 43, "def next_gap(self) -> float", ""),
      sym("OpenLoopRunner", "class", 50, "class OpenLoopRunner", "Sends requests on a schedule for ``duration_s`` seconds."),
      sym("OpenLoopRunner.__init__", "method", 57, "def __init__(self, client: StreamClient, prompts: PromptSource, arrivals: Arrivals, *, duration_s: float, max_in_flight: int=64, timeout_s: float=30.0) -> None", ""),
      sym("OpenLoopRunner.clock", "method", 81, "def clock(self) -> Callable[[], float]", ""),
      sym("OpenLoopRunner.run", "method", 84, "async def run(self) -> list[RequestRecord]", ""),
      sym("OpenLoopRunner._fire", "method", 106, "async def _fire(self, req_id: int, intended_at: float) -> None", ""),
    ] },
    { path: "src/kiln_bench/prompts.py", symbols: [
      sym("PromptSource", "class", 28, "class PromptSource", "Hands out prompts in a seeded, shuffled, repeating order."),
      sym("PromptSource.__init__", "method", 31, "def __init__(self, prompts: Sequence[str]=DEFAULT_PROMPTS, *, seed: int=0) -> None", ""),
      sym("PromptSource.next", "method", 38, "def next(self) -> str", ""),
      sym("load_prompts", "function", 44, "def load_prompts(path: Path) -> list[str]", "Read prompts from a file."),
    ] },
    { path: "src/kiln_bench/records.py", symbols: [
      sym("RequestRecord", "class", 12, "class RequestRecord", "What happened to one request."),
      sym("RequestRecord.ok", "method", 33, "def ok(self) -> bool", ""),
      sym("RequestRecord.ttft_s", "method", 37, "def ttft_s(self) -> float | None", ""),
      sym("RequestRecord.e2e_s", "method", 43, "def e2e_s(self) -> float | None", ""),
      sym("RequestRecord.itl_s", "method", 48, "def itl_s(self) -> list[float]", "Gaps between consecutive content chunks."),
      sym("RequestRecord.to_json", "method", 53, "def to_json(self) -> dict", ""),
      sym("RequestRecord.from_json", "method", 57, "def from_json(cls, data: dict) -> RequestRecord", ""),
      sym("write_jsonl", "function", 72, "def write_jsonl(path: Path, records: Iterable[RequestRecord]) -> int", "Write one JSON object per line. Returns how many were written."),
      sym("read_jsonl", "function", 83, "def read_jsonl(path: Path) -> list[RequestRecord]", ""),
    ] },
    { path: "src/kiln_bench/report.py", symbols: [
      sym("_fmt", "function", 13, "def _fmt(value: float) -> str", ""),
      sym("render_text", "function", 17, "def render_text(s: Summary) -> str", ""),
      sym("_jsonable", "function", 34, "def _jsonable(value: object) -> object", "JSON has no NaN; the bot expects null for 'no data'."),
      sym("render_json", "function", 43, "def render_json(s: Summary) -> str", ""),
    ] },
    { path: "src/kiln_bench/sse.py", symbols: [
      sym("iter_sse_data", "async_function", 8, "async def iter_sse_data(lines: AsyncIterable[str]) -> AsyncIterator[str]", "Yield the data payload of each event in an SSE stream."),
    ] },
    { path: "src/kiln_bench/timing.py", symbols: [
      sym("RunClock", "class", 7, "class RunClock", "Seconds since the run started, read from a monotonic clock."),
      sym("RunClock.__init__", "method", 15, "def __init__(self, source: Callable[[], float]=time.perf_counter) -> None", ""),
      sym("RunClock.__call__", "method", 19, "def __call__(self) -> float", ""),
    ] },
  ],
};

/** A real-life framing for the bridge move. It sets the scene only; his solution box starts empty. */
export const KLN01_STORY_MD = `A bakery has promised the café next door a tray of bread every 6 minutes, all morning. A clipboard by the oven lists the time each tray is due.

Some mornings the oven stalls for a minute or two and trays pile up behind it. There are only so many racks for trays waiting to go out.

At the end of the morning the café owner wants an honest report: how long people really waited for bread, including the slow stretch, and how many trays went out late.

*How would the bakery run the morning, and keep that report honest?*`;

/** Server-only in the real app (plan_key.json). The mock uses it for counts; it is never shown. */
export const KLN01_PLAN_KEY = {
  seam: [
    { path: 'src/kiln_bench/openloop.py', symbol: 'OpenLoopRunner._fire' },
    { path: 'src/kiln_bench/metrics.py', symbol: 'summarize' },
    { path: 'src/kiln_bench/cli.py', symbol: 'build_parser' },
  ],
  callers: [
    { path: 'src/kiln_bench/openloop.py', symbol: 'OpenLoopRunner.run' },
    { path: 'src/kiln_bench/cli.py', symbol: '_print_summary' },
    { path: 'src/kiln_bench/cli.py', symbol: 'main' },
    { path: 'src/kiln_bench/cli.py', symbol: '_run' },
  ],
  touched_files: ['src/kiln_bench/openloop.py', 'src/kiln_bench/metrics.py', 'src/kiln_bench/report.py', 'src/kiln_bench/cli.py', 'tests/test_late_sends.py'],
  touched_symbols: ['OpenLoopRunner._fire', 'OpenLoopRunner.run', 'Summary.to_json', 'render_text', 'build_parser'],
};
