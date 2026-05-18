import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';

describe('App', () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.stubGlobal('fetch', vi.fn(async () => new Response('', { status: 404 })));
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

  it('shows live public current-event scores when generated data is available', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              version: 1,
              generated_at: '2026-05-18T13:00:00+00:00',
              window: {
                start_date: '2026-05-11',
                end_date: '2026-05-19',
              },
              latest_collected_at: '2026-05-18T12:00:00+00:00',
              result_count: 1,
              scores: [
                {
                  source_id: 'data_fei',
                  source_record_id: 'fei-1',
                  rider_name: 'Alex Rider',
                  horse_name: 'Pocket Rocket',
                  event_name: 'Spring Horse Trials',
                  event_date: '2026-05-18',
                  level: 'CCI2',
                  country: 'GBR',
                  dressage_score: 30.2,
                  show_jumping_penalties: 4,
                  cross_country_jump_penalties: 0,
                  cross_country_time_penalties: 1.6,
                  finishing_score: 35.8,
                  collected_at: '2026-05-18T12:00:00+00:00',
                },
              ],
            }),
            { status: 200 },
          ),
      ),
    );

    render(<App />);

    expect(await screen.findByRole('cell', { name: '35.8' })).toBeInTheDocument();
    expect(screen.getByText('Pocket Rocket')).toBeInTheDocument();
    expect(screen.getByText(/showing 1 scores/i)).toBeInTheDocument();
  });
});
