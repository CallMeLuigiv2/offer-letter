// Python words and type previews for the plan.
import type { DataCard, PlanDoc, StepCard, VType } from '../model';
import { looksWhole, oneLine, pascal, snake, takesOf, type LangPack } from './common';

const KEYWORDS = new Set(
  'False None True and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield match case type'.split(' '),
);
const RESERVED = new Set(['Any', 'List', 'Dict', 'Enum', 'Path', 'None', 'Exception', 'Optional', 'Iterator', 'Iterable']);

function valueType(vtype: VType, name: string): string {
  switch (vtype) {
    case 'number':
      return looksWhole(name) ? 'int' : 'float';
    case 'bool':
      return 'bool';
    case 'path':
      return 'Path';
    case 'time':
      return 'datetime';
    case 'duration':
      return 'timedelta';
    case 'bytes':
      return 'bytes';
    default:
      return 'str';
  }
}

function typeOf(doc: Pick<PlanDoc, 'data'>, card: DataCard | undefined, depth = 0): string {
  if (!card) return 'Any';
  switch (card.kind) {
    case 'parts':
    case 'one_of':
      return pascal(card.name, RESERVED);
    case 'many_of': {
      if (depth > 3) return 'list[Any]';
      const inner = doc.data.find((d) => d.id === card.item);
      const t = inner ? typeOf(doc, inner, depth + 1) : card.item?.trim() || 'Any';
      return `list[${t}]`;
    }
    case 'value':
    case 'outside':
      return valueType(card.vtype, card.name);
    default:
      return 'Any';
  }
}

function field(name: string): string {
  return snake(name, KEYWORDS, 'field');
}

function typePreview(doc: Pick<PlanDoc, 'data'>, card: DataCard): string {
  const n = pascal(card.name, RESERVED);
  switch (card.kind) {
    case 'parts': {
      const lines = card.fields.filter((f) => f.name.trim()).map((f) => {
        const inner = f.data_id ? doc.data.find((d) => d.id === f.data_id) : undefined;
        return `    ${field(f.name)}: ${inner ? typeOf(doc, inner) : f.type?.trim() || 'Any'}`;
      });
      return ['@dataclass', `class ${n}:`, ...(lines.length ? lines : ['    ...  # no parts yet'])].join('\n');
    }
    case 'one_of': {
      const opts = card.options.filter((o) => o.trim());
      const lines = opts.map((o) => `    ${snake(o, KEYWORDS, 'option').toUpperCase()} = "${o.trim().replace(/"/g, "'")}"`);
      return [`class ${n}(Enum):`, ...(lines.length ? lines : ['    ...  # no options yet'])].join('\n');
    }
    case 'many_of':
    case 'value':
      return `${field(card.name)}: ${typeOf(doc, card)}`;
    case 'outside':
      return `${field(card.name)}: ${typeOf(doc, card)}  # from outside the code`;
    default:
      return '# pick a kind to see its type';
  }
}

function fnName(label: string): string {
  return snake(label, KEYWORDS, 'step');
}

function stepFnName(step: StepCard): string {
  if (step.existing?.symbol) return step.existing.symbol.split('.').pop() || fnName(step.label);
  return step.new_fn?.trim() || fnName(step.label);
}

function signature(doc: PlanDoc, step: StepCard): string {
  const args = takesOf(doc, step).map((t) => `${field(t.name)}: ${typeOf(doc, t.card)}`);
  if (step.existing?.symbol.includes('.')) args.unshift('self');
  const gives = doc.data.find((d) => d.id === step.gives);
  let ret = gives ? typeOf(doc, gives) : 'None';
  if (step.fails === 'none' && gives) ret = `${ret} | None`;
  return `${step.awaits ? 'async def' : 'def'} ${stepFnName(step)}(${args.join(', ')}) -> ${ret}:`;
}

const MODE_WORDS = { read: 'reads it', change: 'changes it in place', consume: 'uses it up' } as const;

function skeleton(doc: PlanDoc): string {
  const out: string[] = ['# Plan skeleton (Python), made from the plan: names and shapes only, no logic.', 'from __future__ import annotations', ''];
  const types = doc.data.filter((d) => d.kind === 'parts' || d.kind === 'one_of');
  if (types.some((d) => d.kind === 'parts')) out.push('from dataclasses import dataclass');
  if (types.some((d) => d.kind === 'one_of')) out.push('from enum import Enum');
  if (types.length) out.push('');
  for (const d of types) out.push(typePreview(doc, d), '', '');
  doc.steps.forEach((s, i) => {
    out.push(`# Step ${i + 1}: ${oneLine(s.label) || '(no label yet)'}${s.subgoal ? ` (${s.subgoal})` : ''}${s.risky ? ' [risky]' : ''}`);
    out.push(signature(doc, s));
    const first = oneLine(s.label);
    const doclines = [first ? (/[.!?]$/.test(first) ? first : `${first}.`) : 'No label yet.'];
    const takes = takesOf(doc, s);
    if (takes.length) doclines.push(`Takes: ${takes.map((t) => `${t.name} (${MODE_WORDS[t.mode]})`).join(', ')}.`);
    const gives = doc.data.find((d) => d.id === s.gives);
    if (gives) doclines.push(`Gives: ${gives.name}.`);
    if (s.fails === 'none') doclines.push('May return None.');
    if (s.fails === 'raises') doclines.push(`Raises ${s.raises?.trim() || 'an exception'}.`);
    if (s.existing) doclines.push(`Changes the existing ${s.existing.symbol} in ${s.existing.path}.`);
    else if (s.where) doclines.push(`New function in ${s.where}.`);
    out.push(`    """${doclines[0]}`);
    if (doclines.length > 1) out.push('', ...doclines.slice(1).map((l) => `    ${l}`));
    out.push('    """', '    raise NotImplementedError', '', '');
  });
  return out.join('\n').replace(/\n{3,}$/, '\n');
}

export const python: LangPack = {
  id: 'python',
  label: 'Python',
  modes: {
    read: { short: 'reads it', long: 'reads it' },
    change: { short: 'changes it', long: 'changes it in place' },
    consume: { short: 'uses it up', long: 'uses it up (an iterator or stream)' },
  },
  fails: { no: "doesn't fail", none: 'may return None', raises: 'raises …' },
  awaits: 'async: awaits I/O',
  typeOf: (doc, card) => typeOf(doc, card),
  typePreview,
  fnName,
  signature,
  skeleton,
};
