// One clip on screen: the <video> with its subtitles track and our own controls, or (when the clip isn't
// rendered yet) the script lines as text with a "Done reading" button that counts as the clip ending.
import { useEffect, useState, type RefObject } from 'react';
import type { ScriptLine } from '../api/types';
import { findPersona } from '../lib/util';
import { useStore } from '../store';
import { fmtTime } from './machine';

export interface StageProps {
  base: string;
  file: string | null;
  vtt: string | null;
  lines?: ScriptLine[];
  durationHint?: number | null;
  captions: boolean;
  onCaptions: (on: boolean) => void;
  onEnded: () => void;
  videoRef: RefObject<HTMLVideoElement>;
  /** Chapter navigation; left out for branch clips and the plan video. */
  onReplay?: () => void;
  onPrev?: (() => void) | null;
  onNext?: (() => void) | null;
  label?: string;
}

export function TextScene({ lines, onDone }: { lines: ScriptLine[]; onDone: () => void }) {
  const personas = useStore((s) => s.personas);
  return (
    <div className="x-text" data-testid="text-scene">
      <p className="eyebrow">This clip isn't rendered yet, so here is its script</p>
      <ol className="x-lines">
        {lines.map((l, i) => {
          const p = l.who ? findPersona(personas, l.who) : undefined;
          return (
            <li key={i}>
              <b style={p ? { color: p.color } : undefined}>{p?.name.split(' ')[0] ?? 'Narrator'}</b> {l.say}
            </li>
          );
        })}
      </ol>
      <button type="button" className="btn primary" onClick={onDone}>
        Done reading
      </button>
    </div>
  );
}

export function Stage({ base, file, vtt, lines, durationHint, captions, onCaptions, onEnded, videoRef, onReplay, onPrev, onNext, label }: StageProps) {
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(durationHint ?? 0);
  const [paused, setPaused] = useState(true);

  useEffect(() => {
    setTime(0);
    setDuration(durationHint ?? 0);
  }, [file, durationHint]);

  const syncTrack = () => {
    const tracks = videoRef.current?.textTracks;
    if (tracks && tracks.length) tracks[0].mode = captions ? 'showing' : 'hidden';
  };
  useEffect(syncTrack, [captions, file]); // eslint-disable-line react-hooks/exhaustive-deps

  // Start playing when a clip is mounted. Autoplay may be refused; then the play button is there.
  useEffect(() => {
    const v = videoRef.current;
    if (!v || !file) return;
    const p = v.play?.();
    if (p && typeof p.catch === 'function') p.catch(() => setPaused(true));
  }, [file, videoRef]);

  const toggle = () => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) void v.play?.()?.catch?.(() => undefined);
    else v.pause();
  };
  const seek = (t: number) => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = Math.max(0, Math.min(t, duration || t));
    setTime(v.currentTime);
  };

  return (
    <div className="x-stage">
      {label && <p className="x-stage-label">{label}</p>}
      <div className="x-screen">
        {file ? (
          <video
            ref={videoRef}
            className="x-video"
            data-testid="explainer-video"
            src={base + file}
            playsInline
            preload="auto"
            onEnded={() => {
              setPaused(true);
              onEnded();
            }}
            onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)}
            onLoadedMetadata={(e) => {
              if (Number.isFinite(e.currentTarget.duration)) setDuration(e.currentTarget.duration);
              syncTrack();
            }}
            onPlay={() => setPaused(false)}
            onPause={() => setPaused(true)}
          >
            {vtt && <track kind="subtitles" src={base + vtt} srcLang="en" label="English" default={captions} />}
          </video>
        ) : (
          <TextScene lines={lines ?? []} onDone={onEnded} />
        )}
      </div>
      {file && (
        <div className="x-controls" role="group" aria-label="Video controls">
          <button type="button" className="x-ctl" onClick={toggle} aria-label={paused ? 'Play' : 'Pause'} title="Space">
            {paused ? '▶' : '❚❚'}
          </button>
          <input
            type="range"
            className="x-scrub"
            aria-label="Position in this chapter"
            min={0}
            max={duration || 0}
            step={0.1}
            value={Math.min(time, duration || 0)}
            onChange={(e) => seek(Number(e.target.value))}
          />
          <span className="x-time mono small" aria-live="off">
            {fmtTime(time)} / {fmtTime(duration)}
          </span>
          {onReplay && (
            <button type="button" className="x-ctl" onClick={onReplay} aria-label="Replay chapter" title="Replay chapter">
              ↺
            </button>
          )}
          {onPrev !== undefined && (
            <button type="button" className="x-ctl" onClick={() => onPrev?.()} disabled={!onPrev} aria-label="Previous chapter" title="Previous chapter">
              ⏮
            </button>
          )}
          {onNext !== undefined && (
            <button type="button" className="x-ctl" onClick={() => onNext?.()} disabled={!onNext} aria-label="Next chapter" title="Next chapter">
              ⏭
            </button>
          )}
          {vtt && (
            <button type="button" className={`x-ctl cc ${captions ? 'on' : ''}`} onClick={() => onCaptions(!captions)} aria-pressed={captions} aria-label="Subtitles" title="Subtitles (C)">
              CC
            </button>
          )}
        </div>
      )}
    </div>
  );
}
