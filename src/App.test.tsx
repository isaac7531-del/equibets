import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';

describe('App', () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          events: [],
          summary: {
            result_count: 0,
            leaderboard_count: 0,
          },
        }),
      }),
    );
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

  it('shows live current-event scores from the public feed', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          updated_at: '2026-05-18T20:03:00+00:00',
          date_window: {
            start_date: '2026-05-14',
            end_date: '2026-05-19',
          },
          source_ids: ['data_fei'],
          summary: {
            result_count: 1,
            leaderboard_count: 1,
          },
          events: [
            {
              event_key: 'spring-international',
              event_name: 'Spring International',
              event_date: '2026-05-18',
              level: 'CCI2',
              country: 'GBR',
              leader_count: 1,
              leaders: [
                {
                  rank: 1,
                  rider_name: 'Blair Smith',
                  horse_name: 'Juniper',
                  finishing_score: 29,
                  dressage_score: 29,
                  show_jumping_penalties: 0,
                  cross_country_jump_penalties: 0,
                  cross_country_time_penalties: 0,
                  source_id: 'data_fei',
                  source_record_id: 'fei-1',
                  collected_at: '2026-05-18T20:03:00+00:00',
                },
              ],
            },
          ],
        }),
      }),
    );

    render(<App />);

    expect(await screen.findByText('Spring International')).toBeInTheDocument();
    expect(screen.getByText('Juniper')).toBeInTheDocument();
    expect(screen.getByText('29.0')).toBeInTheDocument();
    expect(screen.getByText('Updated 2026-05-18 20:03 UTC')).toBeInTheDocument();
  });
});
