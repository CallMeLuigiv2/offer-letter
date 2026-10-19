/**
 * The walkable Kilnworks office. Loads the generated Tiled map, tileset and
 * character sheets from `assetBase` (default /office/), runs the teammates'
 * schedules (Director), lets the player walk with WASD / arrow keys, and
 * switches between scene modes: day, standup, incident, night.
 */
import Phaser from 'phaser';
import { composeAvatarCanvas, layersFor, normalizeAvatar, type CharactersMeta } from './avatar';
import { Director, type Poi } from './director';
import { LED_GREEN, LED_RED, MOON, SCREEN, WARM, paintNight, type Light } from './lighting';
import type {
  CameraMode,
  Facing,
  OfficeOptions,
  OfficeSnapshot,
  PersonaInfo,
  SceneMode,
} from './types';
import { TILE, Walker } from './walker';
import { BLOCKED, FREE, SEAT, WalkGrid } from './walkGrid';

const LAYERS = ['floor', 'walls', 'furniture_below', 'furniture_above'] as const;
const DEPTH = { floor: 0, walls: 1, furniture_below: 2, furniture_above: 100000, alarm: 140000, night: 150000, ui: 200000 };
const PLAYER_SPEED = 66;
const FONT_CHARS = ' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ';

interface Swap {
  tile: Phaser.Tilemaps.Tile;
  base: string;
}

interface TileProps {
  name?: string;
  layer?: string;
  collides?: boolean;
  seat?: boolean;
}

interface Npc {
  persona: PersonaInfo | null;
  slug: string;
  walker: Walker;
  tag: Phaser.GameObjects.Container;
}

export class OfficeScene extends Phaser.Scene {
  ready = false;
  private opts: OfficeOptions;
  private base: string;
  private meta!: CharactersMeta;
  private map!: Phaser.Tilemaps.Tilemap;
  private tileset!: Phaser.Tilemaps.Tileset;
  private layers = new Map<string, Phaser.Tilemaps.TilemapLayer>();
  private names = new Map<string, number>();
  private swaps: Swap[] = [];
  grid!: WalkGrid;
  pois = new Map<string, Poi>();
  private zones = new Map<string, Phaser.Geom.Rectangle>();
  private npcs = new Map<string, Npc>();
  private director!: Director;
  private player!: Walker;
  private marker!: Phaser.GameObjects.Image;
  private mode: SceneMode = 'day';
  private cameraMode: CameraMode = 'follow';
  private nightDark?: Phaser.GameObjects.Image;
  private nightGlow?: Phaser.GameObjects.Image;
  private alarm?: Phaser.GameObjects.Rectangle;
  private alarmTween?: Phaser.Tweens.Tween;
  private keys = new Set<string>();
  private stillFor = 0;
  private autoWalking = false;
  private cleanup: (() => void)[] = [];

  constructor(opts: OfficeOptions) {
    super({ key: 'office' });
    this.opts = opts;
    this.base = opts.assetBase ?? '/office/';
    this.mode = opts.mode ?? 'day';
    this.cameraMode = opts.camera ?? 'follow';
  }

  // ------------------------------------------------------------------ load
  preload(): void {
    const b = this.base;
    this.load.tilemapTiledJSON('kilnworks', b + 'kilnworks.tmj');
    this.load.image('office-tiles', b + 'tileset.png');
    this.load.image('bubbles', b + 'bubbles.png');
    this.load.image('marker', b + 'marker.png');
    this.load.image('font3x5', b + 'font3x5.png');
    this.load.json('characters', b + 'characters/characters.json');
    this.load.once('filecomplete-json-characters', (_key: string, _type: string, data: CharactersMeta) => {
      const frame = { frameWidth: data.frame.width, frameHeight: data.frame.height };
      for (const c of data.cast) {
        this.load.spritesheet(`char:${c.id}`, b + 'characters/' + c.sheet, frame);
        if (c.focusSheet) this.load.spritesheet(`char:${c.id}:focus`, b + 'characters/' + c.focusSheet, frame);
      }
      this.load.spritesheet('char:player_default', b + 'characters/' + data.playerDefault.sheet, frame);
      const avatar = normalizeAvatar(this.opts.player?.avatar, data);
      if (avatar) {
        for (const name of layersFor(data, avatar)) {
          this.load.image(`layer:${name}`, b + 'characters/' + data.layers[name].file);
        }
      }
    });
  }

  // ---------------------------------------------------------------- create
  create(): void {
    this.meta = this.cache.json.get('characters') as CharactersMeta;
    this.buildMap();
    this.buildGrid();
    this.readObjects();
    this.buildUiTextures();
    this.buildPlayer();
    this.director = new Director({
      grid: this.grid,
      pois: this.pois,
      now: () => this.time.now,
      sheetFor: (id, focus) =>
        focus && this.textures.exists(`char:${id}:focus`) ? `char:${id}:focus` : `char:${id}`,
      seatNudge: (at, facing) => this.seatNudge(at.x, at.y, facing),
    });
    this.spawnNpcs(this.opts.personas);
    this.bindInput();
    this.layoutCamera();
    this.scale.on(Phaser.Scale.Events.RESIZE, this.layoutCamera, this);
    this.applyMode(this.mode, true);
    this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => this.teardown());
    this.events.once(Phaser.Scenes.Events.DESTROY, () => this.teardown());
    this.ready = true;
    this.game.events.emit('office-ready');
  }

  private buildMap(): void {
    this.map = this.make.tilemap({ key: 'kilnworks' });
    const ts = this.map.addTilesetImage('office', 'office-tiles');
    if (!ts) throw new Error('office tileset missing from kilnworks.tmj');
    this.tileset = ts;
    for (const [id, props] of Object.entries(ts.tileProperties as Record<string, TileProps>)) {
      if (props.name) this.names.set(props.name, Number(id));
    }
    for (const name of LAYERS) {
      const layer = this.map.createLayer(name, ts, 0, 0) as Phaser.Tilemaps.TilemapLayer | null;
      if (!layer) throw new Error(`layer ${name} missing`);
      layer.setDepth(DEPTH[name]);
      this.layers.set(name, layer);
    }
    const swappable = /^(rack_okb?|door|window_day|desk_mon_(scrollb?|graph|on))@/;
    for (const layer of this.layers.values()) {
      layer.forEachTile((tile) => {
        const nm = this.propsOf(tile.index).name;
        if (nm && swappable.test(nm)) this.swaps.push({ tile, base: nm });
      });
    }
  }

  private propsOf(index: number): TileProps {
    if (index < 0) return {};
    return (this.tileset.getTileProperties(index) as TileProps | null) ?? {};
  }

  private nameAt(layer: string, x: number, y: number): string | undefined {
    const t = this.layers.get(layer)?.getTileAt(x, y);
    return t ? this.propsOf(t.index).name : undefined;
  }

  private buildGrid(): void {
    const w = this.map.width;
    const h = this.map.height;
    const cells: number[][] = [];
    for (let y = 0; y < h; y++) {
      const row: number[] = [];
      for (let x = 0; x < w; x++) {
        let cell = FREE;
        let any = false;
        for (const layer of this.layers.values()) {
          const t = layer.getTileAt(x, y);
          if (!t || t.index < 0) continue;
          any = true;
          const p = this.propsOf(t.index);
          if (p.collides) cell = BLOCKED;
          else if (p.seat && cell !== BLOCKED) cell = SEAT;
        }
        row.push(any ? cell : BLOCKED);
      }
      cells.push(row);
    }
    this.grid = new WalkGrid(cells);
  }

  private readObjects(): void {
    const layer = this.map.getObjectLayer('poi');
    for (const o of layer?.objects ?? []) {
      const props: Record<string, unknown> = {};
      for (const p of (o.properties ?? []) as { name: string; value: unknown }[]) props[p.name] = p.value;
      if (o.point) {
        const tx = Number(props.tx ?? Math.floor((o.x ?? 0) / TILE));
        const ty = Number(props.ty ?? Math.floor((o.y ?? 0) / TILE));
        this.pois.set(o.name, {
          name: o.name,
          tx,
          ty,
          facing: (props.facing as Facing) ?? 'down',
          sit: props.sit === 'true' || props.sit === true,
        });
      } else {
        this.zones.set(o.name, new Phaser.Geom.Rectangle(o.x ?? 0, o.y ?? 0, o.width ?? 0, o.height ?? 0));
      }
    }
  }

  private buildUiTextures(): void {
    const bubbles = this.textures.get('bubbles');
    this.meta.bubbles.names.forEach((name, i) => bubbles.add(name, 0, i * 16, 0, 16, 16));
    this.anims.create({
      key: 'bubble:typing',
      frames: ['typing0', 'typing1', 'typing2'].map((frame) => ({ key: 'bubbles', frame })),
      frameRate: 3,
      repeat: -1,
    });
    this.anims.create({
      key: 'bubble:alert',
      frames: ['alert0', 'alert1'].map((frame) => ({ key: 'bubbles', frame })),
      frameRate: 4,
      repeat: -1,
    });
    const font = Phaser.GameObjects.RetroFont.Parse(this, {
      image: 'font3x5',
      width: 4,
      height: 6,
      chars: FONT_CHARS,
      charsPerRow: FONT_CHARS.length,
      'spacing.x': 0,
      'spacing.y': 0,
      'offset.x': 0,
      'offset.y': 0,
      lineSpacing: 1,
    });
    this.cache.bitmapFont.add('font3x5', font);
  }

  private buildPlayer(): void {
    let key = 'char:player_default';
    const avatar = normalizeAvatar(this.opts.player?.avatar, this.meta);
    if (avatar) {
      try {
        const images: Record<string, CanvasImageSource> = {};
        for (const name of layersFor(this.meta, avatar)) {
          if (this.textures.exists(`layer:${name}`)) {
            images[name] = this.textures.get(`layer:${name}`).getSourceImage() as HTMLImageElement;
          }
        }
        const canvas = composeAvatarCanvas(this.meta, images, avatar);
        const tex = this.textures.addCanvas('char:player', canvas);
        if (tex) {
          const { width: fw, height: fh } = this.meta.frame;
          const cols = this.meta.columns.length;
          for (let i = 0; i < cols * this.meta.rows.length; i++) {
            tex.add(i, 0, (i % cols) * fw, Math.floor(i / cols) * fh, fw, fh);
          }
          key = 'char:player';
        }
      } catch (err) {
        console.warn('office: could not build the player avatar, using the default', err);
      }
    }
    const start = this.pois.get('spawn') ?? this.pois.get('door') ?? { tx: 2, ty: 14, facing: 'up' as Facing };
    this.player = new Walker(this, 'player', key, { x: start.tx, y: start.ty });
    this.player.face(start.facing);
    this.player.speed = PLAYER_SPEED;
    this.marker = this.add.image(0, 0, 'marker').setOrigin(0.5, 1).setDepth(DEPTH.ui + 1);
  }

  // ------------------------------------------------------------- personas
  private slugOf(id: string): string {
    return id.split('.').pop()!.toLowerCase();
  }

  spawnNpcs(personas: PersonaInfo[]): void {
    const wanted = new Map<string, PersonaInfo | null>();
    if (personas.length) {
      for (const p of personas) wanted.set(this.slugOf(p.id), p);
    } else {
      for (const c of this.meta.cast) wanted.set(c.id, null);
    }
    for (const [slug, npc] of this.npcs) {
      if (!wanted.has(slug)) {
        npc.walker.destroy();
        npc.tag.destroy();
        this.director.remove(slug);
        this.npcs.delete(slug);
      }
    }
    for (const [slug, persona] of wanted) {
      const cast = this.meta.cast.find((c) => c.id === slug);
      if (!cast) continue;
      const existing = this.npcs.get(slug);
      if (existing) {
        existing.persona = persona;
        this.refreshTag(existing);
        continue;
      }
      const home = this.pois.get(`desk:${slug}`) ?? this.pois.get('spawn');
      if (!home) continue;
      const walker = new Walker(this, slug, `char:${slug}`, { x: home.tx, y: home.ty });
      const tag = this.add.container(0, 0).setDepth(DEPTH.ui + 2).setVisible(false);
      const npc: Npc = { persona, slug, walker, tag };
      this.refreshTag(npc, cast.name);
      walker.sprite.setInteractive({ useHandCursor: true });
      walker.sprite.on('pointerover', () => npc.tag.setVisible(walker.sprite.visible));
      walker.sprite.on('pointerout', () => npc.tag.setVisible(false));
      walker.sprite.on('pointerdown', () => {
        const cb = this.opts.onPersonaClick;
        if (cb) cb(npc.persona?.id ?? slug);
      });
      this.npcs.set(slug, npc);
      this.director.add(slug, walker);
    }
    if (this.ready) this.director.setMode(this.mode, true);
  }

  private refreshTag(npc: Npc, fallbackName?: string): void {
    npc.tag.removeAll(true);
    const name = (npc.persona?.name ?? fallbackName ?? npc.slug).split(' ')[0].toUpperCase();
    const text = this.add.bitmapText(0, 0, 'font3x5', name).setOrigin(0.5, 0.5);
    const w = Math.ceil(text.width) + 6;
    const color = Phaser.Display.Color.HexStringToColor(npc.persona?.color ?? '#3456a8').color;
    const g = this.add.graphics();
    g.fillStyle(0x1b1726, 1).fillRect(-w / 2 - 1, -5, w + 2, 10);
    g.fillStyle(color, 1).fillRect(-w / 2, -4, w, 8);
    npc.tag.add([g, text]);
  }

  setPersonas(personas: PersonaInfo[]): void {
    this.opts.personas = personas;
    if (this.ready) this.spawnNpcs(personas);
  }

  setOnPersonaClick(cb: ((id: string) => void) | undefined): void {
    this.opts.onPersonaClick = cb;
  }

  // ----------------------------------------------------------------- modes
  setMode(mode: SceneMode): void {
    if (!this.ready) {
      this.mode = mode;
      return;
    }
    if (mode === this.mode) return;
    this.applyMode(mode, false);
  }

  getMode(): SceneMode {
    return this.mode;
  }

  private applyMode(mode: SceneMode, instant: boolean): void {
    this.mode = mode;
    this.applyTileSwaps(mode);
    this.director.setMode(mode, instant);
    this.setNight(mode === 'night');
    this.setAlarm(mode === 'incident');
  }

  private applyTileSwaps(mode: SceneMode): void {
    const lateDesk = this.pois.get('desk:ines');
    const lateOn = this.npcs.has('ines') && lateDesk;
    for (const s of this.swaps) {
      let name = s.base;
      if (mode === 'incident') {
        name = name
          .replace(/^rack_ok(b?)@/, 'rack_alarm$1@')
          .replace(/^door@/, 'door_alarm@')
          .replace(/^desk_mon_(scrollb?|graph)@/, 'desk_mon_alert@');
      } else if (mode === 'night') {
        name = name.replace(/^window_day@/, 'window_night@');
        const isLate = lateOn && lateDesk && s.tile.x === lateDesk.tx && s.tile.y === lateDesk.ty - 2;
        if (/^desk_mon_/.test(name) && !isLate) name = name.replace(/^desk_mon_\w+@/, 'desk_mon_off@');
      }
      const id = this.names.get(name) ?? this.names.get(s.base);
      if (id !== undefined) s.tile.index = id + this.tileset.firstgid;
    }
  }

  private setAlarm(on: boolean): void {
    const zone = this.zones.get('zone:server');
    if (!zone) return;
    if (!this.alarm) {
      this.alarm = this.add
        .rectangle(zone.x, zone.y, zone.width, zone.height, 0xec6a4c, 1)
        .setOrigin(0)
        .setDepth(DEPTH.alarm)
        .setBlendMode(Phaser.BlendModes.ADD)
        .setAlpha(0);
    }
    this.alarmTween?.stop();
    this.alarmTween = undefined;
    this.alarm.setVisible(on).setAlpha(0);
    if (on) {
      this.alarmTween = this.tweens.add({
        targets: this.alarm,
        alpha: { from: 0.04, to: 0.26 },
        duration: 480,
        yoyo: true,
        repeat: -1,
        ease: 'Stepped',
        easeParams: [4],
      });
    }
  }

  private setNight(on: boolean): void {
    if (on) {
      const w = this.map.widthInPixels;
      const h = this.map.heightInPixels;
      if (this.textures.exists('night-dark')) this.textures.remove('night-dark');
      if (this.textures.exists('night-glow')) this.textures.remove('night-glow');
      const dark = this.textures.createCanvas('night-dark', w, h);
      const glow = this.textures.createCanvas('night-glow', w, h);
      if (!dark || !glow) return;
      paintNight(dark.getContext(), glow.getContext(), w, h, this.collectLights());
      dark.refresh();
      glow.refresh();
      this.nightDark?.destroy();
      this.nightGlow?.destroy();
      this.nightDark = this.add.image(0, 0, 'night-dark').setOrigin(0).setDepth(DEPTH.night);
      this.nightGlow = this.add
        .image(0, 0, 'night-glow')
        .setOrigin(0)
        .setDepth(DEPTH.night + 1)
        .setBlendMode(Phaser.BlendModes.ADD);
    } else {
      this.nightDark?.setVisible(false);
      this.nightGlow?.setVisible(false);
    }
  }

  private collectLights(): Light[] {
    const lights: Light[] = [];
    const add = (x: number, y: number, radius: number, strength: number, color: Light['color']) =>
      lights.push({ x, y, radius, strength, color });
    for (const layer of this.layers.values()) {
      layer.forEachTile((t) => {
        const nm = this.propsOf(t.index).name;
        if (!nm) return;
        const cx = t.x * TILE + 8;
        const cy = t.y * TILE + 8;
        if (nm === 'lamp@0,0') add(cx, cy + 4, 52, 1.05, WARM);
        else if (/^desk_mon_(scrollb?|on|graph|alert)@/.test(nm)) add(cx, cy + 2, 30, 0.95, SCREEN);
        else if (/^window_night@\d,1$/.test(nm)) add(cx, cy + 10, 22, 0.35, MOON);
        else if (nm === 'vending@0,1') add(cx, cy, 24, 0.75, [150, 190, 255]);
        else if (nm === 'arcade@0,1') add(cx, cy - 4, 20, 0.7, LED_GREEN);
        else if (nm === 'coffee@0,1') add(cx, cy - 6, 10, 0.6, LED_RED);
        else if (/^rack_okb?@0,1$/.test(nm)) add(cx, cy, 13, 0.4, LED_GREEN);
        else if (nm === 'sign@2,0') add(cx, cy + 8, 40, 0.6, WARM);
        else if (nm === 'entrance@0,0') add(cx + 8, cy, 30, 0.45, MOON);
        else if (nm === 'copier@0,1') add(cx + 2, cy - 2, 10, 0.5, SCREEN);
      });
    }
    return lights;
  }

  // ---------------------------------------------------------------- camera
  setCamera(mode: CameraMode): void {
    this.cameraMode = mode;
    if (this.ready) this.layoutCamera();
  }

  private layoutCamera(): void {
    const cam = this.cameras.main;
    const vw = this.scale.width;
    const vh = this.scale.height;
    const mw = this.map.widthInPixels;
    const mh = this.map.heightInPixels;
    let zoom: number;
    if (this.cameraMode === 'overview') {
      zoom = Math.max(1, Math.floor(Math.min(vw / mw, vh / mh)));
    } else {
      zoom = Phaser.Math.Clamp(Math.floor(Math.min(vw / (TILE * 22), vh / (TILE * 13))), 2, 6);
    }
    cam.setZoom(zoom);
    cam.setRoundPixels(true);
    const viewW = vw / zoom;
    const viewH = vh / zoom;
    if (viewW >= mw && viewH >= mh) {
      cam.stopFollow();
      cam.removeBounds();
      cam.centerOn(mw / 2, mh / 2);
    } else {
      cam.setBounds(0, 0, mw, mh);
      cam.centerOn(this.player.sprite.x, this.player.sprite.y - 12); // snap, then glide
      cam.startFollow(this.player.sprite, true, 0.18, 0.18, 0, 12);
    }
  }

  // ----------------------------------------------------------------- input
  private bindInput(): void {
    const isTyping = (e: KeyboardEvent): boolean => {
      const t = e.target as HTMLElement | null;
      if (!t || !(t instanceof HTMLElement)) return false;
      return t.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName);
    };
    const KEYMAP: Record<string, string> = {
      ArrowUp: 'up', KeyW: 'up', ArrowDown: 'down', KeyS: 'down',
      ArrowLeft: 'left', KeyA: 'left', ArrowRight: 'right', KeyD: 'right',
    };
    const down = (e: KeyboardEvent) => {
      if (isTyping(e) || e.ctrlKey || e.metaKey || e.altKey) return;
      const dir = KEYMAP[e.code];
      if (!dir) return;
      if (e.code.startsWith('Arrow')) e.preventDefault();
      this.keys.add(dir);
      this.autoWalking = false;
    };
    const up = (e: KeyboardEvent) => {
      const dir = KEYMAP[e.code];
      if (dir) this.keys.delete(dir);
    };
    const blur = () => this.keys.clear();
    window.addEventListener('keydown', down);
    window.addEventListener('keyup', up);
    window.addEventListener('blur', blur);
    this.cleanup.push(() => {
      window.removeEventListener('keydown', down);
      window.removeEventListener('keyup', up);
      window.removeEventListener('blur', blur);
    });
  }

  walkPlayerTo(poiName: string): boolean {
    const poi = this.pois.get(poiName);
    if (!poi || !this.ready) return false;
    const path = this.grid.path(this.player.tile, { x: poi.tx, y: poi.ty });
    if (!path) return false;
    this.autoWalking = true;
    this.player.follow(path, () => {
      this.autoWalking = false;
      if (poi.sit) this.player.sit(poi.facing, poiName === 'desk:player', this.seatNudge(poi.tx, poi.ty, poi.facing));
      else this.player.face(poi.facing);
    });
    return true;
  }

  placePlayer(poiName: string): boolean {
    const poi = this.pois.get(poiName);
    if (!poi || !this.ready) return false;
    this.autoWalking = false;
    this.player.place({ x: poi.tx, y: poi.ty }, poi.facing);
    if (poi.sit) this.player.sit(poi.facing, poiName === 'desk:player', this.seatNudge(poi.tx, poi.ty, poi.facing));
    this.layoutCamera();
    return true;
  }

  private blockedAt(px: number, py: number): boolean {
    // feet box: 10 x 5 px centred on x, sitting on y
    const pts = [
      [px - 5, py - 4],
      [px + 4, py - 4],
      [px - 5, py],
      [px + 4, py],
    ];
    return pts.some(([x, y]) => !this.grid.walkable(Math.floor(x / TILE), Math.floor(y / TILE)));
  }

  private updatePlayer(dt: number): void {
    const p = this.player;
    if (this.autoWalking) {
      p.update(dt);
      return;
    }
    let dx = 0;
    let dy = 0;
    if (this.keys.has('left')) dx -= 1;
    if (this.keys.has('right')) dx += 1;
    if (this.keys.has('up')) dy -= 1;
    if (this.keys.has('down')) dy += 1;
    if (dx || dy) {
      this.stillFor = 0;
      if (p.pose === 'sit' || p.pose === 'type') p.stand();
      const step = (PLAYER_SPEED * dt) / 1000;
      const s = p.sprite;
      const facing: Facing = dy < 0 ? 'up' : dy > 0 ? 'down' : dx < 0 ? 'left' : 'right';
      const nx = s.x + dx * step;
      if (dx && !this.blockedAt(nx, s.y)) s.x = nx;
      const ny = s.y + dy * step;
      if (dy && !this.blockedAt(s.x, ny)) s.y = ny;
      p.tile = { x: Math.floor(s.x / TILE), y: Math.floor((s.y - 1) / TILE) };
      if (p.pose !== 'walk' || p.facing !== facing) {
        p.facing = facing;
        p.pose = 'walk';
        p.applyPose();
      }
    } else {
      if (p.pose === 'walk') {
        p.pose = 'stand';
        p.applyPose();
      }
      if (p.pose === 'stand') {
        this.stillFor += dt;
        if (this.stillFor > 350 && this.grid.at(p.tile.x, p.tile.y) === SEAT) {
          const poi = [...this.pois.values()].find((q) => q.tx === p.tile.x && q.ty === p.tile.y && q.sit);
          const facing = poi?.facing ?? this.seatFacing(p.tile.x, p.tile.y);
          p.place(p.tile);
          p.sit(facing, poi?.name === 'desk:player', this.seatNudge(p.tile.x, p.tile.y, facing));
        }
      }
    }
    p.sync();
  }

  /**
   * Seated sprites tuck into what is in front of them: deep behind a desk or
   * table edge (which hides the lap), a little into a couch or stool.
   */
  seatNudge(x: number, y: number, facing: Facing): { x: number; y: number } {
    const solid = (tx: number, ty: number) => this.grid.at(tx, ty) === BLOCKED;
    const above = (tx: number, ty: number) => {
      const t = this.layers.get('furniture_above')?.getTileAt(tx, ty);
      return !!t && t.index >= 0;
    };
    if (facing === 'down') return { x: 0, y: above(x, y + 1) ? 10 : 2 };
    if (facing === 'up') return { x: 0, y: above(x, y) ? -5 : -2 };
    const dx = facing === 'left' ? -1 : 1;
    return { x: solid(x + dx, y) ? dx * 3 : 0, y: 1 };
  }

  private seatFacing(x: number, y: number): Facing {
    for (const layer of ['furniture_above', 'furniture_below']) {
      const nm = this.nameAt(layer, x, y);
      const m = nm?.match(/^m?chair_(down|up|left|right)$/);
      if (m) return m[1] as Facing;
    }
    return 'down';
  }

  // ---------------------------------------------------------------- update
  update(_time: number, dt: number): void {
    if (!this.ready) return;
    this.director.tick();
    for (const npc of this.npcs.values()) {
      npc.walker.update(dt);
      const lift = npc.walker.bubbleKind ? 48 : 36; // keep the name tag clear of a status bubble
      npc.tag.setPosition(Math.round(npc.walker.sprite.x), Math.round(npc.walker.sprite.y) - lift);
    }
    this.updatePlayer(dt);
    const bob = Math.floor(this.time.now / 400) % 2;
    this.marker.setPosition(Math.round(this.player.sprite.x), Math.round(this.player.sprite.y) - 33 - bob);
    this.marker.setVisible(this.player.sprite.visible);
  }

  snapshot(): OfficeSnapshot {
    const p = this.player;
    return {
      ready: this.ready,
      mode: this.mode,
      camera: this.cameraMode,
      zoom: this.ready ? this.cameras.main.zoom : 0,
      player: p ? { tx: p.tile.x, ty: p.tile.y, facing: p.facing, pose: p.pose } : null,
      npcs: [...this.npcs.values()].map((n) => ({
        id: n.persona?.id ?? n.slug,
        tx: n.walker.tile.x,
        ty: n.walker.tile.y,
        facing: n.walker.facing,
        pose: n.walker.pose,
        bubble: n.walker.bubbleKind,
        visible: n.walker.sprite.visible,
      })),
    };
  }

  /** Screen position of an NPC (for tests that click on one). */
  screenPositionOf(slug: string): { x: number; y: number } | null {
    const npc = this.npcs.get(slug);
    if (!npc) return null;
    const cam = this.cameras.main;
    const s = npc.walker.sprite;
    return {
      x: (s.x - cam.worldView.x) * cam.zoom,
      y: (s.y - 14 - cam.worldView.y) * cam.zoom,
    };
  }

  private teardown(): void {
    for (const fn of this.cleanup.splice(0)) fn();
    this.keys.clear();
  }
}
