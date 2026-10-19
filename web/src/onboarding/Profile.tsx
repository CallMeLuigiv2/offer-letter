import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import type { Avatar } from '../api';
import { DEFAULT_AVATAR } from '../lib/util';
import { useStore } from '../store';
import { errText } from '../ui/hooks';
import { HAIR_COLORS, HAIR_STYLES, PlayerAvatar, SHIRT_COLORS, SKIN_TONES } from '../ui/Avatars';
import { Frame } from './Frame';

const PRONOUNS = ['she/her', 'he/him', 'they/them'];

function Swatches({ label, colors, value, onPick }: { label: string; colors: string[]; value: string; onPick: (c: string) => void }) {
  return (
    <div className="field">
      <span>{label}</span>
      <div className="swatches" role="radiogroup" aria-label={label}>
        {colors.map((c) => (
          <button
            key={c}
            type="button"
            role="radio"
            aria-checked={c === value}
            aria-label={`${label} ${c}`}
            className={`swatch ${c === value ? 'on' : ''}`}
            style={{ background: c }}
            onClick={() => onPick(c)}
          />
        ))}
      </div>
    </div>
  );
}

export function Profile() {
  const nav = useNavigate();
  const draft = useStore((s) => s.draft);
  const completeProfile = useStore((s) => s.completeProfile);
  const acceptOffer = useStore((s) => s.acceptOffer);
  const [name, setName] = useState(draft.name);
  const [pronouns, setPronouns] = useState('they/them');
  const [custom, setCustom] = useState('');
  const [avatar, setAvatar] = useState<Avatar>(DEFAULT_AVATAR);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!draft.companyId || !draft.signed) return <Navigate to="/careers" replace />;

  const set = (patch: Partial<Avatar>) => setAvatar({ ...avatar, ...patch });
  const finalPronouns = pronouns === 'custom' ? custom.trim() : pronouns;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      setBusy('Creating your profile…');
      await completeProfile({ name: name.trim(), pronouns: finalPronouns || undefined, avatar });
      setBusy('Setting up your laptop. This clones the repo, so it can take a moment…');
      await acceptOffer(draft.companyId as string);
      nav('/badge');
    } catch (err) {
      setError(errText(err));
      setBusy(null);
    }
  };

  return (
    <Frame step={3}>
      <form className="panel profile" onSubmit={submit}>
        <div className="profile-form">
          <p className="eyebrow">Profile</p>
          <h1>Who are you at work?</h1>
          <label className="field">
            <span>Name</span>
            <input value={name} onChange={(e) => setName(e.target.value)} aria-label="Name" />
          </label>
          <div className="field">
            <span>Pronouns</span>
            <div className="chips" role="radiogroup" aria-label="Pronouns">
              {[...PRONOUNS, 'custom'].map((p) => (
                <button key={p} type="button" role="radio" aria-checked={pronouns === p} className={`chip ${pronouns === p ? 'on' : ''}`} onClick={() => setPronouns(p)}>
                  {p === 'custom' ? 'Other' : p}
                </button>
              ))}
            </div>
            {pronouns === 'custom' && <input value={custom} onChange={(e) => setCustom(e.target.value)} placeholder="Your pronouns" aria-label="Custom pronouns" />}
          </div>
          <div className="field">
            <span>Hair style</span>
            <div className="chips" role="radiogroup" aria-label="Hair style">
              {HAIR_STYLES.map((h, i) => (
                <button key={h} type="button" role="radio" aria-checked={avatar.hairStyle === i} className={`chip ${avatar.hairStyle === i ? 'on' : ''}`} onClick={() => set({ hairStyle: i })}>
                  {h}
                </button>
              ))}
            </div>
          </div>
          <Swatches label="Hair colour" colors={HAIR_COLORS} value={avatar.hairColor} onPick={(c) => set({ hairColor: c })} />
          <Swatches label="Skin tone" colors={SKIN_TONES} value={avatar.skin} onPick={(c) => set({ skin: c })} />
          <Swatches label="Shirt colour" colors={SHIRT_COLORS} value={avatar.shirt} onPick={(c) => set({ shirt: c })} />
        </div>
        <div className="profile-preview">
          <PlayerAvatar avatar={avatar} size={192} square />
          <p className="small muted">{name || 'Your name'}</p>
          {error && <p className="error" role="alert">{error}</p>}
          {busy && <p className="muted small" role="status">{busy}</p>}
          <button className="btn primary big" type="submit" disabled={!name.trim() || !!busy}>
            Create profile
          </button>
        </div>
      </form>
    </Frame>
  );
}
