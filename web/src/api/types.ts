// Types for the HTTP API (docs/ARCHITECTURE.md §2–§4) and websocket events (§3).

export type Severity = 'blocker' | 'major' | 'minor' | 'nit' | 'praise';
export type Verdict = 'approve' | 'request_changes' | 'comment';
export type Stage = 'review' | 'quiz' | 'explain' | 'change' | 'own';
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

export type ServerEvent =
  | { type: 'message.created'; data: Message }
  | { type: 'teammate.typing'; data: { persona_id: string; channel_id: string; typing: boolean } }
  | { type: 'ticket.updated'; data: Ticket }
  | { type: 'pr.updated'; data: PullRequest }
  | { type: 'review.comment.created'; data: ReviewComment }
  | { type: 'stage.result'; data: StageResult }
  | { type: 'explain.turn'; data: ExplainTurn }
  | { type: 'governor.updated'; data: Governor }
  | { type: 'notice'; data: { level: 'info' | 'warn'; text: string } };

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
}
