import { useEffect, useRef, useState } from 'react';
import type { CameraMode, OfficeController, PlayerInfo, SceneMode } from './types';

/**
 * The walkable pixel office. Loads Phaser lazily (so it stays out of the main
 * bundle and out of jsdom tests), mounts the game on mount and destroys it on
 * unmount (safe under React StrictMode's double mount).
 *
 * Required: `personas` (the company's teammates) and `onPersonaClick`.
 * Optional: the player's avatar, the scene mode, the camera mode, and
 * `onReady` to get the controller (setMode, walkPlayerTo, snapshot...).
 */
export default function OfficeView(props: {
  personas: { id: string; name: string; color: string }[];
  onPersonaClick?: (id: string) => void;
  player?: PlayerInfo;
  mode?: SceneMode;
  camera?: CameraMode;
  assetBase?: string;
  onReady?: (office: OfficeController) => void;
  className?: string;
}): JSX.Element {
  const hostRef = useRef<HTMLDivElement>(null);
  const officeRef = useRef<OfficeController | null>(null);
  const [failed, setFailed] = useState(false);
  // Latest props, read by the game without re-creating it.
  const latest = useRef(props);
  latest.current = props;

  const avatarKey = JSON.stringify(props.player?.avatar ?? null);
  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    let office: OfficeController | null = null;
    let cancelled = false;
    import('./createOfficeGame')
      .then(({ createOfficeGame }) => {
        if (cancelled) return;
        const p = latest.current;
        office = createOfficeGame(host, {
          personas: p.personas,
          player: p.player,
          mode: p.mode,
          camera: p.camera,
          assetBase: p.assetBase,
          onPersonaClick: (id) => latest.current.onPersonaClick?.(id),
        });
        officeRef.current = office;
        p.onReady?.(office);
      })
      .catch((err: unknown) => {
        console.warn('office: could not start the pixel office', err);
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
      office?.destroy();
      if (officeRef.current === office) officeRef.current = null;
    };
  }, [avatarKey, props.assetBase]);

  useEffect(() => {
    if (props.mode) officeRef.current?.setMode(props.mode);
  }, [props.mode]);

  useEffect(() => {
    if (props.camera) officeRef.current?.setCamera(props.camera);
  }, [props.camera]);

  const personaKey = props.personas.map((p) => `${p.id}|${p.name}|${p.color}`).join(',');
  useEffect(() => {
    officeRef.current?.setPersonas(latest.current.personas);
  }, [personaKey]);

  return (
    <div
      ref={hostRef}
      className={props.className}
      data-testid="office-view"
      role="application"
      aria-label="Office floor. Walk with WASD or the arrow keys; click a teammate to open a chat."
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        minHeight: 320,
        overflow: 'hidden',
        background: '#1b1726',
        imageRendering: 'pixelated',
      }}
    >
      {failed && (
        <p style={{ color: '#d3d8e8', padding: 16, margin: 0 }}>
          The office view couldn't start in this browser. Chat and tickets still work from the sidebar.
        </p>
      )}
    </div>
  );
}
