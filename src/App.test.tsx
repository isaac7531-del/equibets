import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';

const liveFeed = {
  version: 1,
  source_id: 'data_fei',
  updated_at: '2026-06-17T13:00:00+00:00',
  window_start: '2026-06-16',
  window_end: '2026-06-18',
  event_count: 1,
  score_count: 2,
  events: [
    {
      event_name: 'Current Horse Trials',
      event_date: '2026-06-17',
      level: 'CCI3*-S',
      country: 'GBR',
      latest_collected_at: '2026-06-17T12:00:00+00:00',
      entry_count: 2,
      leader: {
        rank: 1,
        rider_name: 'Morgan Lee',
        horse_name: 'Copperfield',
        finishing_score: 28,
        dressage_score: 28,
        show_jumping_penalties: 0,
        cross_country_jump_penalties: 0,
        cross_country_time_penalties: 0,
        source_id: 'data_fei',
        source_record_id: 'fei-2',
        collected_at: '2026-06-17T12:00:00+00:00',
      },
      entries: [
        {
          rank: 1,
          rider_name: 'Morgan Lee',
          horse_name: 'Copperfield',
          finishing_score: 28,
          dressage_score: 28,
          show_jumping_penalties: 0,
          cross_country_jump_penalties: 0,
          cross_country_time_penalties: 0,
          source_id: 'data_fei',
          source_record_id: 'fei-2',
          collected_at: '2026-06-17T12:00:00+00:00',
        },
        {
          rank: 2,
          rider_name: 'Alex Rider',
          horse_name: 'Pocket Rocket',
          finishing_score: 35.8,
          dressage_score: 30.2,
          show_jumping_penalties: 4,
          cross_country_jump_penalties: 0,
          cross_country_time_penalties: 1.6,
          source_id: 'data_fei',
          source_record_id: 'fei-1',
          collected_at: '2026-06-17T12:00:00+00:00',
        },
      ],
    },
  ],
};

describe('App', () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        json: vi.fn(),
      }),
    );
  });

  const saveResult = async (
    user: ReturnType<typeof userEvent.setup>,
    result: {
      rider: string;
      horse: string;
      event: string;
      level: string;
      dressage: string;
      showJumping: string;
      xcJumping: string;
    },
  ) => {
    await user.type(screen.getByLabelText(/^rider$/i), result.rider);
    await user.type(screen.getByLabelText(/^horse$/i), result.horse);
    await user.type(screen.getByLabelText(/^event$/i), result.event);
    await user.selectOptions(screen.getByLabelText(/^level$/i), result.level);
    await user.clear(screen.getByLabelText(/dressage/i));
    await user.type(screen.getByLabelText(/dressage/i), result.dressage);
    await user.clear(screen.getByLabelText(/show jumping/i));
    await user.type(screen.getByLabelText(/show jumping/i), result.showJumping);
    await user.clear(screen.getByLabelText(/xc jumping/i));
    await user.type(screen.getByLabelText(/xc jumping/i), result.xcJumping);
    await user.click(screen.getByRole('button', { name: /save result/i }));
  };

  it('saves a calculated result to the results table', async () => {
    const user = userEvent.setup();
    render(<App />);

    await saveResult(user, {
      rider: 'Avery Stone',
      horse: 'Juniper',
      event: 'Spring Horse Trials',
      level: 'Training',
      dressage: '70',
      showJumping: '4',
      xcJumping: '0',
    });

    expect(screen.getByRole('cell', { name: '34.0' })).toBeInTheDocument();
    expect(screen.getAllByText('Juniper')).not.toHaveLength(0);
    expect(screen.getByText(/^Training ·/)).toBeInTheDocument();
    expect(JSON.parse(window.localStorage.getItem('equibets.results') ?? '[]')).toHaveLength(1);
  });

  it('filters the rider dropdown to show horses by level', async () => {
    const user = userEvent.setup();
    render(<App />);

    await saveResult(user, {
      rider: 'Avery Stone',
      horse: 'Juniper',
      event: 'Spring Horse Trials',
      level: 'Training',
      dressage: '70',
      showJumping: '4',
      xcJumping: '0',
    });
    await saveResult(user, {
      rider: 'Avery Stone',
      horse: 'Oakley',
      event: 'Summer Horse Trials',
      level: 'Novice',
      dressage: '72',
      showJumping: '0',
      xcJumping: '0',
    });
    await saveResult(user, {
      rider: 'Morgan Lee',
      horse: 'Copperfield',
      event: 'May Combined Test',
      level: 'Preliminary',
      dressage: '74',
      showJumping: '0',
      xcJumping: '0',
    });

    await user.selectOptions(screen.getByLabelText(/rider menu/i), 'Avery Stone');

    const browser = screen.getByRole('region', { name: /browse horses by rider/i });
    expect(browser).toHaveTextContent('Avery Stone');
    expect(browser).toHaveTextContent('Training');
    expect(browser).toHaveTextContent('Juniper');
    expect(browser).toHaveTextContent('Novice');
    expect(browser).toHaveTextContent('Oakley');
    expect(browser).not.toHaveTextContent('Copperfield');
    expect(screen.getAllByText('Oakley')).not.toHaveLength(0);
    expect(screen.queryByText('Copperfield')).not.toBeInTheDocument();
  });

  it('renders current-event live scoring from the public feed', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(liveFeed),
      }),
    );

    render(<App />);

    expect(await screen.findByText('Current Horse Trials')).toBeInTheDocument();
    expect(screen.getByText(/Pulling 2 FEI scores across 1 events/)).toBeInTheDocument();
    expect(screen.getByText(/Leader: Copperfield with Morgan Lee/)).toBeInTheDocument();
    expect(screen.getByText('35.8')).toBeInTheDocument();
  });
});
