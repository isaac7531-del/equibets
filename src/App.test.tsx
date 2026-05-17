import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import liveScoreFeedJson from '../data/live_event_scores.json';
import App from './App';
import { getLiveLeaderRows, sortLiveLeaderRows, type LiveScoreFeed } from './liveScoring';

const liveScoreFeed = liveScoreFeedJson as LiveScoreFeed;

describe('App', () => {
  beforeEach(() => {
    window.localStorage.clear();
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
    expect(screen.getAllByText('Juniper').length).toBeGreaterThan(0);
    expect(JSON.parse(window.localStorage.getItem('equibets.results') ?? '[]')).toHaveLength(1);
  });

  it('shows current event live scoring leaders', () => {
    render(<App />);

    const liveLeaderRows = sortLiveLeaderRows(getLiveLeaderRows(liveScoreFeed));

    expect(screen.getByRole('heading', { name: /live scoring/i })).toBeInTheDocument();
    expect(screen.getByText(liveScoreFeed.as_of_date, { exact: false })).toBeInTheDocument();
    expect(screen.getByText('StartBox current eventing scores', { exact: false })).toBeInTheDocument();
    if (liveLeaderRows.length === 0) {
      expect(screen.getByText(/no live leaders found/i)).toBeInTheDocument();
    } else {
      expect(screen.getAllByText(liveLeaderRows[0].event.name).length).toBeGreaterThan(0);
      expect(screen.getByText(liveLeaderRows[0].leader.horse)).toBeInTheDocument();
    }
  });
});
