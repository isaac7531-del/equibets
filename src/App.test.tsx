import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';

describe('App', () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.unstubAllGlobals();
  });

  it('saves a calculated result to the results table', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/rider/i), 'Avery Stone');
    await user.type(screen.getByLabelText(/horse/i), 'Juniper');
    await user.type(screen.getByLabelText(/event/i), 'Spring Horse Trials');
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

  it('renders published current-event live scores', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          generated_at: '2026-05-15T12:00:00+00:00',
          latest_collected_at: '2026-05-15T11:30:00+00:00',
          event_count: 1,
          result_count: 1,
          events: [
            {
              event_name: 'Current Horse Trials',
              event_date: '2026-05-15',
              level: 'CCI2',
              country: 'GBR',
              result_count: 1,
              results: [
                {
                  rank: 1,
                  rider_name: 'Alex Rider',
                  horse_name: 'Pocket Rocket',
                  total_penalties: 35.8,
                  dressage_score: 30.2,
                  show_jumping_penalties: 4,
                  cross_country_jump_penalties: 0,
                  cross_country_time_penalties: 1.6,
                },
              ],
            },
          ],
        }),
      }),
    );

    render(<App />);

    expect(await screen.findByText('Current Horse Trials')).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: '35.8' })).toBeInTheDocument();
    expect(screen.getByText('Pocket Rocket')).toBeInTheDocument();
  });
});
