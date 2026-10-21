// Rust words and type previews for the plan.
import type { DataCard, Mode, PlanDoc, StepCard, VType } from '../model';
import { looksWhole, oneLine, pascal, snake, takesOf, type LangPack } from './common';

const KEYWORDS = new Set(
  ('as break const continue crate else enum extern false fn for if impl in let loop match mod move mut pub ref return self Self static struct super trait true type unsafe use where while async await dyn abstract become box do final macro override priv typeof unsized virtual yield try gen').split(' '),
);
const RESERVED = new Set(['Error', 'Path', 'PathBuf', 'String', 'Vec', 'Option', 'Result', 'Box', 'Some', 'None', 'Ok', 'Err', 'Self']);

function valueType(vtype: VType, name: string, mode: Mode | 'owned'): string {
  const borrowed = mode === 'read';
  switch (vtype) {
    case 'number':
      return looksWhole(name) ? 'usize' : 'f64';
    case 'bool':
      return 'bool';
    case 'path':
      return borrowed ? '&Path' : 'PathBuf';
    case 'time':
      return 'SystemTime';
    case 'duration':
      return 'Duration';
    case 'bytes':
      return borrowed ? '&[u8]' : 'Vec<u8>';
    default:
      return borrowed ? '&str' : 'String';
  }
}

function owned(doc: Pick<PlanDoc, 'data'>, card: DataCard | undefined, depth = 0): string {
  if (!card) return '()';
  switch (card.kind) {
    case 'parts':
    case 'one_of':
      return pascal(card.name, RESERVED);
    case 'many_of': {
      if (depth > 3) return 'Vec<_>';
      const inner = doc.data.find((d) => d.id === card.item);
      const t = inner ? owned(doc, inner, depth + 1) : card.item?.trim() ? pascal(card.item, RESERVED) : '_';
      return `Vec<${t}>`;
    }
    case 'value':
    case 'outside':
      return valueType(card.vtype, card.name, 'owned');
    default:
      return '_';
  }
}

/** The parameter type for a mode: `&T` to read, `&mut T` to change, `T` to take it over. */
function param(doc: Pick<PlanDoc, 'data'>, card: DataCard | undefined, mode: Mode): string {
  if (!card) return '_';
  const copyish = (card.kind === 'value' || card.kind === 'outside') && ['number', 'bool', 'time', 'duration'].includes(card.vtype);
  if (mode === 'consume') return owned(doc, card);
  if (mode === 'change') return `&mut ${owned(doc, card)}`;
  if (copyish) return owned(doc, card);
  if ((card.kind === 'value' || card.kind === 'outside') && ['text', 'path', 'bytes'].includes(card.vtype)) return valueType(card.vtype, card.name, 'read');
  if (card.kind === 'many_of') return `&[${owned(doc, card).replace(/^Vec<(.*)>$/, '$1')}]`;
  return `&${owned(doc, card)}`;
}

function field(name: string): string {
  return snake(name, KEYWORDS, 'field', '_value');
}

function typePreview(doc: Pick<PlanDoc, 'data'>, card: DataCard): string {
  const n = pascal(card.name, RESERVED);
  switch (card.kind) {
    case 'parts': {
      const lines = card.fields.filter((f) => f.name.trim()).map((f) => {
        const inner = f.data_id ? doc.data.find((d) => d.id === f.data_id) : undefined;
        return `    ${field(f.name)}: ${inner ? owned(doc, inner) : f.type?.trim() || '_'},`;
      });
      return [`struct ${n} {`, ...(lines.length ? lines : ['    // no parts yet']), '}'].join('\n');
    }
    case 'one_of': {
      const opts = card.options.filter((o) => o.trim());
      return [`enum ${n} {`, ...(opts.length ? opts.map((o) => `    ${pascal(o, new Set(['Self']), 'Variant')},`) : ['    // no options yet']), '}'].join('\n');
    }
    case 'many_of':
    case 'value':
      return `${field(card.name)}: ${owned(doc, card)}`;
    case 'outside':
      return `${field(card.name)}: ${owned(doc, card)} // from outside the code`;
    default:
      return '// pick a kind to see its type';
  }
}

function fnName(label: string): string {
  return snake(label, KEYWORDS, 'step', '_step');
}

function stepFnName(step: StepCard): string {
  if (step.existing?.symbol) return step.existing.symbol.split(/::|\./).pop() || fnName(step.label);
  return step.new_fn?.trim() || fnName(step.label);
}

function signature(doc: PlanDoc, step: StepCard): string {
  const args = takesOf(doc, step).map((t) => `${field(t.name)}: ${param(doc, t.card, t.mode)}`);
  const gives = doc.data.find((d) => d.id === step.gives);
  let ret = gives ? owned(doc, gives) : '';
  if (step.fails === 'none') ret = `Option<${ret || '()'}>`;
  if (step.fails === 'raises') ret = `Result<${ret || '()'}, ${step.raises?.trim() ? pascal(step.raises, RESERVED, 'Error') : 'Error'}>`;
  return `${step.awaits ? 'async fn' : 'fn'} ${stepFnName(step)}(${args.join(', ')})${ret ? ` -> ${ret}` : ''}`;
}

const MODE_WORDS = { read: 'borrows it (&)', change: 'changes it (&mut)', consume: 'takes it over (owned)' } as const;

function skeleton(doc: PlanDoc): string {
  const out: string[] = ['// Plan skeleton (Rust), made from the plan: names and shapes only, no logic.', ''];
  for (const d of doc.data.filter((x) => x.kind === 'parts' || x.kind === 'one_of')) out.push(typePreview(doc, d), '');
  doc.steps.forEach((s, i) => {
    out.push(`/// Step ${i + 1}: ${oneLine(s.label) || '(no label yet)'}${s.subgoal ? ` (${s.subgoal})` : ''}${s.risky ? ' [risky]' : ''}`);
    const takes = takesOf(doc, s);
    if (takes.length) out.push(`/// Takes: ${takes.map((t) => `${t.name} (${MODE_WORDS[t.mode]})`).join(', ')}.`);
    if (s.existing) out.push(`/// Changes the existing ${s.existing.symbol} in ${s.existing.path}.`);
    else if (s.where) out.push(`/// New function in ${s.where}.`);
    out.push(`${signature(doc, s)} {`, `    todo!("${(oneLine(s.label) || 'step').replace(/["\\{}]/g, '')}")`, '}', '');
  });
  return out.join('\n');
}

export const rust: LangPack = {
  id: 'rust',
  label: 'Rust',
  modes: {
    read: { short: '&', long: 'borrows it (&)' },
    change: { short: '&mut', long: 'changes it (&mut)' },
    consume: { short: 'owned', long: 'takes it over (owned)' },
  },
  fails: { no: "doesn't fail", none: 'Option', raises: 'Result' },
  awaits: 'async: awaits I/O',
  typeOf: (doc, card) => owned(doc, card),
  typePreview,
  fnName,
  signature,
  skeleton,
};
