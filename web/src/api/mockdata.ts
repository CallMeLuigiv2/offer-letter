// Sample Kilnworks data for the in-memory mock. All fictional.
import type { Persona, Severity } from './types';

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
