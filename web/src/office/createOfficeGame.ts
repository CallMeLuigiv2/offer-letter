/**
 * Create the office Phaser game inside a DOM element and return a small
 * controller. Commands sent before the scene finishes loading are applied
 * once it is ready.
 */
import Phaser from 'phaser';
import { OfficeScene } from './OfficeScene';
import type { CameraMode, OfficeController, OfficeOptions, PersonaInfo, SceneMode } from './types';

export function createOfficeGame(parent: HTMLElement, options: OfficeOptions): OfficeController {
  const opts: OfficeOptions = { ...options, personas: [...options.personas] };
  const scene = new OfficeScene(opts);
  const game = new Phaser.Game({
    type: Phaser.AUTO,
    parent,
    backgroundColor: '#1b1726',
    pixelArt: true,
    roundPixels: true,
    antialias: false,
    banner: false,
    audio: { noAudio: true },
    // the office reads its own key events so typing in chat never moves you
    input: { keyboard: false, gamepad: false },
    scale: {
      mode: Phaser.Scale.RESIZE,
      width: Math.max(1, parent.clientWidth || 800),
      height: Math.max(1, parent.clientHeight || 600),
    },
    scene: [scene],
  });

  let destroyed = false;
  let pendingMode: SceneMode | null = null;
  let pendingCamera: CameraMode | null = null;

  const whenReady = (fn: () => void) => {
    if (destroyed) return;
    if (scene.ready) fn();
    else game.events.once('office-ready', () => !destroyed && fn());
  };

  game.events.once('office-ready', () => {
    if (pendingMode) scene.setMode(pendingMode);
    if (pendingCamera) scene.setCamera(pendingCamera);
  });

  return {
    setMode(mode) {
      if (scene.ready) scene.setMode(mode);
      else pendingMode = mode;
    },
    getMode() {
      return scene.ready ? scene.getMode() : pendingMode ?? opts.mode ?? 'day';
    },
    setCamera(mode) {
      if (scene.ready) scene.setCamera(mode);
      else pendingCamera = mode;
    },
    setPersonas(personas: PersonaInfo[]) {
      scene.setPersonas(personas);
    },
    setOnPersonaClick(cb) {
      scene.setOnPersonaClick(cb);
    },
    walkPlayerTo(poi) {
      if (scene.ready) return scene.walkPlayerTo(poi);
      whenReady(() => scene.walkPlayerTo(poi));
      return true;
    },
    placePlayer(poi) {
      if (scene.ready) return scene.placePlayer(poi);
      whenReady(() => scene.placePlayer(poi));
      return true;
    },
    snapshot() {
      return scene.ready
        ? scene.snapshot()
        : { ready: false, mode: opts.mode ?? 'day', camera: opts.camera ?? 'follow', zoom: 0, player: null, npcs: [] };
    },
    screenPositionOf(id) {
      return scene.ready ? scene.screenPositionOf(id.split('.').pop()!.toLowerCase()) : null;
    },
    destroy() {
      if (destroyed) return;
      destroyed = true;
      game.destroy(true);
    },
  };
}
