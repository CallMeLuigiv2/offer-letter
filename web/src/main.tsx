import '@fontsource/schibsted-grotesk/400.css';
import '@fontsource/schibsted-grotesk/500.css';
import '@fontsource/schibsted-grotesk/700.css';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/500.css';
import '@fontsource/pixelify-sans/500.css';
import { MotionConfig } from 'motion/react';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { MOCK, connectEvents } from './api';
import { App } from './App';
import { useStore, wireEvents } from './store';
import './styles.css';

document.documentElement.dataset.theme = useStore.getState().theme;
wireEvents();
if (!MOCK) connectEvents();

const root = createRoot(document.getElementById('root') as HTMLElement);
root.render(<div className="splash">Opening Offer Letter…</div>);

void useStore
  .getState()
  .load()
  .then(() => {
    const { loadError } = useStore.getState();
    root.render(
      <StrictMode>
        <MotionConfig reducedMotion="user">
          <BrowserRouter>
            {loadError ? (
              <div className="splash">
                <p>{loadError}</p>
                <button className="btn primary" onClick={() => location.reload()}>Try again</button>
              </div>
            ) : (
              <App />
            )}
          </BrowserRouter>
        </MotionConfig>
      </StrictMode>,
    );
  });
