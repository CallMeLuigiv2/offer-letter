import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

const STEPS = ['Careers', 'Apply', 'Offer', 'Profile', 'Badge', 'Laptop'];

export function Frame({ step, children, wide }: { step?: number; children: ReactNode; wide?: boolean }) {
  return (
    <div className="ob">
      <header className="ob-head">
        <Link to="/careers" className="logo">
          <span className="logo-mark" aria-hidden="true" />
          OFFER LETTER
        </Link>
        {step !== undefined && (
          <ol className="ob-steps" aria-label="Onboarding progress">
            {STEPS.map((s, i) => (
              <li key={s} className={i === step ? 'on' : i < step ? 'past' : ''} aria-current={i === step ? 'step' : undefined}>
                {s}
              </li>
            ))}
          </ol>
        )}
      </header>
      <main className={`ob-main ${wide ? 'wide' : ''}`}>{children}</main>
    </div>
  );
}
