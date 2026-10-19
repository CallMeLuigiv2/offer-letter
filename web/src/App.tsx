import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { ChannelView } from './app/Channel';
import { Shell } from './app/Shell';
import { TaskBoard } from './app/TaskBoard';
import { Apply } from './onboarding/Apply';
import { Badge } from './onboarding/Badge';
import { Careers } from './onboarding/Careers';
import { Offer } from './onboarding/Offer';
import { Profile } from './onboarding/Profile';
import { Setup } from './onboarding/Setup';
import { ReviewPage } from './review/ReviewPage';
import { ChangePage } from './ticket/Change';
import { ExplainPage } from './ticket/Explain';
import { OwnPage } from './ticket/Own';
import { QuizPage } from './ticket/Quiz';
import { Debriefs, TicketLayout, TicketOverview } from './ticket/TicketLayout';
import { dmPartner, parseAvatar } from './lib/util';
import { useStore } from './store';
import { Toasts } from './ui/Toasts';

const OfficeView = lazy(() => import('./office/OfficeView'));

function Root() {
  const employment = useStore((s) => s.employment);
  const channels = useStore((s) => s.channels);
  if (!employment) return <Navigate to="/careers" replace />;
  const general = channels.find((c) => c.name === 'general') ?? channels[0];
  return <Navigate to={general ? `/channels/${general.id}` : '/tickets'} replace />;
}

function Guard({ children }: { children: React.ReactNode }) {
  const employment = useStore((s) => s.employment);
  if (!employment) return <Navigate to="/careers" replace />;
  return <>{children}</>;
}

function Office() {
  const personas = useStore((s) => s.personas);
  const channels = useStore((s) => s.channels);
  const player = useStore((s) => s.player);
  const nav = useNavigate();
  return (
    <Suspense fallback={<div className="pane-pad muted">Loading the office…</div>}>
      <OfficeView
        personas={personas.map((p) => ({ id: p.id, name: p.name, color: p.color }))}
        player={player ? { name: player.name, avatar: parseAvatar(player) } : undefined}
        onPersonaClick={(id) => {
          const dm = channels.find((c) => c.kind === 'dm' && dmPartner(c, personas)?.id === id);
          if (dm) nav(`/channels/${dm.id}`);
        }}
      />
    </Suspense>
  );
}

export function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Root />} />
        <Route path="/careers" element={<Careers />} />
        <Route path="/join/:company" element={<Apply />} />
        <Route path="/offer" element={<Offer />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/badge" element={<Badge />} />
        <Route path="/setup" element={<Setup />} />
        <Route
          element={
            <Guard>
              <Shell />
            </Guard>
          }
        >
          <Route path="/channels/:id" element={<ChannelView />} />
          <Route path="/tickets" element={<TaskBoard />} />
          <Route path="/tickets/:id" element={<TicketLayout />}>
            <Route index element={<TicketOverview />} />
            <Route path="review" element={<ReviewPage />} />
            <Route path="quiz" element={<QuizPage />} />
            <Route path="explain" element={<ExplainPage />} />
            <Route path="change" element={<ChangePage />} />
            <Route path="own" element={<OwnPage />} />
            <Route path="debriefs" element={<Debriefs />} />
          </Route>
          <Route path="/office" element={<Office />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toasts />
    </>
  );
}
