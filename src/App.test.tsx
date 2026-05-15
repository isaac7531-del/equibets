import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';

const currentEventsPayload = {
  version: 1,
  generatedAt: '2026-05-15T19:00:00.000Z',
  results: [
    {
      id: 'live-1',
      rider: 'Mira Bennett',
      horse: 'Willow Run',
      eventName: 'River Run CCI3*',
      date: '2026-05-15',
      level: 'CCI3-S',
      country: 'USA',
      dressagePercentage: 71.2,
      showJumpingPenalties: 0,
      crossCountryJumpPenalties: 0,
      optimumTimeSeconds: 342,
      actualTimeSeconds: 348,
      sourceId: 'equibets_current_events',
      sourceName: 'Equibets current events feed',
      status: 'provisional',
      phase: 'cross_country',
      collectedAt: '2026-05-15T18:55:00.000Z',
    },
    {
      id: 'live-2',
      rider: 'Avery Stone',
      horse: 'Juniper',
      eventName: 'River Run CCI3*',
      date: '2026-05-15',
      level: 'CCI3-S',
      country: 'USA',
      dressagePercentage: 69.8,
      showJumpingPenalties: 4,
      crossCountryJumpPenalties: 0,
      optimumTimeSeconds: 342,
      actualTimeSeconds: 342,
      sourceId: 'equibets_current_events',
      sourceName: 'Equibets current events feed',
      status: 'in_progress',
      phase: 'show_jumping',
      collectedAt: '2026-05-15T18:48:00.000Z',
    },
  ],
};

describe('App', () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => currentEventsPayload,
      })),
    );
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
    expect(screen.getAllByText('Juniper').length).toBeGreaterThan(0);
    expect(JSON.parse(window.localStorage.getItem('equibets.results') ?? '[]')).toHaveLength(1);
  });

  it('searches current events and pulls a live score into saved results', async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findAllByText('River Run CCI3*')).toHaveLength(2);

    await user.type(screen.getByLabelText(/search current events/i), 'willow');
    expect(screen.getByText('Willow Run')).toBeInTheDocument();
    expect(screen.queryByText('Juniper')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /pull score for willow run/i }));

    expect(JSON.parse(window.localStorage.getItem('equibets.results') ?? '[]')[0]).toMatchObject({
      horse: 'Willow Run',
      sourceId: 'equibets_current_events',
      sourceRecordId: 'live-1',
      score: { totalPenalties: 31.2 },
    });
    expect(screen.getByText('Update saved')).toBeInTheDocument();
  });
});
