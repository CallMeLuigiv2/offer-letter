import { act, fireEvent, render, screen } from '@testing-library/react';
import { Portrait } from './Portrait';

afterEach(() => vi.useRealTimers());

describe('Portrait', () => {
  it('flaps between the expression and its _talk frame every 120 ms while talking', () => {
    vi.useFakeTimers();
    render(<Portrait personaId="kilnworks.ines" color="#f38ba8" expression="happy" talking />);
    const src = () => screen.getByTestId('portrait').getAttribute('data-src');
    expect(src()).toBe('/portraits/kilnworks/ines/happy.webp');
    act(() => void vi.advanceTimersByTime(120));
    expect(src()).toBe('/portraits/kilnworks/ines/happy_talk.webp');
    act(() => void vi.advanceTimersByTime(120));
    expect(src()).toBe('/portraits/kilnworks/ines/happy.webp');
  });

  it('stays on the still frame when not talking', () => {
    vi.useFakeTimers();
    render(<Portrait personaId="kilnworks.ines" color="#f38ba8" />);
    act(() => void vi.advanceTimersByTime(500));
    expect(screen.getByTestId('portrait').getAttribute('data-src')).toBe('/portraits/kilnworks/ines/neutral.webp');
  });

  it('falls back from a missing expression to neutral, then to the placeholder bust', () => {
    render(<Portrait personaId="kilnworks.dana" color="#a6e3a1" expression="surprised" />);
    fireEvent.error(screen.getByTestId('portrait'));
    expect(screen.getByTestId('portrait').getAttribute('data-src')).toBe('/portraits/kilnworks/dana/neutral.webp');
    fireEvent.error(screen.getByTestId('portrait'));
    expect(screen.getByTestId('portrait-fallback')).toBeInTheDocument();
  });

  it('keeps the still frame if the talk frame is missing', () => {
    vi.useFakeTimers();
    render(<Portrait personaId="kilnworks.kenji" color="#89b4fa" expression="neutral" talking />);
    act(() => void vi.advanceTimersByTime(120));
    fireEvent.error(screen.getByTestId('portrait')); // the _talk file 404s
    act(() => void vi.advanceTimersByTime(600));
    expect(screen.getByTestId('portrait').getAttribute('data-src')).toBe('/portraits/kilnworks/kenji/neutral.webp');
  });
});
