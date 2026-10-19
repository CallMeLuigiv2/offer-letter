import { motion } from 'motion/react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useStore } from '../store';
import { Frame } from './Frame';

const fold = {
  hidden: { rotateX: -90, opacity: 0 },
  shown: { rotateX: 0, opacity: 1 },
};

export function Offer() {
  const nav = useNavigate();
  const draft = useStore((s) => s.draft);
  const setDraft = useStore((s) => s.setDraft);
  if (!draft.companyId || !draft.name) return <Navigate to="/careers" replace />;
  const today = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

  const sign = () => {
    setDraft({ signed: true });
    nav('/profile');
  };

  return (
    <Frame step={2}>
      <div className="letter-wrap">
        <motion.article
          className="letter"
          data-testid="offer-letter"
          initial="hidden"
          animate="shown"
          variants={{ shown: { transition: { staggerChildren: 0.45 } } }}
          style={{ perspective: 1200 }}
          aria-label="Offer letter"
        >
          <motion.header className="letterhead" variants={fold} transition={{ duration: 0.5, ease: 'easeOut' }} style={{ transformOrigin: 'top' }}>
            <b>Kilnworks</b>
            <span>{today}</span>
          </motion.header>
          <motion.div variants={fold} transition={{ duration: 0.5, ease: 'easeOut' }} style={{ transformOrigin: 'top' }}>
            <p>Dear {draft.name},</p>
            <p>
              We would like to offer you the position of <b>Software Engineer I</b> on the Serving team at Kilnworks. You would work on the
              tools we use to measure how fast our inference API really is.
            </p>
            <p>The offer includes:</p>
            <ul>
              <li>A seat on the Serving team, with Dana Whitfield as your manager</li>
              <li>Your own laptop setup: a clone of kiln-bench, ready to run</li>
              <li>A first ticket, KLN-01, and teammates who will answer questions</li>
              <li>Code review from people who expect you to explain your reasoning</li>
            </ul>
            <p>Please sign below to accept. We are looking forward to working with you.</p>
          </motion.div>
          <motion.footer className="letter-sign" variants={fold} transition={{ duration: 0.5, ease: 'easeOut' }} style={{ transformOrigin: 'top' }}>
            <div>
              <p className="sig">Dana Whitfield</p>
              <p className="muted small">Engineering Manager, Kilnworks</p>
            </div>
            <button className="btn primary big" onClick={sign}>
              Sign and accept
            </button>
          </motion.footer>
        </motion.article>
      </div>
    </Frame>
  );
}
