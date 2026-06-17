import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';

describe('App', () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('', { status: 404 })),
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

  it('loads current events and prefills the live scoring form', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            updated_at: '2026-06-17T00:00:00+00:00',
            window_start: '2026-06-17',
            window_end: '2026-06-24',
            events: [
              {
                source_event_id: 'aachen-2026',
                name: 'Aachen CCIO4*-S',
                url: 'https://data.fei.org/Calendar/EventDetail.aspx?event=aachen',
                start_date: '2026-06-17',
                end_date: '2026-06-20',
                country: 'GER',
                discipline: 'Eventing',
                level: 'CCIO4*-S',
              },
            ],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      ),
    );
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole('heading', { name: 'Aachen CCIO4*-S' });
    await user.click(screen.getByRole('button', { name: /score this event/i }));

    expect(screen.getByLabelText(/^event$/i)).toHaveValue('Aachen CCIO4*-S');
    expect(screen.getByLabelText(/^level$/i)).toHaveValue('CCIO4*-S');
    expect(screen.getByLabelText(/^date$/i)).toHaveValue('2026-06-17');
    expect(screen.getByText(/Live now|Upcoming|Recently finished/)).toBeInTheDocument();
  });
});
