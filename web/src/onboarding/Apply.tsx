import { useState } from 'react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import { useAsync } from '../ui/hooks';
import { useStore } from '../store';
import { Frame } from './Frame';

export function Apply() {
  const { company } = useParams();
  const nav = useNavigate();
  const draft = useStore((s) => s.draft);
  const setDraft = useStore((s) => s.setDraft);
  const [name, setName] = useState(draft.name);
  const { data } = useAsync(() => api.catalog(), []);
  const c = data?.find((x) => x.id === company);

  if (data && (!c || !c.kit_ready)) return <Navigate to="/careers" replace />;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setDraft({ companyId: company ?? null, name: name.trim(), signed: false });
    nav('/offer');
  };

  return (
    <Frame step={1}>
      <form className="panel narrow" onSubmit={submit}>
        <p className="eyebrow">Application</p>
        <h1>Apply to {c?.name ?? '…'}</h1>
        <p>{c?.pitch}</p>
        <label className="field">
          <span>Your name</span>
          <input autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder="Full name" aria-label="Your name" />
        </label>
        <div className="callout">
          <b>About the interview</b>
          <p>
            A placement interview arrives in a later version. It will set your starting level. For now, everyone starts at Software
            Engineer I (L1).
          </p>
        </div>
        <div className="row">
          <button type="button" className="btn" onClick={() => nav('/careers')}>
            Back
          </button>
          <button type="submit" className="btn primary" disabled={!name.trim()}>
            Submit application
          </button>
        </div>
      </form>
    </Frame>
  );
}
