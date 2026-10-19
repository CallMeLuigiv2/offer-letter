import { StrictMode, useState } from 'react';
import { createRoot } from 'react-dom/client';
import OfficeView from '@office/OfficeView';
import type { AvatarSpec, CameraMode, OfficeController, SceneMode } from '@office/types';
import { composeAvatarCanvas, loadLayerImages, normalizeAvatar, type CharactersMeta } from '@office/avatar';

// Query params: mode, camera, bare (hide toolbar), avatar=custom, w/h (fixed size)
const q = new URLSearchParams(location.search);
const PERSONAS = [
  { id: 'kilnworks.dana', name: 'Dana Whitfield', color: '#6b8f3e' },
  { id: 'kilnworks.kenji', name: 'Kenji Mori', color: '#56587a' },
  { id: 'kilnworks.ines', name: 'Ines Duarte', color: '#bb3b42' },
  { id: 'kilnworks.theo', name: 'Theo Lindqvist', color: '#a9762c' },
  { id: 'kilnworks.amara', name: 'Amara Osei', color: '#e3b041' },
  { id: 'kilnworks.leo', name: 'Leo Park', color: '#3456a8' },
];
const CUSTOM: AvatarSpec = {
  skin: 'tan', hair: 'long', hairColor: 'brown', shirt: 'hoodie', shirtColor: 'red',
  pantsColor: 'black', shoes: 'white', acc: ['glasses'],
};

declare global {
  interface Window {
    __office?: OfficeController;
    __clicks: string[];
    __remount?: () => void;
    __composeMismatch?: (id: string) => Promise<number>;
    __normalize?: (a: unknown) => Promise<AvatarSpec | null>;
  }
}
window.__clicks = [];
// the web app's onboarding avatar shape: hex colours + a hair-style index
const SIMPLE = { hairStyle: 4, hairColor: '#2b1d14', skin: '#7a4e32', shirt: '#89b4fa' };
window.__normalize = async (a: unknown) => {
  const meta = (await (await fetch('/office/characters/characters.json')).json()) as CharactersMeta;
  return normalizeAvatar(a, meta);
};

/** Compose a cast member from layers in TS and count pixels that differ from the Python sheet. */
window.__composeMismatch = async (id: string) => {
  const base = '/office/characters/';
  const meta = (await (await fetch(base + 'characters.json')).json()) as CharactersMeta;
  const recipe = id === 'player_default' ? meta.playerDefault : meta.cast.find((c) => c.id === id)!;
  const images = await loadLayerImages(meta, recipe, base);
  const mine = composeAvatarCanvas(meta, images, recipe);
  const ref = await new Promise<HTMLImageElement>((res, rej) => {
    const img = new Image();
    img.onload = () => res(img);
    img.onerror = rej;
    img.src = base + recipe.sheet;
  });
  const c = document.createElement('canvas');
  c.width = mine.width;
  c.height = mine.height;
  const ctx = c.getContext('2d')!;
  ctx.drawImage(ref, 0, 0);
  const a = ctx.getImageData(0, 0, c.width, c.height).data;
  const b = mine.getContext('2d')!.getImageData(0, 0, c.width, c.height).data;
  let diff = 0;
  for (let i = 0; i < a.length; i += 4) {
    if (a[i] !== b[i] || a[i + 1] !== b[i + 1] || a[i + 2] !== b[i + 2] || a[i + 3] !== b[i + 3]) diff++;
  }
  return diff;
};

function App() {
  const [mode, setMode] = useState<SceneMode>((q.get('mode') as SceneMode) ?? 'day');
  const [camera, setCamera] = useState<CameraMode>((q.get('camera') as CameraMode) ?? 'follow');
  const [mounted, setMounted] = useState(true);
  const [last, setLast] = useState('');
  window.__remount = () => {
    setMounted(false);
    setTimeout(() => setMounted(true), 50);
  };
  const w = q.get('w');
  const h = q.get('h');
  const style = w && h ? { width: `${w}px`, height: `${h}px` } : { width: '100vw', height: '100vh' };
  return (
    <>
      {!q.has('bare') && (
        <div className="bar">
          {(['day', 'standup', 'incident', 'night'] as SceneMode[]).map((m) => (
            <button key={m} aria-pressed={mode === m} onClick={() => setMode(m)}>{m}</button>
          ))}
          {(['follow', 'overview'] as CameraMode[]).map((c) => (
            <button key={c} aria-pressed={camera === c} onClick={() => setCamera(c)}>{c}</button>
          ))}
          <button onClick={() => window.__remount?.()}>remount</button>
          <input placeholder="type here: keys must not move you" />
        </div>
      )}
      {!q.has('bare') && last && <div className="log">clicked {last}</div>}
      <div style={style}>
        {mounted && (
          <OfficeView
            personas={PERSONAS}
            mode={mode}
            camera={camera}
            player={
              q.get('avatar') === 'custom'
                ? { name: 'Luigi', avatar: CUSTOM }
                : q.get('avatar') === 'simple'
                  ? { name: 'Luigi', avatar: SIMPLE }
                  : { name: 'Luigi' }
            }
            onPersonaClick={(id) => {
              window.__clicks.push(id);
              setLast(id);
            }}
            onReady={(o) => {
              window.__office = o;
            }}
          />
        )}
      </div>
    </>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
