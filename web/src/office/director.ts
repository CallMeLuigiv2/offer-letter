/**
 * Ambient life in the office: what each teammate does in each scene mode.
 *
 * Every NPC runs a small plan (walk / sit / stand / wait / bubble / hide)
 * over the map's POIs. In `day` they work at their desks and wander off on
 * errands (coffee, the kanban board, a colleague's desk...). `standup`
 * gathers everyone in the meeting room, `incident` sends people to the
 * server room, and `night` sends everyone home except the person on a late
 * shift.
 */
import type { Facing, SceneMode } from './types';
import type { WalkGrid, TilePoint } from './walkGrid';
import { SEAT } from './walkGrid';
import type { Walker } from './walker';

export interface Poi {
  name: string;
  tx: number;
  ty: number;
  facing: Facing;
  sit: boolean;
}

type Step =
  | { t: 'walk'; to: TilePoint; speed?: number }
  | { t: 'sit'; facing: Facing; typing: boolean }
  | { t: 'stand'; facing?: Facing }
  | { t: 'wait'; ms: number }
  | { t: 'bubble'; kind: string | null }
  | { t: 'texture'; focus: boolean }
  | { t: 'hide' }
  | { t: 'show' }
  | { t: 'release' };

export interface DirectorHost {
  grid: WalkGrid;
  pois: Map<string, Poi>;
  now(): number;
  /** Texture key for a persona: the plain sheet, or the "focus" sheet. */
  sheetFor(id: string, focus: boolean): string;
  /** How far a seated sprite tucks into the furniture at this seat. */
  seatNudge(at: TilePoint, facing: Facing): { x: number; y: number };
}

interface Errand {
  poi?: string;
  visit?: string;
  bubble?: string;
  wait: [number, number];
}

const ERRANDS: Record<string, Errand[]> = {
  dana: [
    { poi: 'kanban', wait: [5000, 9000] },
    { visit: 'theo', bubble: 'talk', wait: [6000, 9000] },
    { poi: 'coffee', bubble: 'coffee', wait: [4000, 7000] },
    { poi: 'printer', wait: [3000, 5000] },
  ],
  kenji: [
    { poi: 'water', bubble: 'coffee', wait: [3000, 5000] },
    { poi: 'rolling_wb', wait: [6000, 9000] },
    { visit: 'ines', bubble: 'talk', wait: [5000, 8000] },
    { poi: 'coffee', bubble: 'coffee', wait: [4000, 6000] },
  ],
  ines: [
    { poi: 'bookshelf', wait: [5000, 8000] },
    { poi: 'water', bubble: 'coffee', wait: [3000, 5000] },
    { poi: 'lounge:4', wait: [8000, 12000] },
  ],
  theo: [
    { poi: 'coffee', bubble: 'coffee', wait: [4000, 7000] },
    { poi: 'vending', wait: [3000, 5000] },
    { poi: 'pingpong:1', wait: [6000, 9000] },
    { visit: 'leo', bubble: 'talk', wait: [5000, 8000] },
  ],
  amara: [
    { poi: 'kanban', wait: [6000, 9000] },
    { visit: 'kenji', bubble: 'ask', wait: [5000, 8000] },
    { poi: 'printer', wait: [3000, 5000] },
    { poi: 'lounge:1', wait: [7000, 10000] },
  ],
  leo: [
    { poi: 'water', bubble: 'coffee', wait: [3000, 5000] },
    { poi: 'vending', wait: [3000, 5000] },
    { poi: 'bookshelf', wait: [5000, 8000] },
    { poi: 'pingpong:2', wait: [6000, 9000] },
  ],
};

const STANDUP_SEATS: Record<string, string> = {
  kenji: 'whiteboard',
  amara: 'meeting:1',
  dana: 'meeting:3',
  ines: 'meeting:2',
  theo: 'meeting:5',
  leo: 'meeting:6',
};

const RUSH = 96;
const WALK = 54;

class Brain {
  plan: Step[] = [];
  waitUntil = 0;
  walking = false;
  nextErrandAt = 0;
  reserved: string | null = null;
  constructor(readonly walker: Walker, readonly id: string) {}
}

export class Director {
  mode: SceneMode = 'day';
  private brains = new Map<string, Brain>();
  private reserved = new Set<string>();
  private rng: () => number;

  constructor(private host: DirectorHost, seed = 7) {
    let s = seed >>> 0;
    this.rng = () => {
      s = (s * 1664525 + 1013904223) >>> 0;
      return s / 4294967296;
    };
  }

  add(id: string, walker: Walker): void {
    this.brains.set(id, new Brain(walker, id));
  }

  remove(id: string): void {
    const b = this.brains.get(id);
    if (b?.reserved) this.reserved.delete(b.reserved);
    this.brains.delete(id);
  }

  home(id: string): Poi | undefined {
    return this.host.pois.get(`desk:${id}`);
  }

  /** Switch mode. `instant` jumps everyone to where the mode puts them. */
  setMode(mode: SceneMode, instant: boolean): void {
    this.mode = mode;
    for (const b of this.brains.values()) {
      b.plan = [];
      b.waitUntil = 0;
      b.walking = false;
      if (b.reserved) this.reserved.delete(b.reserved);
      b.reserved = null;
      b.walker.stop();
      b.walker.speed = WALK;
      this.planFor(b, mode, instant);
    }
  }

  private planFor(b: Brain, mode: SceneMode, instant: boolean): void {
    const id = b.id;
    const home = this.home(id);
    const w = b.walker;
    const now = this.host.now();
    const steps: Step[] = [{ t: 'show' }];
    if (mode === 'day') {
      steps.push({ t: 'texture', focus: false }, { t: 'bubble', kind: null });
      if (instant && id === 'theo' && this.host.pois.has('coffee')) {
        this.goto(steps, this.host.pois.get('coffee')!);
        steps.push({ t: 'bubble', kind: 'coffee' }, { t: 'wait', ms: 9000 }, { t: 'bubble', kind: null });
      } else if (instant && id === 'amara' && this.host.pois.has('kanban')) {
        this.goto(steps, this.host.pois.get('kanban')!);
        steps.push({ t: 'wait', ms: 12000 });
      }
      if (home) this.backToDesk(steps, id, home);
      b.nextErrandAt = now + 8000 + this.rng() * 20000;
    } else if (mode === 'standup') {
      steps.push({ t: 'texture', focus: false }, { t: 'bubble', kind: null });
      const seat = this.host.pois.get(STANDUP_SEATS[id] ?? '') ?? this.freeMeetingSeat();
      if (seat) {
        this.goto(steps, seat);
        if (id === 'kenji') steps.push({ t: 'bubble', kind: 'talk' });
      }
    } else if (mode === 'incident') {
      steps.push({ t: 'texture', focus: false });
      const spots: Record<string, string> = { kenji: 'server:1', ines: 'server:2', dana: 'server:3' };
      if (spots[id] && this.host.pois.has(spots[id])) {
        steps.push({ t: 'bubble', kind: 'alert' });
        w.speed = id === 'dana' ? WALK + 10 : RUSH;
        this.goto(steps, this.host.pois.get(spots[id])!);
      } else if (home) {
        steps.push({ t: 'bubble', kind: id === 'amara' ? 'ask' : 'alert' });
        w.speed = RUSH;
        this.goto(steps, home, id !== 'amara');
      }
    } else if (mode === 'night') {
      steps.push({ t: 'texture', focus: false }, { t: 'bubble', kind: null });
      if (id === 'ines' && home) {
        this.goto(steps, home, true);
        steps.push({ t: 'bubble', kind: 'typing' });
      } else {
        const door = this.host.pois.get('door');
        if (door && !instant) {
          steps.push({ t: 'walk', to: { x: door.tx, y: door.ty } });
        }
        steps.push({ t: 'hide' });
      }
    }
    b.plan = steps;
    if (instant) this.runInstant(b);
  }

  /** Walk to (or jump to) a POI and take its pose. */
  private goto(steps: Step[], poi: Poi, typing = false): void {
    steps.push({ t: 'walk', to: { x: poi.tx, y: poi.ty } });
    if (poi.sit) steps.push({ t: 'sit', facing: poi.facing, typing });
    else steps.push({ t: 'stand', facing: poi.facing });
  }

  private backToDesk(steps: Step[], id: string, home: Poi): void {
    this.goto(steps, home, true);
    steps.push({ t: 'release' });
    if (id === 'kenji') steps.push({ t: 'texture', focus: true }, { t: 'bubble', kind: 'focus' });
    else if (id === 'ines') steps.push({ t: 'bubble', kind: 'typing' });
  }

  private freeMeetingSeat(): Poi | undefined {
    for (let i = 1; i <= 12; i++) {
      const p = this.host.pois.get(`meeting:${i}`);
      if (p && !Object.values(STANDUP_SEATS).includes(p.name)) return p;
    }
    return undefined;
  }

  /** Run a plan to its first wait, teleporting instead of walking. */
  private runInstant(b: Brain): void {
    while (b.plan.length) {
      const s = b.plan[0];
      if (s.t === 'wait') break;
      b.plan.shift();
      if (s.t === 'walk') b.walker.place(s.to);
      else this.apply(b, s);
    }
  }

  private apply(b: Brain, s: Step): void {
    const w = b.walker;
    switch (s.t) {
      case 'sit':
        w.sit(s.facing, s.typing, this.host.seatNudge(w.tile, s.facing));
        break;
      case 'stand':
        w.stand(s.facing);
        break;
      case 'bubble':
        w.setBubble(s.kind);
        break;
      case 'texture':
        w.setTexture(this.host.sheetFor(b.id, s.focus));
        break;
      case 'hide':
        w.setVisible(false);
        break;
      case 'show':
        w.setVisible(true);
        break;
      case 'release':
        if (b.reserved) this.reserved.delete(b.reserved);
        b.reserved = null;
        break;
      default:
        break;
    }
  }

  tick(): void {
    const now = this.host.now();
    for (const b of this.brains.values()) {
      if (b.walking || b.waitUntil > now) continue;
      while (b.plan.length && !b.walking && b.waitUntil <= now) {
        const s = b.plan.shift()!;
        if (s.t === 'wait') {
          b.waitUntil = now + s.ms;
        } else if (s.t === 'walk') {
          const path = this.host.grid.path(b.walker.tile, s.to);
          if (!path) continue; // unreachable: skip the walk, keep the plan
          if (s.speed) b.walker.speed = s.speed;
          b.walking = true;
          b.walker.follow(path, () => {
            b.walking = false;
          });
        } else {
          this.apply(b, s);
        }
      }
      if (!b.plan.length && !b.walking && this.mode === 'day' && now >= b.nextErrandAt) {
        this.startErrand(b, now);
      }
    }
  }

  private startErrand(b: Brain, now: number): void {
    const home = this.home(b.id);
    b.nextErrandAt = now + 25000 + this.rng() * 35000;
    const list = ERRANDS[b.id];
    if (!home || !list?.length) return;
    const pick = list[Math.floor(this.rng() * list.length)];
    let target: Poi | undefined;
    let key = '';
    if (pick.visit) {
      const desk = this.home(pick.visit);
      if (!desk || this.brains.get(pick.visit)?.plan.length) return;
      target = this.besideDesk(desk);
      key = `visit:${pick.visit}`;
    } else if (pick.poi) {
      target = this.host.pois.get(pick.poi);
      key = pick.poi;
    }
    if (!target || this.reserved.has(key)) return;
    this.reserved.add(key);
    b.reserved = key;
    const steps: Step[] = [{ t: 'texture', focus: false }, { t: 'bubble', kind: null }];
    this.goto(steps, target);
    if (pick.bubble) steps.push({ t: 'bubble', kind: pick.bubble });
    const [lo, hi] = pick.wait;
    steps.push({ t: 'wait', ms: lo + this.rng() * (hi - lo) }, { t: 'bubble', kind: null });
    this.backToDesk(steps, b.id, home);
    b.plan = steps;
  }

  /** A standing spot next to someone's chair, facing them. */
  private besideDesk(desk: Poi): Poi | undefined {
    const g = this.host.grid;
    for (const dx of [-1, 1]) {
      const x = desk.tx + dx;
      if (g.walkable(x, desk.ty) && g.at(x, desk.ty) !== SEAT) {
        return { name: `beside:${desk.name}`, tx: x, ty: desk.ty, facing: dx < 0 ? 'right' : 'left', sit: false };
      }
    }
    for (const dy of [1, -1]) {
      const y = desk.ty + dy;
      if (g.walkable(desk.tx, y) && g.at(desk.tx, y) !== SEAT) {
        return { name: `beside:${desk.name}`, tx: desk.tx, ty: y, facing: dy < 0 ? 'down' : 'up', sit: false };
      }
    }
    return undefined;
  }
}
