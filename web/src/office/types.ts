/** Shared types for the pixel office (Phaser scene + React wrapper). */

export type SceneMode = 'day' | 'standup' | 'incident' | 'night';
export type Facing = 'down' | 'left' | 'right' | 'up';
export type CameraMode = 'follow' | 'overview';

export const SCENE_MODES: readonly SceneMode[] = ['day', 'standup', 'incident', 'night'];

export interface PersonaInfo {
  id: string;
  name: string;
  color: string;
}

/** Same field names as a cast recipe in characters.json. */
export interface AvatarSpec {
  skin: string;
  hair: string;
  hairColor: string;
  streak?: string | null;
  shirt: string;
  shirtColor: string;
  outer?: string | null;
  outerColor?: string;
  pantsColor: string;
  shoes: string;
  acc?: string[];
}

/** The web app's simple avatar (onboarding picker): hex colours + a hair-style index. */
export interface SimpleAvatar {
  hairStyle: number | string;
  hairColor: string;
  skin: string;
  shirt: string;
}

export interface PlayerInfo {
  name?: string;
  /** Either a full layered spec or the simple picker avatar (mapped to the nearest ramps). */
  avatar?: AvatarSpec | SimpleAvatar | null;
}

export interface OfficeOptions {
  personas: PersonaInfo[];
  player?: PlayerInfo;
  mode?: SceneMode;
  camera?: CameraMode;
  /** Where tileset.png, kilnworks.tmj and characters/ are served. Default '/office/'. */
  assetBase?: string;
  onPersonaClick?: (id: string) => void;
}

export interface NpcSnapshot {
  id: string;
  tx: number;
  ty: number;
  facing: Facing;
  pose: string;
  bubble: string | null;
  visible: boolean;
}

export interface OfficeSnapshot {
  ready: boolean;
  mode: SceneMode;
  camera: CameraMode;
  zoom: number;
  player: { tx: number; ty: number; facing: Facing; pose: string } | null;
  npcs: NpcSnapshot[];
}

export interface OfficeController {
  setMode(mode: SceneMode): void;
  getMode(): SceneMode;
  setCamera(mode: CameraMode): void;
  setPersonas(personas: PersonaInfo[]): void;
  setOnPersonaClick(cb: ((id: string) => void) | undefined): void;
  /** Walk the player to a named POI from the map ("desk:player", "coffee", ...). */
  walkPlayerTo(poi: string): boolean;
  /** Move the player instantly (tests and scene setup). */
  placePlayer(poi: string): boolean;
  snapshot(): OfficeSnapshot;
  /** Where a teammate is drawn, in CSS pixels relative to the office element. */
  screenPositionOf(id: string): { x: number; y: number } | null;
  destroy(): void;
}
