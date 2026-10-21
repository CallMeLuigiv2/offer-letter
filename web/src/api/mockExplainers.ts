// The explainer-video endpoints (§9.4) for the mock server. Manifests come from the two PUBLIC authored
// scripts; the server-only rubric is never imported here (answer keys must never reach the client bundle),
// so grading is canned: a table of correct option letters and a keyword rule for open answers.
import howScript from '../../../content/companies/kilnworks/tickets/KLN-01/explainers/how-it-works/script.json';
import wrongScript from '../../../content/companies/kilnworks/tickets/KLN-01/explainers/what-went-wrong/script.json';
import { ApiError } from './client';
import { emit } from './events';
import type {
  Api,
  AnswerState,
  BranchClip,
  BridgeSeed,
  ChatMsg,
  ExplainerChapter,
  ExplainerFlag,
  ExplainerManifest,
  ExplainerSummary,
  MyPlanState,
  OpenVerdict,
  PlanVideoConfirm,
} from './types';

interface ScriptBeat { who?: string; say: string; caption?: string }
interface ScriptQuestion { id: string; kind: 'predict' | 'open'; who: string; prompt: string; options?: { id: string; text: string }[]; branches?: { id: string; beats: ScriptBeat[] }[] }
interface ScriptChapter { id: string; title: string; function?: string; issue?: string; ask?: string; beats: ScriptBeat[]; question?: ScriptQuestion }
interface Script { id: string; title: string; unlock: string; mode: 'describe' | 'explain'; narrator: string; chapters: ScriptChapter[] }

export interface MockExplainerCtx {
  wait: (ms: number) => Promise<void>;
  nid: (prefix: string) => string;
  now: () => string;
  /** Throws a 404 for unknown tickets; returns whether it has started. */
  started: (ticketId: string) => boolean;
  reviewSubmitted: (ticketId: string) => boolean;
  /** Whether the plan stage is open, and the stored plan's step count and version. */
  plan: (ticketId: string) => { open: boolean; steps: number; version: number };
}

const SCRIPTS: Record<string, Script> = {
  'how-it-works': howScript as unknown as Script,
  'what-went-wrong': wrongScript as unknown as Script,
};
const MEDIA_BASE = '/test-media/';
const PERSONA = (slug: string | undefined) => (slug ? (slug.includes('.') ? slug : `kilnworks.${slug}`) : null);
// Correct options of the how-it-works predictions (letters only; the reveal text stays on the server).
const PREDICT_KEY: Record<string, string> = { h1: 'a', h2: 'a', h3: 'b', h4: 'b', h5: 'b', h6: 'a', h7: 'b', h8: 'a', h9: 'a' };
const GOOD_WORDS = /\b(due|schedule|scheduled|round(ed|s)? up|ceil|book|stopwatch|monotonic|stall|late|queue|waits?)\b/i;
// The topic of each what-went-wrong question and the plan piece an answer becomes (the server reads both from the rubric).
const SEED: Record<string, Pick<BridgeSeed, 'kind' | 'topic'>> = {
  w1: { kind: 'rule', topic: 'When the stopwatch starts' },
  w2: { kind: 'action', topic: 'Keeping the schedule' },
  w3: { kind: 'rule', topic: 'Picking the percentile slip' },
  w4: { kind: 'rule', topic: 'Failed orders' },
  w5: { kind: 'rule', topic: 'Which clock' },
  w6: { kind: 'limit', topic: 'A trial that proves it' },
  w7: { kind: 'action', topic: 'Counting late orders' },
  w8: { kind: 'rule', topic: 'Running out of trays' },
};
// In mock mode the last what-went-wrong chapter has no clip, so the text fallback is exercised too.
const TEXT_ONLY = new Set(['w9']);

const lines = (beats: ScriptBeat[]) => beats.map((b) => ({ who: PERSONA(b.who), say: b.caption ?? b.say }));

function manifestOf(s: Script): ExplainerManifest {
  return {
    id: s.id,
    title: s.title,
    unlock: s.unlock,
    mode: s.mode,
    narrator: PERSONA(s.narrator) ?? 'kilnworks.theo',
    rendered_at: '2026-10-21T12:00:00Z',
    quality: 'test',
    chapters: s.chapters.map((c): ExplainerChapter => {
      const textOnly = TEXT_ONLY.has(c.id);
      return {
        id: c.id,
        title: c.title,
        ...(c.function ? { function: c.function } : {}),
        ...(c.issue ? { issue: c.issue } : {}),
        ...(c.ask ? { ask: c.ask } : {}),
        file: textOnly ? null : 'chapter.webm',
        vtt: textOnly ? null : 'chapter.vtt',
        duration_s: textOnly ? null : 2,
        ...(c.question
          ? { question: { id: c.question.id, kind: c.question.kind, who: PERSONA(c.question.who) ?? 'kilnworks.theo', prompt: c.question.prompt, ...(c.question.options ? { options: c.question.options } : {}) } }
          : {}),
        ...(textOnly ? { lines: lines(c.beats) } : {}),
      };
    }),
  };
}

const blank = (kind: AnswerState['kind']): AnswerState => ({
  kind, verdict: null, option_id: null, body_md: null, accepted: false, seen_not_solved: false, attempts: 0, followups: 0, can_show_me: false, rung: 0,
});

const OPENER = 'Okay, so what went wrong there? And how would you fix it?';
const RUNG = [
  OPENER,
  'Think about one customer who walked in during the stall. What would they say about their wait?',
  'Here is what I see: the book and the customer disagree about that order. Where does the difference come from?',
];

export function createMockExplainers(ctx: MockExplainerCtx) {
  const done: Record<string, Set<string>> = {};
  const answers: Record<string, AnswerState> = {};
  const chats: Record<string, ChatMsg[]> = {};
  const flags: ExplainerFlag[] = [];
  const render: Record<string, { state: MyPlanState['state']; plan_version: number | null; error: string | null }> = {};
  const confirms: Record<string, PlanVideoConfirm> = {};
  const key = (t: string, v: string, id = '') => `${t}|${v}|${id}`;

  function lockedReason(t: string, video: string): string | null {
    if (video === 'how-it-works') return ctx.started(t) ? null : 'Start the ticket first.';
    if (video === 'what-went-wrong') return ctx.reviewSubmitted(t) ? null : "Submit your review first. This one shows what goes wrong, so it waits until you've had your own look.";
    const p = ctx.plan(t);
    if (!p.open) return 'Opens in the Plan stage.';
    return p.steps ? null : 'Opens once your plan has a step.';
  }
  function script(video: string): Script {
    const s = SCRIPTS[video];
    if (!s) throw new ApiError(`There is no explainer video ${video}.`, 404);
    return s;
  }
  function question(video: string, qid: string): ScriptQuestion {
    const q = script(video).chapters.find((c) => c.question?.id === qid)?.question;
    if (!q) throw new ApiError("That question isn't in this video.", 404);
    return q;
  }
  function requireOpen(t: string, video: string) {
    const why = lockedReason(t, video);
    if (why) throw new ApiError(why, 409);
  }
  function chat(t: string, video: string, qid: string, author: string, body_md: string): ChatMsg {
    const m: ChatMsg = { id: ctx.nid('xc'), ticket_id: t, video, question_id: qid, author, body_md, expression: author === 'player' ? undefined : 'thinking', created_at: ctx.now() };
    (chats[key(t, video, qid)] ??= []).push(m);
    emit({ type: 'explainer.chat', data: m });
    return m;
  }
  function grade(text: string): OpenVerdict {
    const words = text.trim().split(/\s+/).filter(Boolean).length;
    if (words < 3) return 'cant_tell';
    return words >= 6 && GOOD_WORDS.test(text) ? 'works' : 'off_track';
  }
  function branchFor(q: ScriptQuestion): BranchClip | null {
    const b = q.branches?.[0];
    return b ? { id: b.id, file: 'branch.webm', vtt: 'branch.vtt', duration_s: 1.5 } : null;
  }
  function myPlan(t: string): MyPlanState {
    const r = render[t] ?? { state: 'none', plan_version: null, error: null };
    const p = ctx.plan(t);
    const ready = r.state === 'ready';
    return {
      state: r.state,
      plan_version: r.plan_version,
      current_version: p.version,
      stale: ready && r.plan_version !== p.version,
      error: r.error,
      manifest: ready
        ? {
            id: 'my-plan', title: 'Your plan, played out', unlock: 'plan', mode: 'plan', narrator: 'kilnworks.kenji', rendered_at: ctx.now(), quality: 'preview',
            chapters: [{ id: 'plan', title: 'Your plan, step by step', file: 'plan.webm', vtt: 'plan.vtt', duration_s: 2 }],
          }
        : null,
      media_base: ready ? MEDIA_BASE : null,
      confirm: confirms[t] ?? null,
    };
  }
  function summary(t: string, video: string): ExplainerSummary {
    const s = script(video);
    const qs = s.chapters.filter((c) => c.question).map((c) => c.question!.id);
    const why = lockedReason(t, video);
    return {
      id: s.id, title: s.title, mode: s.mode, unlock: s.unlock as ExplainerSummary['unlock'], unlocked: !why, locked_reason: why,
      chapters_total: s.chapters.length, chapters_done: done[key(t, video)]?.size ?? 0,
      questions_total: qs.length,
      questions_done: qs.filter((q) => {
        const a = answers[key(t, video, q)];
        return a && (a.kind === 'predict' ? a.attempts > 0 : a.accepted || a.seen_not_solved);
      }).length,
      media_ready: true,
    };
  }

  const api: Pick<
    Api,
    'explainers' | 'explainer' | 'explainerPredict' | 'explainerOpen' | 'explainerFollowup' | 'explainerShowMe' | 'explainerProgress' | 'explainerFlag' | 'explainerFlags' | 'myPlanVideo' | 'renderMyPlan' | 'confirmMyPlan'
  > = {
    async explainers(t) {
      await ctx.wait(60);
      ctx.started(t);
      const list = Object.keys(SCRIPTS).map((v) => summary(t, v));
      const why = lockedReason(t, 'my-plan');
      const mp = myPlan(t);
      list.push({
        id: 'my-plan', title: 'Your plan, played out', mode: 'plan', unlock: 'plan', unlocked: !why, locked_reason: why,
        chapters_total: 1, chapters_done: confirms[t] ? 1 : 0, questions_total: 1, questions_done: confirms[t] ? 1 : 0,
        media_ready: mp.state === 'ready', state: mp.state,
      });
      return list;
    },

    async explainer(t, video) {
      await ctx.wait(80);
      const s = script(video);
      requireOpen(t, video);
      const manifest = manifestOf(s);
      const ans: Record<string, AnswerState> = {};
      const ch: Record<string, ChatMsg[]> = {};
      for (const c of s.chapters) {
        const q = c.question;
        if (!q) continue;
        const a = answers[key(t, video, q.id)];
        if (a) ans[q.id] = { ...a };
        const m = chats[key(t, video, q.id)];
        if (m) ch[q.id] = [...m];
      }
      return {
        manifest,
        order: manifest.chapters.map((c) => c.id),
        media_base: MEDIA_BASE,
        media_ready: true,
        progress: { chapters_done: [...(done[key(t, video)] ?? [])], answers: ans, chats: ch, flags: flags.filter((f) => f.ticket_id === t && f.video === video) },
      };
    },

    async explainerPredict(t, video, qid, optionId) {
      await ctx.wait(150);
      requireOpen(t, video);
      const q = question(video, qid);
      if (q.kind !== 'predict') throw new ApiError('That question wants an answer in your own words.', 400);
      const correct = PREDICT_KEY[qid] ?? q.options?.[0]?.id ?? 'a';
      const k = key(t, video, qid);
      const prev = answers[k] ?? blank('predict');
      answers[k] = {
        ...prev,
        verdict: prev.verdict ?? (optionId === correct ? 'correct' : 'incorrect'),
        option_id: prev.option_id ?? optionId,
        attempts: prev.attempts + 1,
        correct_option_id: correct,
        reveal_md: 'In the full app the teammate says here what really happens. (Mock mode has no answer text.)',
      };
      return { kind: 'predict', verdict: optionId === correct ? 'correct' : 'incorrect', correct_option_id: correct, reveal_md: answers[k].reveal_md! };
    },

    async explainerOpen(t, video, qid, body_md) {
      requireOpen(t, video);
      const q = question(video, qid);
      if (q.kind !== 'open') throw new ApiError('Pick one of the options for this question.', 400);
      if (!body_md.trim()) throw new ApiError('Write your answer first.', 400);
      const who = PERSONA(q.who)!;
      chat(t, video, qid, 'player', body_md.trim());
      await ctx.wait(500);
      const verdict = grade(body_md);
      const accepted = verdict === 'works';
      const k = key(t, video, qid);
      const prev = answers[k] ?? blank('open');
      const branch = !accepted && verdict === 'off_track' ? branchFor(q) : null;
      const rung = branch ? 0 : 1;
      answers[k] = { ...prev, verdict, body_md: body_md.trim(), accepted, attempts: prev.attempts + 1, rung, can_show_me: prev.followups > 0 };
      const persona_md = accepted ? null : RUNG[rung];
      if (persona_md) chat(t, video, qid, who, persona_md);
      return {
        kind: 'open', verdict, accepted, quote: body_md.trim().split(/\s+/).slice(0, 6).join(' '),
        note_md: accepted ? 'That keeps the customer and the book in agreement.' : null,
        branch, persona_id: who, persona_md, can_show_me: answers[k].can_show_me, rung,
      };
    },

    async explainerFollowup(t, video, qid, body_md) {
      requireOpen(t, video);
      const q = question(video, qid);
      const k = key(t, video, qid);
      const prev = answers[k];
      if (!prev || prev.attempts === 0) throw new ApiError('Answer the question first.', 409);
      if (prev.accepted) throw new ApiError("That one's already answered.", 409);
      if (!body_md.trim()) throw new ApiError('Write your reply first.', 400);
      const who = PERSONA(q.who)!;
      chat(t, video, qid, 'player', body_md.trim());
      await ctx.wait(500);
      const verdict = grade(body_md);
      const accepted = verdict === 'works';
      const rung = Math.min(prev.rung + 1, 2);
      answers[k] = { ...prev, verdict, accepted, followups: prev.followups + 1, rung, can_show_me: true, ...(accepted ? { body_md: body_md.trim() } : {}) };
      const persona_md = accepted ? 'Yes. That would do it.' : RUNG[rung];
      chat(t, video, qid, who, persona_md);
      return {
        verdict, accepted, quote: body_md.trim().split(/\s+/).slice(0, 6).join(' '),
        note_md: accepted ? 'That keeps the customer and the book in agreement.' : null,
        persona_id: who, persona_md, can_show_me: true, rung,
      };
    },

    async explainerShowMe(t, video, qid) {
      await ctx.wait(120);
      requireOpen(t, video);
      question(video, qid);
      const k = key(t, video, qid);
      const prev = answers[k];
      if (!prev?.can_show_me) throw new ApiError('Try once more first: answer the question in the chat, then "Show me" opens.', 409);
      answers[k] = { ...prev, seen_not_solved: true };
      return { model_answer_md: "**Mock mode.** The teammate's model answer appears here in the full app. It's marked *seen, not solved*." };
    },

    async explainerProgress(t, video, chapterId) {
      await ctx.wait(30);
      requireOpen(t, video);
      if (!script(video).chapters.some((c) => c.id === chapterId)) throw new ApiError("That chapter isn't in this video.", 404);
      (done[key(t, video)] ??= new Set()).add(chapterId);
      return { chapters_done: [...done[key(t, video)]] };
    },

    async explainerFlag(t, video, f) {
      await ctx.wait(40);
      requireOpen(t, video);
      const ch = script(video).chapters.find((c) => c.id === f.chapter_id);
      if (!ch) throw new ApiError("That chapter isn't in this video.", 404);
      const row: ExplainerFlag = {
        id: ctx.nid('xf'), ticket_id: t, video, chapter_id: f.chapter_id, t_s: Math.round(f.t_s * 10) / 10,
        function: ch.function ?? null, note_md: f.note_md?.trim() || null, created_at: ctx.now(),
      };
      flags.push(row);
      return row;
    },

    async explainerFlags(t) {
      await ctx.wait(40);
      return flags.filter((f) => f.ticket_id === t);
    },

    async myPlanVideo(t) {
      await ctx.wait(60);
      return myPlan(t);
    },

    async renderMyPlan(t) {
      await ctx.wait(120);
      const why = lockedReason(t, 'my-plan');
      if (why) throw new ApiError(why === 'Opens once your plan has a step.' ? 'Add a step to your plan first.' : why, 409);
      const version = ctx.plan(t).version;
      render[t] = { state: 'rendering', plan_version: version, error: null };
      emit({ type: 'explainer.render', data: { ticket_id: t, video: 'my-plan', state: 'rendering', plan_version: version, error: null } });
      // Not shortened in fast mode, so the "rendering" status can be seen in e2e.
      setTimeout(() => {
        render[t] = { state: 'ready', plan_version: version, error: null };
        emit({ type: 'explainer.render', data: { ticket_id: t, video: 'my-plan', state: 'ready', plan_version: version, error: null } });
      }, 900);
      return myPlan(t);
    },

    async confirmMyPlan(t, reply, note_md) {
      await ctx.wait(80);
      if (render[t]?.state !== 'ready') throw new ApiError('Watch your plan video first.', 409);
      confirms[t] = { reply, note_md: note_md?.trim() || null, plan_version: render[t].plan_version, created_at: ctx.now() };
      return confirms[t];
    },
  };
  /** §9.5: accepted what-went-wrong answers, in his words, for the plan's Real world move. */
  function bridgeSeed(t: string): BridgeSeed[] {
    return wrongScript.chapters.flatMap((c) => {
      const qid = c.question?.id;
      const a = qid ? answers[key(t, 'what-went-wrong', qid)] : undefined;
      if (!qid || !a?.accepted || !a.body_md) return [];
      return [{ question_id: qid, topic: SEED[qid]?.topic ?? c.title, kind: SEED[qid]?.kind ?? 'rule', real: a.body_md.trim() }];
    });
  }
  return { api, bridgeSeed };
}
