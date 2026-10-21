// Deterministic checks over a plan → Check[] (docs/ARCHITECTURE.md §8.2).
// Every check has a stable key, a plain message about the work (never the person),
// an L1 question (`ask`) and an L2 observation (`observe`). Severity:
//   wont_work = the plan cannot work as written; costly = it works but will cost you; note = worth a look.
import { analyse, consumersOf, outputIds, producersOf, startSet } from './flow';
import {
  dataById,
  dataName,
  exampleById,
  listMove,
  removeData,
  stepName,
  uid,
  withHistory,
  type Check,
  type DataCard,
  type Example,
  type FixOp,
  type MoveId,
  type PlanDoc,
  type Reason,
  type Ref,
  type Severity,
  type TicketKind,
} from './model';

export interface CheckCtx {
  kind?: TicketKind | null;
}

/** Steps whose job is a side effect, so giving nothing back is fine. */
const SIDE_EFFECTS = new Set(['report', 'store', 'wire-up', 'handle-failure', 'measure']);
/** Labels that name a side effect (writing, sending, printing), so giving nothing back is fine. */
const SIDE_EFFECT_VERBS = /\b(copy|copies|write|writes|save|saves|store|send|sends|post|print|prints|log|logs|delete|remove|move|upload|emit|publish|notify|warn|warns|render|show|display|apply|push|commit|flush)\b/i;
const HOW_WORDS = /\b(loop|loops|looping|iterate|iterates|iterating|iteration|for each|foreach|for every|variable|variables|index|indices|counter variable|i\+\+|while loop)\b/i;
const TWO_JOBS = /\s(and|&)\s/i;
const TAUTOLOGY = /\b(cleaner|clean|simpler|simple|better|easier|nicer|neater|more readable|readable|best practice|good practice|elegant|proper|correct way)\b/i;
const CONCRETE = /\d|\bthan\b|\bso that\b|\bso\b|\bwhen\b|\bif\b|\bbecause\b|\bunless\b|\bwithout\b|\bfewer\b|\bless\b|\bavoid/i;
const MIN_PER_STEP = 20;
const MIN_PER_BLOCK = 30;

/** Families of words that are usually the options of one thing, not things of their own. */
const FAMILIES: { name: string; words: string[] }[] = [
  { name: 'level', words: ['trace', 'debug', 'info', 'notice', 'warn', 'warning', 'error', 'err', 'critical', 'crit', 'fatal'] },
  { name: 'status', words: ['pending', 'queued', 'running', 'active', 'done', 'finished', 'complete', 'completed', 'failed', 'ok', 'success', 'succeeded', 'cancelled', 'canceled', 'timeout', 'retrying'] },
  { name: 'outcome', words: ['copied', 'skipped', 'moved', 'kept', 'deleted', 'changed', 'unchanged', 'added', 'removed', 'sent', 'dropped', 'late', 'on time'] },
  { name: 'size', words: ['tiny', 'small', 'medium', 'large', 'huge'] },
  { name: 'priority', words: ['low', 'medium', 'high', 'urgent'] },
  { name: 'direction', words: ['up', 'down', 'left', 'right', 'north', 'south', 'east', 'west'] },
  { name: 'method', words: ['get', 'post', 'put', 'patch', 'delete', 'head'] },
  { name: 'arrivals', words: ['poisson', 'constant', 'uniform', 'bursty', 'burst'] },
  { name: 'colour', words: ['red', 'green', 'blue', 'yellow', 'black', 'white', 'orange', 'purple'] },
];
const CATEGORY = /\b(level|status|state|kind|type|mode|severity|category|outcome|result|priority|colou?r|size|direction|method|variant|flavou?r|choice|option|class|tier|phase|stage|arrivals?)s?$/i;

const norm = (s: string) => s.trim().toLowerCase().replace(/[_-]+/g, ' ').replace(/\s+/g, ' ');

function mk(id: string, keyTail: string, severity: Severity, ref: Ref | undefined, msg: string, ask: string, observe: string, fix?: Check['fix']): Check {
  return { key: keyTail ? `${id}:${keyTail}` : id, id, severity, ref, msg, ask, observe, ...(fix ? { fix } : {}) };
}

/** Does this example say what should happen? */
export function hasExpect(e: Example): boolean {
  if (e.form === 'call') return Boolean(e.call?.target.trim()) && (e.call?.compare === 'truthy' || Boolean(e.call?.expect.trim()));
  if (e.form === 'cli') return (e.cli?.checks ?? []).some((c) => c.kind === 'exit' || c.kind === 'json_has' || Boolean(c.value?.trim()));
  return Boolean(e.text?.expect.trim());
}
export function isRunnable(e: Example): boolean {
  return e.form === 'call' || e.form === 'cli';
}
/** Has anything been typed into this example? */
export function isTouched(e: Example): boolean {
  if (e.rule.trim()) return true;
  if (e.form === 'call') return Boolean(e.call && (e.call.target.trim() || e.call.args.trim() || e.call.expect.trim()));
  if (e.form === 'cli') return Boolean(e.cli && (e.cli.args.trim() || e.cli.checks.length));
  return Boolean(e.text && (e.text.given.trim() || e.text.expect.trim()));
}
function exampleSignature(e: Example): string {
  if (e.form === 'call') return `call|${norm(e.call?.target ?? '')}|${norm(e.call?.args ?? '')}|${norm(e.call?.expect ?? '')}`;
  if (e.form === 'cli') return `cli|${norm(e.cli?.args ?? '')}|${e.cli?.fixture ?? ''}|${norm(e.cli?.fixture_args ?? '')}|${(e.cli?.checks ?? []).map((c) => `${c.kind}:${String(c.path ?? '')}:${c.value ?? ''}`).join(',')}`;
  return `text|${norm(e.text?.given ?? '')}|${norm(e.text?.expect ?? '')}`;
}

/** Is this reason a tautology ("cleaner", "simpler") with nothing concrete behind it? */
export function isTautology(text: string | undefined): boolean {
  const t = (text ?? '').trim();
  if (!t || !TAUTOLOGY.test(t)) return false;
  const rest = t.replace(new RegExp(TAUTOLOGY.source, 'gi'), ' ').split(/\s+/).filter((w) => w.length > 2 && !/^(it|is|its|it's|this|that|way|the|and|more|much|just|also|very|code|looks|feels|seems)$/i.test(w));
  return !CONCRETE.test(t) && rest.length <= 3;
}

// ---- data: loose cards that are really the options of another card -----------------

interface OptionGroup {
  container: DataCard | null;
  family: string;
  cards: DataCard[];
}

function isLoose(d: DataCard): boolean {
  if (d.fields.length) return false;
  if (d.kind === 'one_of' && d.options.some((o) => o.trim())) return false;
  if (d.kind !== null && d.kind !== 'one_of' && d.kind !== 'value') return false;
  return d.name.trim().length > 0 && norm(d.name).split(' ').length <= 2;
}

export function optionGroups(doc: Pick<PlanDoc, 'data'>): OptionGroup[] {
  const loose = doc.data.filter(isLoose);
  const groups: OptionGroup[] = [];
  const used = new Set<string>();
  for (const fam of FAMILIES) {
    const members = loose.filter((d) => !used.has(d.id) && fam.words.includes(norm(d.name)));
    if (members.length < 2) continue;
    const others = doc.data.filter((d) => !members.includes(d));
    const container =
      others.find((d) => norm(d.name) === fam.name || norm(d.name) === `${fam.name}s`) ??
      others.find((d) => d.options.some((o) => members.some((m) => norm(o) === norm(m.name)))) ??
      others.find((d) => CATEGORY.test(norm(d.name)) && !fam.words.includes(norm(d.name))) ??
      null;
    for (const m of members) used.add(m.id);
    groups.push({ container, family: fam.name, cards: members });
  }
  // A category card ("level", "status") next to two or more empty one-of cards: likely the same mistake.
  const cats = doc.data.filter((d) => CATEGORY.test(norm(d.name)) && !used.has(d.id));
  for (const c of cats) {
    const members = loose.filter((d) => !used.has(d.id) && d.id !== c.id && d.kind === 'one_of' && !CATEGORY.test(norm(d.name)));
    if (members.length < 2) continue;
    for (const m of members) used.add(m.id);
    groups.push({ container: c, family: norm(c.name), cards: members });
  }
  return groups;
}

// ---- the checks ------------------------------------------------------------------------

export function runChecks(doc: PlanDoc, ctx: CheckCtx = {}): Check[] {
  const out: Check[] = [];
  const add = (c: Check) => out.push(c);
  const lite = doc.weight === 'lite';
  const stepRef = (id: string): Ref => ({ type: 'step', id });
  const dataRef = (id: string): Ref => ({ type: 'data', id });

  // ---- flow
  const flow = analyse(doc);
  const producers = producersOf(doc);
  const consumers = consumersOf(doc);
  const start = startSet(doc);
  const outputs = outputIds(doc);
  const contractsStarted = doc.steps.some((s) => s.takes.length > 0 || s.gives);
  const groups = optionGroups(doc);
  const grouped = new Set<string>();
  for (const g of groups) {
    for (const c of g.cards) grouped.add(c.id);
    if (g.container) grouped.add(g.container.id);
  }

  for (const sf of flow) {
    const s = sf.step;
    const sn = stepName(doc, s.id);
    sf.inputs.forEach((inp, k) => {
      const dn = dataName(doc, inp.data_id);
      if (inp.status === 'empty') {
        add(mk('flow.empty_take', `${s.id}:${k}`, 'note', stepRef(s.id), `${sn} has a "takes" row with no value picked.`, `What does ${sn} need here?`, 'An empty row adds nothing to the contract. Pick the value or remove the row.'));
      } else if (inp.status === 'missing') {
        add(
          mk(
            'flow.no_source',
            `${s.id}:${inp.data_id}`,
            'wont_work',
            stepRef(s.id),
            `${sn} takes ${dn}, but no earlier step gives it and it isn't an outside input.`,
            `Where does ${dn} come from before ${sn} runs?`,
            `Nothing in the plan produces ${dn}. Either an earlier step gives it, or it comes from outside the code (a flag, a file, the network) and its card says "outside".`,
            { label: `Show ${sn}`, op: { kind: 'jump', move: 'contracts', ref: stepRef(s.id) } },
          ),
        );
      } else if (inp.status === 'later') {
        const p = inp.producer ?? sf.index;
        const pn = stepName(doc, doc.steps[p]?.id);
        const self = p === sf.index;
        add(
          mk(
            'flow.later_source',
            `${s.id}:${inp.data_id}`,
            'wont_work',
            stepRef(s.id),
            self ? `${sn} takes ${dn}, which only it gives.` : `${sn} takes ${dn}, but ${dn} is given by ${pn}, which runs later.`,
            self ? `How can ${sn} use ${dn} before it has made it?` : `What does ${sn} have to work with when it runs before ${pn}?`,
            self ? `A step can't take its own result.` : `Steps run top to bottom. When ${sn} runs (step ${sf.index + 1}), ${dn} doesn't exist yet; it appears at step ${p + 1}.`,
            self ? undefined : { label: `Move ${pn} before ${sn}`, op: { kind: 'move_step', step_id: doc.steps[p].id, to: sf.index } },
          ),
        );
      } else if (inp.status === 'used_up') {
        const by = stepName(doc, doc.steps[inp.consumedBy ?? 0]?.id);
        const rust = doc.lang === 'rust';
        add(
          mk(
            rust ? 'rust.use_after_consume' : 'flow.used_up',
            `${doc.steps[inp.consumedBy ?? 0]?.id}:${inp.data_id}:${s.id}`,
            'wont_work',
            stepRef(s.id),
            rust ? `${sn} uses ${dn} after ${by} took it over (owned).` : `${sn} reads ${dn} after ${by} used it up.`,
            rust ? `Does ${by} need to own ${dn}, or would borrowing it (&) be enough?` : `What will ${sn} see when it reads ${dn} a second time?`,
            rust
              ? `After a move the old owner can't use the value (E0382), so ${sn} would have nothing to work with. Borrow it in ${by}, or make ${by} the last step to use it.`
              : `An iterator or stream is empty once it has been read. ${sn} would get nothing. Turn it into a list first, or read it once.`,
            { label: `Show ${by}`, op: { kind: 'jump', move: 'contracts', ref: stepRef(doc.steps[inp.consumedBy ?? 0]?.id ?? s.id) } },
          ),
        );
      }
    });

    if (s.takes.length === 0 && !s.gives) {
      add(
        mk(
          'flow.no_contract',
          s.id,
          'costly',
          stepRef(s.id),
          `${sn} has no contract yet: it takes nothing and gives nothing.`,
          `What does ${sn} need, and what does it hand to the next step?`,
          `Without takes or gives, nothing connects ${sn} to the other steps, so the map shows it alone and the walk can't check it.`,
          { label: `Show ${sn}`, op: { kind: 'jump', move: 'contracts', ref: stepRef(s.id) } },
        ),
      );
    } else if (!s.gives && !s.takes.some((t) => t.mode === 'change') && !(s.subgoal && SIDE_EFFECTS.has(s.subgoal)) && !SIDE_EFFECT_VERBS.test(s.label)) {
      add(
        mk(
          'flow.dead_step',
          s.id,
          'costly',
          stepRef(s.id),
          `${sn} gives nothing back and changes nothing.`,
          `What is different after ${sn} runs?`,
          `${sn} takes ${s.takes.map((t) => dataName(doc, t.data_id)).join(', ') || 'values'} but its work goes nowhere: no result, nothing changed in place. If it reports or stores something, give it that subgoal.`,
          { label: `Show ${sn}`, op: { kind: 'jump', move: 'contracts', ref: stepRef(s.id) } },
        ),
      );
    }

    if (s.label.trim() && TWO_JOBS.test(s.label)) {
      add(mk('steps.two_jobs', s.id, 'costly', stepRef(s.id), `${sn} does two jobs.`, 'Which half could stand on its own?', 'A step whose name needs "and" is usually two steps. Split, each one gets its own contract and can be checked on its own.'));
    }
    if (s.label.trim() && HOW_WORDS.test(s.label)) {
      add(mk('steps.how_not_what', s.id, 'note', stepRef(s.id), `${sn} says how, not what.`, `What does ${sn} achieve, in one verb phrase?`, 'Name the goal ("count the late sends"), not the mechanics ("loop over the records"). The how belongs in the code.'));
    }
    if (doc.weight === 'full' && isExternal(doc, s) && s.fails === 'no') {
      add(mk('steps.no_failure', s.id, 'costly', stepRef(s.id), `${sn} talks to the outside world but says it never fails.`, `What happens in ${sn} when the network, the disk or the other side misbehaves?`, 'Anything that awaits I/O or reads from outside can fail. Say how: may return nothing, or raises a named error.'));
    }
  }

  // outputs nobody produces
  if (outputs.explicit) {
    for (const id of outputs.ids) {
      if (!start.has(id) && !producers.has(id)) {
        add(mk('flow.no_source', `output:${id}`, 'wont_work', dataRef(id), `${dataName(doc, id)} is marked as a result, but no step gives it.`, `Which step produces ${dataName(doc, id)}?`, 'The plan promises this result, but no step makes it.'));
      }
    }
  }

  // values given but never used
  if (contractsStarted) {
    const contained = new Set<string>();
    for (const d of doc.data) {
      for (const f of d.fields) if (f.data_id) contained.add(f.data_id);
      if (d.kind === 'many_of' && d.item) contained.add(d.item);
    }
    for (const d of doc.data) {
      if (outputs.ids.includes(d.id) || contained.has(d.id) || d.kind === 'outside' || grouped.has(d.id)) continue;
      const given = producers.get(d.id);
      const taken = consumers.get(d.id) ?? [];
      if (given && given.length) {
        const first = Math.min(...given);
        if (!taken.some((j) => j > first)) {
          add(
            mk(
              'flow.unused',
              d.id,
              'note',
              dataRef(d.id),
              `${dataName(doc, d.id)} is given by ${stepName(doc, doc.steps[first].id)} but no later step takes it.`,
              `Who needs ${dataName(doc, d.id)}?`,
              `Nothing after ${stepName(doc, doc.steps[first].id)} uses ${dataName(doc, d.id)}, and it isn't marked as a result. Either a step takes it, it's a result, or the work can go.`,
            ),
          );
        }
      } else if (!taken.length) {
        add(mk('flow.unused', d.id, 'note', dataRef(d.id), `Nothing gives or takes ${dataName(doc, d.id)} yet.`, `Which step uses ${dataName(doc, d.id)}?`, `${dataName(doc, d.id)} is a card with no part in any contract.`));
      }
    }
  }

  // ---- data
  for (const g of groups) {
    const names = g.cards.map((c) => c.name.trim());
    const list = names.length === 2 ? names.join(' and ') : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
    const target = g.container ? `“${g.container.name.trim()}”` : `one “${g.family}” card`;
    add(
      mk(
        'data.options_as_cards',
        g.container?.id ?? g.cards.map((c) => c.id).join('+'),
        'costly',
        dataRef(g.container?.id ?? g.cards[0].id),
        `${list} are separate cards, but they look like the options of ${target}.`,
        `Is ${list} a list of things that exist side by side, or the choices for one value?`,
        `As separate cards, nothing says a value is exactly one of ${list}. A "one of" card with them as options says that, and becomes one type.`,
        {
          label: g.container ? `Make them the options of ${g.container.name.trim()}` : `Make one “${g.family}” card with these options`,
          op: { kind: 'make_options', target: g.container?.id ?? '', cards: g.cards.map((c) => c.id), name: g.container ? undefined : g.family },
        },
      ),
    );
  }
  for (const d of doc.data) {
    if (grouped.has(d.id)) continue;
    const dn = d.name.trim() ? `“${d.name.trim()}”` : 'An unnamed card';
    if (!d.kind) {
      add(mk('data.no_kind', d.id, 'note', dataRef(d.id), `${dn} has no kind yet.`, `Is ${dn} made of parts, one of a few options, a list, one plain value, or something from outside?`, 'Each card needs a kind before it can become a type.'));
    } else if (d.kind === 'one_of' && !d.options.some((o) => o.trim())) {
      add(mk('data.one_of_no_options', d.id, 'costly', dataRef(d.id), `${dn} is "one of", but has no options.`, `What are the choices ${dn} can be?`, `A "one of" with no options can't hold any value. List the options, or pick another kind.`));
    } else if (d.kind === 'parts' && !d.fields.some((f) => f.name.trim())) {
      add(mk('data.parts_no_fields', d.id, 'costly', dataRef(d.id), `${dn} "has parts", but no parts are listed.`, `What is ${dn} made of?`, `A card with parts needs at least one named part. If it's a single value, "plain value" fits better.`));
    } else if (d.kind === 'many_of' && !d.item?.trim()) {
      add(mk('data.many_of_no_item', d.id, 'costly', dataRef(d.id), `${dn} is a list, but the list of what isn't said.`, `What is one item of ${dn}?`, 'Name the item (another card or a type), so the steps that use the list know what they get from it.'));
    }
  }

  // ---- rust: changing a value while something borrowed from it is still in use (approximate, by order)
  if (doc.lang === 'rust') {
    doc.steps.forEach((si, i) => {
      if (!si.gives) return;
      for (const t of si.takes.filter((x) => x.mode === 'read')) {
        for (let j = i + 1; j < doc.steps.length; j++) {
          if (!doc.steps[j].takes.some((x) => x.data_id === t.data_id && x.mode === 'change')) continue;
          const k = doc.steps.findIndex((sk, kk) => kk > j && sk.takes.some((x) => x.data_id === si.gives));
          if (k < 0) continue;
          const jn = stepName(doc, doc.steps[j].id);
          add(
            mk(
              'rust.change_while_read',
              `${doc.steps[j].id}:${t.data_id}`,
              'costly',
              stepRef(doc.steps[j].id),
              `${jn} changes ${dataName(doc, t.data_id)} (&mut) while ${dataName(doc, si.gives)}, made from it, is still used later.`,
              `Does ${dataName(doc, si.gives)} borrow from ${dataName(doc, t.data_id)}, or is it its own copy?`,
              `If ${dataName(doc, si.gives)} holds a reference into ${dataName(doc, t.data_id)}, changing ${dataName(doc, t.data_id)} at step ${j + 1} while step ${k + 1} still needs it won't compile (E0502). This check only looks at step order.`,
            ),
          );
          return;
        }
      }
    });
  }

  // ---- examples (only once he has started some)
  if (doc.examples.length) {
    const filled = doc.examples.filter(hasExpect);
    const min = lite ? 2 : 3;
    if (filled.length < min) {
      add(mk('examples.too_few', '', 'costly', undefined, `${filled.length} example${filled.length === 1 ? '' : 's'} with an expected result; this plan needs at least ${min}.`, 'What is one more case the change has to get right?', 'Fewer examples means fewer things the plan can be checked against.'));
    }
    const hasB = doc.examples.some((e) => e.label === 'boundary');
    const hasE = doc.examples.some((e) => e.label === 'error');
    if (lite) {
      if (!hasB && !hasE) add(mk('examples.no_boundary', '', 'costly', undefined, 'No boundary or error example yet.', 'What should happen at the edge: empty input, exactly the limit, one bad item?', 'Edges are where most bugs live. A light plan still needs one.'));
    } else {
      if (!hasB) add(mk('examples.no_boundary', '', 'costly', undefined, 'No boundary example yet.', 'What happens exactly at the limit, or with nothing at all?', 'Boundaries (empty, one, exactly the limit) are where most bugs live.'));
      if (!hasE) add(mk('examples.no_error', '', 'costly', undefined, 'No error example yet.', 'What should happen when something goes wrong: a timeout, a bad value, a refused request?', 'Without an error case, the plan says nothing about failure.'));
    }
    const seen = new Map<string, Example>();
    for (const e of doc.examples) {
      if (!isTouched(e)) continue;
      const sig = exampleSignature(e);
      const prev = seen.get(sig);
      if (prev) add(mk('examples.duplicate', e.id, 'note', { type: 'example', id: e.id }, 'This example is the same as an earlier one.', 'What does this one check that the other doesn\'t?', 'Two identical examples check the same thing twice.'));
      else seen.set(sig, e);
      if (!hasExpect(e)) {
        add(
          mk(
            'examples.no_expect',
            e.id,
            'costly',
            { type: 'example', id: e.id },
            e.form === 'cli' ? 'This command example has no checks on its output.' : 'This example has no expected result.',
            'What should come out?',
            'An example without an expected result can\'t pass or fail, so it checks nothing.',
          ),
        );
      } else if (isRunnable(e) && !e.predict) {
        add(mk('examples.unpredicted', e.id, 'note', { type: 'example', id: e.id }, 'No prediction for this example yet.', 'Will it pass, fail or error on the current code?', 'Predict before you run, so the run can tell you something you didn\'t know.'));
      }
    }
  }

  // ---- reasons
  for (const d of doc.decisions) {
    if (d.choice.trim() && !d.because.trim()) {
      add(mk('reasons.no_because', d.id, 'costly', { type: 'decision', id: d.id }, `“${d.choice.trim()}” has no because.`, 'Why this choice and not the other one?', 'A choice without a reason can\'t be checked: not by a reviewer, not by you in a month.'));
    } else if (isTautology(d.because)) {
      add(mk('reasons.tautology', `decision:${d.id}`, 'note', { type: 'decision', id: d.id }, `The reason for “${d.choice.trim() || 'this choice'}” says it's better without saying how.`, 'Better in what way: fewer steps, fewer bugs, faster, easier to test?', `“${d.because.trim()}” would fit almost any choice. Name what it saves or prevents.`));
    }
  }
  const reasonTargets: [Ref, Reason | undefined, string][] = [
    ...doc.data.map((d) => [{ type: 'data', id: d.id } as Ref, d.because, d.name] as [Ref, Reason | undefined, string]),
    ...doc.steps.map((s) => [{ type: 'step', id: s.id } as Ref, s.because, s.label] as [Ref, Reason | undefined, string]),
  ];
  for (const [ref, r, name] of reasonTargets) {
    if (r?.text && isTautology(r.text)) {
      add(mk('reasons.tautology', `${ref.type}:${ref.id}`, 'note', ref, `The reason on “${name.trim() || 'this card'}” says it's better without saying how.`, 'Better in what way?', `“${r.text.trim()}” would fit almost any choice. Name what it saves or prevents.`));
    }
  }

  // ---- scope
  const sc = doc.scope;
  if (sc.appetite_blocks && doc.steps.length && doc.steps.length * MIN_PER_STEP > sc.appetite_blocks * MIN_PER_BLOCK) {
    const need = doc.steps.length * MIN_PER_STEP;
    add(
      mk(
        'scope.over_appetite',
        '',
        'costly',
        undefined,
        `${doc.steps.length} steps at about ${MIN_PER_STEP} minutes each is about ${fmtMin(need)}; the appetite is ${fmtMin(sc.appetite_blocks * MIN_PER_BLOCK)} (${sc.appetite_blocks} block${sc.appetite_blocks === 1 ? '' : 's'}).`,
        'What could you leave out and still meet the request?',
        'The plan is bigger than the time you said it\'s worth. Cut steps, add a no-go, or raise the appetite on purpose.',
      ),
    );
  }
  const scopeStarted = sc.appetite_blocks !== null || sc.no_gos.some((x) => x.trim()) || doc.decisions.length > 0 || doc.premortem.some((p) => p.text.trim());
  if (sc.first_slice && !exampleById(doc, sc.first_slice)) {
    add(mk('scope.first_slice_not_example', '', 'costly', undefined, 'The first slice points at an example that no longer exists.', 'Which example will you make pass first?', 'The first slice is one of your examples; that one was removed.'));
  } else if (scopeStarted && !sc.first_slice) {
    add(mk('scope.no_first_slice', '', 'costly', undefined, 'No first slice yet.', 'Which one example will you make pass first?', 'A first slice (one example, a few steps, including the risky one) is the smallest thing you can finish and show.'));
  }

  // ---- pre-mortem
  if (!lite && (doc.premortem.length > 0 || doc.decisions.length > 0)) {
    const n = doc.premortem.filter((p) => p.text.trim()).length;
    if (n !== 3) add(mk('premortem.count', '', 'costly', undefined, `${n} pre-mortem line${n === 1 ? '' : 's'}; the plan asks for exactly 3.`, 'Imagine it shipped and broke. What are three reasons why?', 'Three is enough to get past the obvious one, and few enough to finish.'));
  }

  // ---- bridge
  const rows = doc.bridge.mapping.filter((m) => m.real.trim());
  for (const m of rows) {
    const target = m.to ? (m.to.type === 'data' ? dataById(doc, m.to.id) : m.to.type === 'step' ? doc.steps.find((s) => s.id === m.to!.id) : m.to.type === 'example' ? exampleById(doc, m.to.id) : true) : null;
    if (!target) {
      add(mk('bridge.unmapped', m.id, 'note', { type: 'bridge', id: m.id }, `“${m.real.trim()}” from the real world isn't a card yet.`, 'What does this become in the plan: a value, a step, or an example?', 'Each row of the real-world solution should land somewhere in the plan, or be dropped on purpose.'));
    }
  }
  if (rows.length && !doc.bridge.breaks?.trim() && !rows.some((m) => m.breaks?.trim())) {
    add(mk('bridge.no_breaks', '', 'note', undefined, 'No line says where the real-world version stops matching.', 'Where would the real-life version and the code behave differently?', 'Every analogy breaks somewhere. Saying where keeps it from misleading you.'));
  }

  void ctx;
  return out;
}

function fmtMin(m: number): string {
  if (m < 60) return `${m} minutes`;
  const h = m / 60;
  return `${Number.isInteger(h) ? h : h.toFixed(1)} hour${h === 1 ? '' : 's'}`;
}

/** A step that talks to the outside world: awaits I/O, reads or stores, or takes an outside input. */
export function isExternal(doc: Pick<PlanDoc, 'data'>, s: PlanDoc['steps'][number]): boolean {
  if (s.awaits) return true;
  if (s.subgoal === 'read' || s.subgoal === 'store') return true;
  return s.takes.some((t) => doc.data.find((d) => d.id === t.data_id)?.kind === 'outside');
}

/** Which move a check belongs to (where the rail and the panel send him). */
export function checkMove(c: Pick<Check, 'id'>): MoveId {
  const [area, rule] = c.id.split('.');
  if (area === 'flow' || area === 'rust') return 'contracts';
  if (area === 'data') return 'pieces';
  if (area === 'steps') return rule === 'no_failure' ? 'contracts' : 'pieces';
  if (area === 'examples') return 'examples';
  if (area === 'bridge') return 'bridge';
  if (area === 'reasons' || area === 'scope' || area === 'premortem') return 'decide';
  return 'contracts';
}

/** Apply a quick fix. `jump` doesn't change the doc (the UI navigates). */
export function applyFix(doc: PlanDoc, op: FixOp): PlanDoc {
  switch (op.kind) {
    case 'jump':
      return doc;
    case 'move_step': {
      const from = doc.steps.findIndex((s) => s.id === op.step_id);
      if (from < 0) return doc;
      const to = Math.max(0, Math.min(op.to, doc.steps.length - 1));
      return withHistory({ ...doc, steps: listMove(doc.steps, from, to) }, { action: 'reorder', ref: { type: 'step', id: op.step_id }, from, to });
    }
    case 'set_kind': {
      const d = dataById(doc, op.data_id);
      if (!d) return doc;
      return withHistory({ ...doc, data: doc.data.map((x) => (x.id === op.data_id ? { ...x, kind: op.to } : x)) }, { action: 'kind', ref: { type: 'data', id: d.id }, from: d.kind, to: op.to });
    }
    case 'make_options': {
      let next = doc;
      let targetId = op.target;
      const cards = op.cards.map((id) => dataById(doc, id)).filter((d): d is DataCard => Boolean(d));
      if (!cards.length) return doc;
      if (!targetId) {
        const fresh: DataCard = { id: uid('d'), name: op.name ?? 'choice', kind: 'one_of', options: [], fields: [], vtype: 'text' };
        next = { ...next, data: [...next.data, fresh] };
        targetId = fresh.id;
      }
      const target = dataById(next, targetId);
      if (!target) return doc;
      const options = [...target.options.filter((o) => o.trim())];
      for (const c of cards) if (!options.some((o) => norm(o) === norm(c.name))) options.push(c.name.trim());
      next = { ...next, data: next.data.map((d) => (d.id === targetId ? { ...d, kind: 'one_of' as const, options } : d)) };
      for (const c of cards) next = removeData(next, c.id, targetId);
      return withHistory(next, { action: 'make_options', ref: { type: 'data', id: targetId }, from: { kind: target.kind, cards: cards.map((c) => c.name) }, to: { kind: 'one_of', options } });
    }
  }
}
