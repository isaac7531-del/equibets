import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';

describe('App', () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          generated_at: '2026-05-16T19:00:00+00:00',
          source_ids: [],
          results: [],
        }),
      })),
    );
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

  it('loads current-event live scoring rows', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          generated_at: '2026-05-16T19:00:00+00:00',
          source_ids: ['data_fei'],
          results: [
            {
              source_id: 'data_fei',
              source_record_id: 'fei-live-1',
              source_priority: 0,
              rider_name: 'Avery Stone',
              horse_name: 'Juniper',
              event_name: 'Current Spring International',
              event_date: '2026-05-16',
              level: 'CCI3',
              country: 'GBR',
              dressage_score: 29.4,
              show_jumping_penalties: 4,
              phase_statuses: {
                dressage: 'complete',
                show_jumping: 'complete',
                cross_country: 'not_started',
              },
              collected_at: '2026-05-16T19:00:00+00:00',
              status: 'live',
            },
          ],
        }),
      })),
    );

    render(<App />);

    expect(await screen.findByText('Current Spring International')).toBeInTheDocument();
    expect(screen.getAllByText('33.4')[0]).toBeInTheDocument();
  });
});
