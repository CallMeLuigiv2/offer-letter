// Types for the HTTP API (docs/ARCHITECTURE.md §2–§4, §8.4) and websocket events (§3).
import type { Lang, PlanDoc, Prediction, Ref, ReplyChoice, TicketKind, Weight, WorkedPlan } from '../plan/engine';

export type Severity = 'blocker' | 'major' | 'minor' | 'nit' | 'praise';
export type Verdict = 'approve' | 'request_changes' | 'comment';
export type Stage = 'review' | 'quiz' | 'explain' | 'plan' | 'change' | 'own';
export type TicketStage = Stage | 'done';
export type TicketStatus = 'backlog' | 'assigned' | 'in_progress' | 'done';
export type GovernorMode = 'normal' | 'thrifty' | 'lunch';

export interface Avatar {
  hairStyle: number;
  hairColor: string;
  skin: string;
  shirt: string;
}

export interface Player {
  id: string;
  name: string;
  pronouns: string | null;
  avatar_json: string | Avatar | null;
  created_at?: string;
}

export interface Employment {
  id: string;
  player_id: string;
  company_id: string;
  role: string;
  level: string;
  started_at: string;
  status: 'onboarding' | 'active' | 'left';
}

export interface CatalogCompany {
  id: string;
  name: string;
  pitch: string;
  domain: string;
  domain_label?: string;
  stage: string;
  stage_label: string;
  culture: string;
  stack: string[];
  ticket_count: number;
  first_ticket: { id: string; title: string } | null;
  kit_ready: boolean;
}

export interface Company {
  id: string;
  name: string;
  pitch?: string;
  team_name?: string;
  stage_label?: string;
  domain?: string;
  repos?: { name: string; description: string }[];
}

export interface Persona {
  id: string; // "<company>.<slug>"
  company_id: string;
  name: string;
  role: string;
  color: string;
  model?: string;
  pronouns?: string;
}

export interface Channel {
  id: string;
  company_id: string;
  kind: 'channel' | 'dm';
  name: string;
  topic: string | null;
  members_json: string | string[] | null;
}

export interface Message {
  id: string;
  channel_id: string;
  author: string; // 'player' | persona id | 'system'
  body_md: string;
  thread_root_id: string | null;
  attachments_json?: string | null;
  created_at: string;
}

export interface Ticket {
  id: string;
  company_id: string;
  title: string;
  type: string;
  level: string;
  size_hours: number;
  status: TicketStatus;
  stage: TicketStage;
  assignee: string | null;
  kit_path?: string;
  started_at: string | null;
  done_at: string | null;
  /** The ticket's own stage list (§8.1). Older rows without it use the v0.1 list. */
  stages?: string[];
}

export interface StageResult {
  id: string;
  ticket_id: string;
  stage: Stage;
  passed: 0 | 1 | boolean;
  detail_json: string | Record<string, unknown> | null;
  created_at: string;
}

export interface TicketDetail extends Ticket {
  brief_md: string;
  pr_id: number | null;
  stage_results: StageResult[];
}

export interface Governor {
  id?: number;
  five_hour_util: number;
  seven_day_util: number;
  resets_at: string | number | null; // ISO string or epoch seconds
  mode: GovernorMode;
  updated_at?: string;
}

export interface AppState {
  player: Player | null;
  employment: Employment | null;
  company: Company | null;
  personas: Persona[];
  channels: Channel[];
  tickets: Ticket[];
  governor: Governor | null;
  setup?: Setup | SetupStep[] | null;
}

export interface SetupStep {
  id: string;
  label: string;
  path?: string;
  command?: string;
  detail?: string;
}
export interface Setup {
  title?: string;
  steps: SetupStep[];
}

export interface AcceptResult {
  employment: Employment;
  channels: Channel[];
  setup: Setup | SetupStep[];
}

export interface SetupCheckStep {
  id: string;
  label: string;
  ok: boolean;
  detail: string;
}

export interface PullRequest {
  id: number;
  company_id: string;
  repo: string;
  ticket_id: string;
  title: string;
  author: string;
  base: string;
  head: string;
  description_md: string;
  status: 'open' | 'merged' | 'closed';
}

export interface PrFile {
  path: string;
  status: string;
  additions: number;
  deletions: number;
}

export interface DiffFile {
  path: string;
  old_path: string | null;
  status: string;
  hunks_text: string;
}

export interface ReviewComment {
  id: string;
  pr_id: number;
  author: string;
  path: string;
  line: number;
  side: 'new' | 'old';
  body_md: string;
  severity: Severity | null;
  parent_id: string | null;
  created_at: string;
}

export interface NewComment {
  path: string;
  line: number;
  side: 'new' | 'old';
  body_md: string;
  severity: Severity;
}

export interface ReviewScore {
  found: { issue_id: string; comment_id: string; title?: string; explanation?: string }[];
  missed: { issue_id: string; title: string; path: string; line: number; explanation: string }[];
  false_flags: string[];
  recall: number;
  precision: number;
}
export interface ReviewResult {
  score: ReviewScore;
  debrief_md: string;
  passed: boolean;
}

export type QuizKind = 'mcq' | 'predict_output' | 'which_test';
export interface QuizQuestion {
  id: string;
  kind: QuizKind;
  prompt_md: string;
  code?: string;
  options?: string[];
}
export interface QuizResult {
  score: number;
  results: { id: string; correct: boolean; explanation_md: string }[];
  passed: boolean;
}

export interface ExplainTurn {
  id: string;
  ticket_id?: string;
  author: string; // 'player' | persona id
  body_md: string;
  created_at: string;
  expression?: string;
}
export interface ExplainState {
  persona: string | { id: string; name?: string; role?: string; color?: string }; // id, or the persona object
  opening_md: string;
  turns: ExplainTurn[];
}
export interface Debrief {
  stage: Stage;
  body_md: string;
  created_at: string;
}

export interface ExplainFinish {
  passed: boolean;
  rubric: { point: string; covered: boolean; note: string }[];
  debrief_md: string;
}

export interface ChangeRequest {
  request_md: string;
  from_persona: string | { id: string }; // id, bare slug, or object
  branch_hint: string;
}
export interface ChangeResult {
  passed: boolean;
  tests: { name: string; passed: boolean; output: string }[];
  debrief_md: string;
}

export interface Health {
  ok: boolean;
  claude: { loggedIn: boolean; authMethod: string };
  version: string;
}

// ---- the Plan stage (§8) ----------------------------------------------------------

export interface PlanFixture {
  id: string;
  label: string;
  args_hint: string;
}
export interface PlanContext {
  lang: Lang;
  weight_default: Weight;
  kind: TicketKind;
  request_md: string;
  requester: string | null;
  reviewer: string;
  repo: string;
  base_ref: string;
  fixtures: PlanFixture[];
  worked: WorkedPlan[];
  size_hours: number;
  /** Contract note (web-plan): an optional real-life framing for the bridge move. */
  story?: { source: string | null; story_md: string } | null;
  /** §9.5: his accepted answers from the "what went wrong" video, in his own words. */
  bridge_seed?: BridgeSeed[];
}
export interface BridgeSeed {
  question_id: string;
  topic: string;
  kind: 'thing' | 'action' | 'rule' | 'limit';
  real: string;
}
export type RunOutcome = 'pass' | 'fail' | 'error' | 'skipped';
export interface PlanRun {
  example_id: string;
  outcome: RunOutcome;
  output: string;
  predicted: Prediction | null;
  matched: boolean | null;
  ref: string;
  created_at: string;
}
export interface PlanReply {
  id: string;
  question_id: string;
  choice: ReplyChoice;
  body_md: string;
  persona_md: string;
  rung: number;
  created_at: string;
}
export interface PlanQuestion {
  id: string;
  ref?: Ref | null;
  ask_md: string;
  why_md: string;
  status: 'open' | 'answered';
  rung: number;
  replies: PlanReply[];
}
export interface PlanReview {
  id: string;
  round: number;
  persona_id: string;
  intent_md: string;
  intent_reply: 'yes' | 'no' | 'partly' | null;
  intent_note?: string | null;
  questions: PlanQuestion[];
  created_at: string;
}
export interface PlanState {
  doc: PlanDoc | null;
  version: number;
  context: PlanContext;
  runs: Record<string, PlanRun>;
  review: PlanReview | null;
  submitted_at: string | null;
}
export interface OutlineSymbol {
  name: string;
  qualname: string;
  kind: 'function' | 'async_function' | 'method' | 'class';
  line: number;
  signature: string;
  doc: string;
}
export interface Outline {
  ref: string;
  files: { path: string; symbols: OutlineSymbol[] }[];
}
export interface PlanCheckRow {
  /** e.g. "seam.exists:<path>::<symbol>", "callers.match", "step.existing:<id>", "example.target:<id>", "example.fixture:<id>" */
  id: string;
  ok: boolean;
  severity: string;
  msg: string;
  /** callers.match: {found, missed, wrong: [names he listed]}; others carry refs. Older servers sent a string. */
  detail: string | Record<string, unknown>;
}
export interface PlanSubmit {
  passed: boolean;
  missing: string[];
  debrief_md: string;
}
export interface PlanDrift {
  branch?: string;
  planned_files: string[];
  touched_files: string[];
  planned_symbols: string[];
  touched_symbols: string[];
  examples: { id: string; status: string }[];
  appetite_blocks: number | null;
  /** Minutes worked on the ticket (null if no sessions); the UI converts to 30-minute blocks. */
  worked_minutes: number | null;
  silent: { kind: string; name: string }[];
}
export interface RetroAnswers {
  surprised: string;
  next_time: string;
  why: Record<string, string>;
}

// ---- explainer videos (§9) ---------------------------------------------------------

export type ExplainerMode = 'describe' | 'explain' | 'plan';
export type RenderState = 'none' | 'rendering' | 'ready' | 'failed';
export interface ExplainerSummary {
  id: string;
  title: string;
  mode: ExplainerMode;
  unlock: 'review' | 'after_review' | 'plan';
  unlocked: boolean;
  locked_reason: string | null;
  chapters_total: number;
  chapters_done: number;
  questions_total: number;
  questions_done: number;
  media_ready: boolean;
  /** Only on the `my-plan` row. */
  state?: RenderState;
}
export interface ScriptLine {
  who: string | null; // persona id
  say: string;
}
export interface ExplainerQuestion {
  id: string;
  kind: 'predict' | 'open';
  who: string; // persona id
  prompt: string;
  options?: { id: string; text: string }[];
}
export interface ExplainerChapter {
  id: string;
  title: string;
  function?: string;
  issue?: string;
  ask?: string;
  file: string | null;
  vtt: string | null;
  duration_s: number | null;
  question?: ExplainerQuestion;
  /** Present when the clip isn't rendered yet: the player shows these lines instead. */
  lines?: ScriptLine[];
}
export interface ExplainerManifest {
  id: string;
  title: string;
  unlock: string;
  mode: ExplainerMode;
  narrator: string;
  rendered_at: string | null;
  quality: string | null;
  chapters: ExplainerChapter[];
}
export type OpenVerdict = 'works' | 'different_but_valid' | 'partly' | 'off_track' | 'cant_tell';
export interface AnswerState {
  kind: 'predict' | 'open';
  verdict: string | null;
  option_id: string | null;
  body_md: string | null;
  accepted: boolean;
  seen_not_solved: boolean;
  attempts: number;
  followups: number;
  can_show_me: boolean;
  rung: number;
  reveal_md?: string;
  correct_option_id?: string;
}
export interface ChatMsg {
  id: string;
  ticket_id: string;
  video: string;
  question_id: string;
  author: string; // 'player' | persona id
  body_md: string;
  expression?: string;
  created_at: string;
}
export interface ExplainerFlag {
  id: string;
  ticket_id: string;
  video: string;
  chapter_id: string;
  t_s: number;
  function: string | null;
  note_md: string | null;
  created_at: string;
}
export interface ExplainerProgress {
  chapters_done: string[];
  answers: Record<string, AnswerState>;
  chats: Record<string, ChatMsg[]>;
  flags: ExplainerFlag[];
}
export interface ExplainerVideo {
  manifest: ExplainerManifest;
  order: string[];
  media_base: string;
  media_ready: boolean;
  progress: ExplainerProgress;
}
export interface BranchClip {
  id: string;
  file: string | null;
  vtt: string | null;
  duration_s: number | null;
  lines?: ScriptLine[];
}
export interface PredictResult {
  kind: 'predict';
  verdict: 'correct' | 'incorrect';
  correct_option_id: string;
  reveal_md: string;
}
export interface OpenResult {
  kind: 'open';
  verdict: OpenVerdict;
  accepted: boolean;
  quote: string;
  note_md: string | null;
  branch: BranchClip | null;
  persona_id: string;
  persona_md: string | null;
  can_show_me: boolean;
  rung: number;
}
export interface FollowupResult {
  verdict: OpenVerdict;
  accepted: boolean;
  quote: string;
  note_md: string | null;
  persona_id: string;
  persona_md: string | null;
  can_show_me: boolean;
  rung: number;
}
export type ConfirmReply = 'yes' | 'no' | 'partly';
export interface PlanVideoConfirm {
  reply: ConfirmReply;
  note_md: string | null;
  plan_version: number | null;
  created_at: string;
}
export interface MyPlanState {
  state: RenderState;
  plan_version: number | null;
  current_version: number;
  stale: boolean;
  error: string | null;
  manifest: ExplainerManifest | null;
  media_base: string | null;
  confirm: PlanVideoConfirm | null;
}

export type ServerEvent =
  | { type: 'message.created'; data: Message }
  | { type: 'teammate.typing'; data: { persona_id: string; channel_id: string; typing: boolean } }
  | { type: 'ticket.updated'; data: Ticket }
  | { type: 'pr.updated'; data: PullRequest }
  | { type: 'review.comment.created'; data: ReviewComment }
  | { type: 'stage.result'; data: StageResult }
  | { type: 'explain.turn'; data: ExplainTurn }
  | { type: 'governor.updated'; data: Governor }
  | { type: 'notice'; data: { level: 'info' | 'warn'; text: string } }
  | { type: 'plan.review'; data: PlanReview }
  | { type: 'plan.reply'; data: { review_id: string; question: PlanQuestion } }
  | { type: 'explainer.chat'; data: ChatMsg }
  | { type: 'explainer.render'; data: { ticket_id: string; video: string; state: RenderState; plan_version: number | null; error: string | null } };

export interface Api {
  health(): Promise<Health>;
  catalog(): Promise<CatalogCompany[]>;
  state(): Promise<AppState>;
  createPlayer(body: { name: string; pronouns?: string; avatar: Avatar }): Promise<Player>;
  accept(companyId: string): Promise<AcceptResult>;
  setupCheck(): Promise<{ steps: SetupCheckStep[] }>;
  messages(channelId: string, before?: string, limit?: number): Promise<Message[]>;
  sendMessage(channelId: string, body_md: string, thread_root_id?: string): Promise<Message>;
  tickets(): Promise<Ticket[]>;
  ticket(id: string): Promise<TicketDetail>;
  startTicket(id: string): Promise<Ticket>;
  pr(id: number): Promise<{ pr: PullRequest; files: PrFile[] }>;
  prDiff(id: number): Promise<{ files: DiffFile[] }>;
  prFile(id: number, path: string, ref: 'base' | 'head'): Promise<{ path: string; ref: string; content: string }>;
  comments(prId: number): Promise<ReviewComment[]>;
  addComment(prId: number, c: NewComment & { parent_id?: string }): Promise<ReviewComment>;
  submitReview(prId: number, body: { verdict: Verdict; body_md: string }): Promise<ReviewResult>;
  quiz(ticketId: string): Promise<{ questions: QuizQuestion[] }>;
  submitQuiz(ticketId: string, answers: Record<string, string>): Promise<QuizResult>;
  explain(ticketId: string): Promise<ExplainState>;
  explainSend(ticketId: string, body_md: string): Promise<{ turn: ExplainTurn; player_turn?: ExplainTurn }>;
  explainFinish(ticketId: string): Promise<ExplainFinish>;
  change(ticketId: string): Promise<ChangeRequest>;
  changeCheck(ticketId: string, branch: string): Promise<ChangeResult>;
  own(ticketId: string): Promise<{ repo_url: string }>;
  governor(): Promise<Governor>;
  debriefs(ticketId: string): Promise<Debrief[]>;
  clockIn(minutes: number): Promise<{ standup_channel_id: string }>;

  // §8.4 the Plan stage
  plan(ticketId: string): Promise<PlanState>;
  savePlan(ticketId: string, doc: PlanDoc, version: number): Promise<{ version: number }>;
  planOutline(ticketId: string): Promise<Outline>;
  planCheck(ticketId: string): Promise<{ checks: PlanCheckRow[] }>;
  planRun(ticketId: string, exampleIds?: string[]): Promise<{ runs: PlanRun[] }>;
  planReview(ticketId: string): Promise<PlanReview>;
  planIntent(ticketId: string, reply: 'yes' | 'no' | 'partly', note?: string): Promise<PlanReview>;
  planReply(ticketId: string, questionId: string, choice: ReplyChoice, body_md: string): Promise<PlanQuestion>;
  planSubmit(ticketId: string): Promise<PlanSubmit>;
  planToBranch(ticketId: string, overwrite?: boolean): Promise<{ written: string[] }>;
  planDrift(ticketId: string, branch?: string): Promise<PlanDrift>;
  planRetro(ticketId: string, answers: RetroAnswers): Promise<{ persona_md: string; debrief_md: string }>;

  // §9.4 explainer videos
  explainers(ticketId: string): Promise<ExplainerSummary[]>;
  explainer(ticketId: string, video: string): Promise<ExplainerVideo>;
  /** Both POST …/answer: a predict pick, or an open answer in his words. */
  explainerPredict(ticketId: string, video: string, questionId: string, optionId: string): Promise<PredictResult>;
  explainerOpen(ticketId: string, video: string, questionId: string, body_md: string): Promise<OpenResult>;
  explainerFollowup(ticketId: string, video: string, questionId: string, body_md: string): Promise<FollowupResult>;
  explainerShowMe(ticketId: string, video: string, questionId: string): Promise<{ model_answer_md: string }>;
  explainerProgress(ticketId: string, video: string, chapterId: string): Promise<{ chapters_done: string[] }>;
  explainerFlag(ticketId: string, video: string, flag: { chapter_id: string; t_s: number; note_md?: string }): Promise<ExplainerFlag>;
  explainerFlags(ticketId: string): Promise<ExplainerFlag[]>;
  myPlanVideo(ticketId: string): Promise<MyPlanState>;
  renderMyPlan(ticketId: string): Promise<MyPlanState>;
  confirmMyPlan(ticketId: string, reply: ConfirmReply, note_md?: string): Promise<PlanVideoConfirm>;
}
