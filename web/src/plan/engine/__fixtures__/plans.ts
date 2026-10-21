// Test fixtures for the engine. The first three reproduce real mistakes from his prototype session
// (a log-summary tool, "loglens"); the last is a clean plan of a toy backup script.
import { migrate, type DataCard, type Example, type Mode, type PlanDoc, type StepCard } from '../model';

export function plan(parts: Partial<PlanDoc>, lang: PlanDoc['lang'] = 'python', weight: PlanDoc['weight'] = 'standard'): PlanDoc {
  return migrate({ ticket_id: 'T-1', lang, weight, ...parts });
}

export const card = (id: string, name: string, kind: DataCard['kind'], extra: Partial<DataCard> = {}): DataCard => ({
  id,
  name,
  kind,
  options: [],
  fields: [],
  vtype: 'text',
  ...extra,
});

export const step = (id: string, label: string, takes: [string, Mode][], gives: string | null, extra: Partial<StepCard> = {}): StepCard => ({
  id,
  label,
  subgoal: null,
  existing: null,
  new_fn: null,
  where: null,
  takes: takes.map(([data_id, mode]) => ({ data_id, mode })),
  gives,
  fails: 'no',
  awaits: false,
  risky: false,
  ...extra,
});

export const textEx = (id: string, label: Example['label'], given: string, expect: string, extra: Partial<Example> = {}): Example => ({
  id,
  label,
  rule: '',
  form: 'text',
  text: { given, expect },
  predict: null,
  ...extra,
});

/** His prototype: `level` made "has parts", and info / warn / error made three separate "one of" cards. */
export function levelSplit(): PlanDoc {
  return plan({
    data: [
      card('line', 'log line', 'outside'),
      card('level', 'level', 'parts'),
      card('info', 'info', 'one_of'),
      card('warn', 'warn', 'one_of'),
      card('error', 'error', 'one_of'),
    ],
    steps: [step('parse', 'Parse the level', [['line', 'read']], 'level', { subgoal: 'parse' })],
  });
}

/** His prototype: `count` gives nothing, `build` needs the counts, and `count` is ordered last. */
export function countLast(): PlanDoc {
  return plan({
    data: [
      card('path', 'log file path', 'outside', { vtype: 'path' }),
      card('lines', 'lines', 'many_of', { item: 'line' }),
      card('line', 'line', 'value'),
      card('counts', 'counts per level', 'parts', { fields: [{ name: 'info', type: 'int' }, { name: 'error', type: 'int' }] }),
      card('report', 'report', 'value', { output: true }),
    ],
    steps: [
      step('read', 'Read the lines', [['path', 'read']], 'lines', { subgoal: 'read' }),
      step('build', 'Build the report', [['counts', 'read']], 'report', { subgoal: 'report' }),
      step('count', 'Count the levels', [['lines', 'read']], null, { subgoal: 'count' }),
    ],
  });
}

/** His prototype map: a step → step chain with no data at all. */
export function chainNoData(): PlanDoc {
  return plan({
    steps: [step('a', 'Open the file', [], null), step('b', 'Loop over the lines', [], null), step('c', 'Count the levels', [], null), step('d', 'Print the report', [], null)],
  });
}

/** A clean plan: the toy backup script (`--dry-run` + a skipped-files count). */
export function cleanBackup(): PlanDoc {
  return plan({
    watched: ['w1'],
    restate: { given: 'a source folder, a backup folder and the --dry-run flag', produce: 'copies of the changed files, and a summary with copied and skipped counts', done_when: 'a dry run copies nothing and the summary still counts the skipped files' },
    bridge: {
      source: null,
      story_md: 'A librarian moves new editions from the old shelf to the new one.',
      solution_md: "First I'd walk the old shelf.\nIf the new shelf already has that edition, then I skip it and make a tally mark.\nThe rule is: in 'just tell me' mode I write titles down instead of carrying books.",
      mapping: [
        { id: 'b1', real: 'the old shelf', kind: 'thing', to: { type: 'data', id: 'src' } },
        { id: 'b2', real: 'check if the new shelf has it', kind: 'action', to: { type: 'step', id: 'pick' } },
        { id: 'b3', real: 'tally marks', kind: 'thing', to: { type: 'data', id: 'skipped' } },
        { id: 'b4', real: "'just tell me' mode moves nothing", kind: 'rule', to: { type: 'example', id: 'e2' }, breaks: 'A librarian notices a torn book; the script needs an error example for unreadable files.' },
      ],
    },
    examples: [
      textEx('e1', 'happy', 'three files, one changed since the last backup', 'copied 1, skipped 2'),
      textEx('e2', 'boundary', 'an empty source folder', 'copied 0, skipped 0'),
      { id: 'e3', label: 'error', rule: 'an unreadable file stops the copy with a clear error', form: 'call', call: { target: 'backup.copy_changed', args: '["locked.txt"], dest, dry_run=False', expect: 'PermissionError', compare: 'raises' }, predict: 'fail' },
    ],
    data: [
      card('src', 'source folder', 'outside', { vtype: 'path' }),
      card('dest', 'backup folder', 'outside', { vtype: 'path' }),
      card('dry', 'dry run flag', 'outside', { vtype: 'bool' }),
      card('file', 'file', 'parts', { fields: [{ name: 'path', type: 'Path' }, { name: 'modified', type: 'datetime' }] }),
      card('files', 'files', 'many_of', { item: 'file' }),
      card('todo', 'files to copy', 'many_of', { item: 'file' }),
      card('skipped', 'skipped count', 'value', { vtype: 'number' }),
      card('copied', 'copied count', 'value', { vtype: 'number' }),
      card('summary', 'summary', 'parts', { output: true, fields: [{ name: 'copied', data_id: 'copied' }, { name: 'skipped', data_id: 'skipped' }] }),
    ],
    steps: [
      step('list', 'List the source files', [['src', 'read']], 'files', { subgoal: 'read', fails: 'raises', raises: 'FileNotFoundError' }),
      step('pick', 'Pick the changed files', [['files', 'read'], ['dest', 'read']], 'todo', { subgoal: 'decide', fails: 'raises', raises: 'OSError' }),
      step('skip', 'Count the skipped files', [['files', 'read'], ['todo', 'read']], 'skipped', { subgoal: 'count' }),
      step('copy', 'Copy the changed files', [['todo', 'read'], ['dest', 'read'], ['dry', 'read']], 'copied', { subgoal: 'store', fails: 'raises', raises: 'PermissionError', risky: true }),
      step('sum', 'Build the summary', [['copied', 'read'], ['skipped', 'read']], 'summary', { subgoal: 'report' }),
    ],
    decisions: [{ id: 'k1', choice: 'count skipped files in their own step', because: 'the dry run must report it without copying', instead_of: 'counting inside the copy step', would_change_if: 'the copy step ever needs the count' }],
    premortem: [
      { id: 'p1', text: 'the dry run still copied because the flag was read too late' },
      { id: 'p2', text: 'the skipped count included files that failed to copy' },
      { id: 'p3', text: 'modified times differ by a second on another file system' },
    ],
    scope: { appetite_blocks: 4, no_gos: ['no progress bar'], first_slice: 'e2' },
    walks: [{ id: 'w1', example_id: 'e2', values: { list: '[]', pick: '[]', skip: '0', copy: '0', sum: 'copied 0, skipped 0' }, done: true, result: 'match', at: '2026-10-21T10:00:00Z' }],
  });
}
