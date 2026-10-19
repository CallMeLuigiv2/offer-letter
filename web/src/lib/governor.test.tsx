import { act, render, screen } from '@testing-library/react';
import { bannerFor, resetDate, teammatesAvailable } from './governor';
import { GovernorBanner } from '../app/Shell';
import { useStore } from '../store';
import type { Governor } from '../api/types';

const g = (mode: Governor['mode'], resets_at: Governor['resets_at'] = null): Governor => ({
  five_hour_util: 0.5,
  seven_day_util: 0.1,
  resets_at,
  mode,
});

describe('governor banner', () => {
  it('is hidden in normal mode and with no governor', () => {
    expect(bannerFor(g('normal'))).toBeNull();
    expect(bannerFor(null)).toBeNull();
  });
  it('says the team is out to lunch until the reset time', () => {
    const at = new Date(2026, 9, 19, 5, 10, 0);
    const b = bannerFor(g('lunch', at.toISOString()))!;
    expect(b.mode).toBe('lunch');
    expect(b.text).toBe('The team is out to lunch until 5:10 AM. You can still read code, take quizzes and run benchmarks.');
  });
  it('accepts epoch seconds', () => {
    const at = new Date(2026, 9, 19, 17, 5, 0);
    expect(resetDate({ resets_at: Math.floor(at.getTime() / 1000) })?.getTime()).toBe(at.getTime());
  });
  it('still reads sensibly without a reset time', () => {
    expect(bannerFor(g('lunch'))!.text).toMatch(/^The team is out to lunch\. You can still read code/);
  });
  it('has a separate message for thrifty', () => {
    expect(bannerFor(g('thrifty'))!.mode).toBe('thrifty');
  });
  it('only blocks teammate calls at lunch', () => {
    expect(teammatesAvailable(g('thrifty'))).toBe(true);
    expect(teammatesAvailable(g('lunch'))).toBe(false);
  });
  it('renders in the shell', () => {
    act(() => useStore.setState({ governor: g('lunch', new Date(2026, 9, 19, 5, 10).toISOString()) }));
    render(<GovernorBanner />);
    expect(screen.getByTestId('governor-banner')).toHaveTextContent('out to lunch until 5:10 AM');
    act(() => useStore.setState({ governor: g('normal') }));
  });
});
