import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';

describe('App', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('saves a calculated result to the results table', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/rider/i), 'Avery Stone');
    await user.type(screen.getByLabelText(/horse/i), 'Juniper');
    await user.type(screen.getByLabelText(/^event$/i), 'Spring Horse Trials');
    await user.clear(screen.getByLabelText(/dressage/i));
    await user.type(screen.getByLabelText(/dressage/i), '70');
    await user.clear(screen.getByLabelText(/show jumping/i));
    await user.type(screen.getByLabelText(/show jumping/i), '4');
    await user.clear(screen.getByLabelText(/xc jumping/i));
    await user.type(screen.getByLabelText(/xc jumping/i), '0');

    await user.click(screen.getByRole('button', { name: /save result/i }));

    expect(screen.getByRole('cell', { name: '34.0' })).toBeInTheDocument();
    expect(screen.getByText('Juniper')).toBeInTheDocument();
    expect(JSON.parse(window.localStorage.getItem('equibets.results') ?? '[]')).toHaveLength(1);
  });

  it('loads live current-event scores from the configured feed', async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => ({
          collectedAt: '2026-05-16T17:00:00Z',
          source: {
            id: 'data_fei',
            name: 'FEI Database',
          },
          results: [
            {
              id: 'fei-live-1',
              rider: 'Avery Stone',
              horse: 'Juniper',
              eventName: 'Current Spring Horse Trials',
              eventDate: '2026-05-16',
              level: 'CCI2*-S',
              country: 'USA',
              dressagePenalties: 29.2,
              showJumpingPenalties: 4,
              crossCountryJumpPenalties: 0,
              crossCountryTimePenalties: 0,
              status: 'provisional',
            },
          ],
        }),
      })),
    );

    render(<App />);
    await user.click(screen.getByRole('button', { name: /refresh live results/i }));

    expect(await screen.findByRole('cell', { name: '33.2' })).toBeInTheDocument();
    expect(screen.getByText('FEI Database')).toBeInTheDocument();
    expect(screen.getByText(/1 of 1 results/)).toBeInTheDocument();
  });
});
