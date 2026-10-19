/**
 * A character in the office: sprite, facing, walk/sit/type animation, a
 * path to follow, and an optional status bubble over the head.
 */
import Phaser from 'phaser';
import type { Facing } from './types';
import type { TilePoint } from './walkGrid';

export const TILE = 16;
const FRAME_COLS = 7;
const ROWS: Record<Facing, number> = { down: 0, left: 1, right: 2, up: 3 };
const COL = { idle: 0, walk: [1, 2, 3, 4], sit: 5, type: 6 };

export type Pose = 'stand' | 'walk' | 'sit' | 'type';

/** Feet position (sprite origin) for a tile. */
export function tileFeet(t: TilePoint): { x: number; y: number } {
  return { x: t.x * TILE + TILE / 2, y: t.y * TILE + TILE - 1 };
}

/** Default pixel nudge for a seated character (the scene can pass a better one). */
const SIT_NUDGE: Record<Facing, { x: number; y: number }> = {
  down: { x: 0, y: 2 },
  up: { x: 0, y: -2 },
  left: { x: 0, y: 0 },
  right: { x: 0, y: 0 },
};

/** Create the walk/idle/sit/type animations for one sheet texture (once). */
export function ensureAnims(scene: Phaser.Scene, key: string): void {
  if (scene.anims.exists(`${key}:walk:down`)) return;
  for (const [dir, row] of Object.entries(ROWS)) {
    const base = row * FRAME_COLS;
    scene.anims.create({
      key: `${key}:walk:${dir}`,
      frames: COL.walk.map((c) => ({ key, frame: base + c })),
      frameRate: 8,
      repeat: -1,
    });
    scene.anims.create({
      key: `${key}:type:${dir}`,
      frames: [{ key, frame: base + COL.sit }, { key, frame: base + COL.type }],
      frameRate: 4,
      repeat: -1,
    });
  }
}

export class Walker {
  readonly id: string;
  readonly sprite: Phaser.GameObjects.Sprite;
  key: string;
  tile: TilePoint;
  facing: Facing = 'down';
  pose: Pose = 'stand';
  speed = 54; // px per second
  bubble: Phaser.GameObjects.Sprite;
  bubbleKind: string | null = null;
  private path: TilePoint[] = [];
  private onArrive: (() => void) | null = null;
  private scene: Phaser.Scene;

  constructor(scene: Phaser.Scene, id: string, key: string, at: TilePoint) {
    this.scene = scene;
    this.id = id;
    this.key = key;
    this.tile = { ...at };
    ensureAnims(scene, key);
    const p = tileFeet(at);
    this.sprite = scene.add.sprite(p.x, p.y, key, 0).setOrigin(0.5, 1);
    this.bubble = scene.add.sprite(p.x, p.y - 32, 'bubbles', 'typing0').setOrigin(0.5, 1).setVisible(false);
    this.bubble.setDepth(200000);
    this.applyPose();
  }

  get moving(): boolean {
    return this.path.length > 0;
  }

  setTexture(key: string): void {
    if (key === this.key) return;
    this.key = key;
    ensureAnims(this.scene, key);
    this.applyPose();
  }

  /** Jump straight to a tile (no walking). */
  place(t: TilePoint, facing?: Facing): void {
    this.path = [];
    this.onArrive = null;
    this.tile = { ...t };
    if (facing) this.facing = facing;
    const p = tileFeet(t);
    this.sprite.setPosition(p.x, p.y);
    this.pose = 'stand';
    this.applyPose();
  }

  /** Follow a tile path (as returned by WalkGrid.path). */
  follow(path: TilePoint[], onArrive?: () => void): void {
    const p = path.slice();
    if (p.length && p[0].x === this.tile.x && p[0].y === this.tile.y) p.shift();
    this.path = p;
    this.onArrive = onArrive ?? null;
    if (this.pose === 'sit' || this.pose === 'type') {
      // stand up on the spot before walking off
      const f = tileFeet(this.tile);
      this.sprite.setPosition(f.x, f.y);
    }
    if (!p.length) {
      this.pose = 'stand';
      this.applyPose();
      const cb = this.onArrive;
      this.onArrive = null;
      cb?.();
      return;
    }
    this.pose = 'walk';
    this.applyPose();
  }

  stop(): void {
    this.path = [];
    this.onArrive = null;
    if (this.pose === 'walk') {
      this.pose = 'stand';
      this.applyPose();
    }
  }

  sit(facing: Facing, typing: boolean, nudge?: { x: number; y: number }): void {
    this.path = [];
    this.facing = facing;
    this.pose = typing ? 'type' : 'sit';
    const f = tileFeet(this.tile);
    const n = nudge ?? SIT_NUDGE[facing];
    this.sprite.setPosition(f.x + n.x, f.y + n.y);
    this.applyPose();
  }

  stand(facing?: Facing): void {
    if (facing) this.facing = facing;
    const f = tileFeet(this.tile);
    this.sprite.setPosition(f.x, f.y);
    this.pose = 'stand';
    this.applyPose();
  }

  face(f: Facing): void {
    if (this.facing === f) return;
    this.facing = f;
    this.applyPose();
  }

  setBubble(kind: string | null): void {
    if (kind === this.bubbleKind) return;
    this.bubbleKind = kind;
    if (!kind) {
      this.bubble.setVisible(false).stop();
      return;
    }
    this.bubble.setVisible(this.sprite.visible);
    if (this.scene.anims.exists(`bubble:${kind}`)) this.bubble.play(`bubble:${kind}`);
    else this.bubble.stop().setFrame(kind);
  }

  setVisible(v: boolean): void {
    this.sprite.setVisible(v);
    this.bubble.setVisible(v && this.bubbleKind !== null);
  }

  /** Move along the path; returns true while still walking. */
  update(dt: number): boolean {
    if (this.path.length) {
      let budget = (this.speed * dt) / 1000;
      while (budget > 0 && this.path.length) {
        const next = this.path[0];
        const target = tileFeet(next);
        const dx = target.x - this.sprite.x;
        const dy = target.y - this.sprite.y;
        const dist = Math.abs(dx) + Math.abs(dy);
        const dir: Facing = Math.abs(dx) > Math.abs(dy) ? (dx < 0 ? 'left' : 'right') : dy < 0 ? 'up' : 'down';
        if (dist > 0.01 && dir !== this.facing) {
          this.facing = dir;
          this.applyPose();
        }
        if (dist <= budget) {
          this.sprite.setPosition(target.x, target.y);
          this.tile = { ...next };
          this.path.shift();
          budget -= dist;
        } else {
          this.sprite.x += Math.sign(dx) * Math.min(Math.abs(dx), budget);
          if (Math.abs(dx) < budget) {
            const rest = budget - Math.abs(dx);
            this.sprite.y += Math.sign(dy) * Math.min(Math.abs(dy), rest);
          }
          budget = 0;
        }
      }
      if (!this.path.length) {
        this.pose = 'stand';
        this.applyPose();
        const cb = this.onArrive;
        this.onArrive = null;
        cb?.();
      }
    }
    this.sync();
    return this.path.length > 0;
  }

  /** Keep depth + bubble attached to the sprite. */
  sync(): void {
    const s = this.sprite;
    // sort by feet; seated characters sort by their seat, not the nudged sprite
    const seated = this.pose === 'sit' || this.pose === 'type';
    s.setDepth(10 + (seated ? tileFeet(this.tile).y : s.y));
    this.bubble.setPosition(Math.round(s.x), Math.round(s.y) - 30);
  }

  applyPose(): void {
    const s = this.sprite;
    const row = ROWS[this.facing] * FRAME_COLS;
    if (this.pose === 'walk') {
      s.play(`${this.key}:walk:${this.facing}`, true);
    } else if (this.pose === 'type') {
      s.play(`${this.key}:type:${this.facing}`, true);
    } else {
      s.stop();
      s.setTexture(this.key, row + (this.pose === 'sit' ? COL.sit : COL.idle));
    }
    this.sync();
  }

  destroy(): void {
    this.sprite.destroy();
    this.bubble.destroy();
  }
}
