import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import App from './App';
import liveScoresData from './data/live_scores.json';
import { formatLiveEventTitle, type LiveScorePayload } from './liveScores';

const liveScores = liveScoresData as LiveScorePayload;

describe('App', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  const saveResult = async (
    user: ReturnType<typeof userEvent.setup>,
    result: {
      rider: string;
      horse: string;
      event: string;
      level: string;
      country?: string;
      dressage: string;
      showJumping: string;
      xcJumping: string;
    },
  ) => {
    const calculatorForm = screen.getByLabelText(/^event$/i).closest('form');
    if (!calculatorForm) {
      throw new Error('Calculator form not found');
    }
    const calculator = within(calculatorForm);

    await user.type(calculator.getByLabelText(/^rider$/i), result.rider);
    await user.type(calculator.getByLabelText(/^horse$/i), result.horse);
    await user.type(calculator.getByLabelText(/^event$/i), result.event);
    await user.selectOptions(calculator.getByLabelText(/^level$/i), result.level);
    if (result.country) {
      const resultCountryInput = calculator.getByLabelText(/^country$/i);
      await user.clear(resultCountryInput);
      await user.type(resultCountryInput, result.country);
    }
    await user.clear(calculator.getByLabelText(/dressage/i));
    await user.type(calculator.getByLabelText(/dressage/i), result.dressage);
    await user.clear(calculator.getByLabelText(/show jumping/i));
    await user.type(calculator.getByLabelText(/show jumping/i), result.showJumping);
    await user.clear(calculator.getByLabelText(/xc jumping/i));
    await user.type(calculator.getByLabelText(/xc jumping/i), result.xcJumping);
    await user.click(calculator.getByRole('button', { name: /save result/i }));
  };

  it('saves a calculated result to the results table', async () => {
    const user = userEvent.setup();
    render(<App />);

    await saveResult(user, {
      rider: 'Avery Stone',
      horse: 'Juniper',
      event: 'Spring Horse Trials',
      level: 'Training',
      country: 'USA',
      dressage: '70',
      showJumping: '4',
      xcJumping: '0',
    });

    expect(screen.getAllByRole('cell', { name: '34.0' }).length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('Juniper').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/^Training - USA/)).toBeInTheDocument();
    expect(screen.getByText('My score')).toBeInTheDocument();
    expect(JSON.parse(window.localStorage.getItem('equibets.results') ?? '[]')).toHaveLength(1);
  });

  it('shows public results and prediction from consolidated data', () => {
    render(<App />);

    expect(screen.getByRole('heading', { name: /likely finishing score/i })).toBeInTheDocument();
    expect(screen.getAllByText('Atlas Bay').length).toBeGreaterThan(0);
    expect(screen.getAllByText('FEI').length).toBeGreaterThan(0);
    expect(screen.getByText(/medium confidence/i)).toBeInTheDocument();
  });

  it('shows the free-play prediction market roadmap without gambling flows', () => {
    render(<App />);

    expect(screen.getByRole('heading', { name: /prediction markets roadmap/i })).toBeInTheDocument();
    expect(screen.getByText('Win market')).toBeInTheDocument();
    expect(screen.getByText('Head-to-head matchups')).toBeInTheDocument();
    expect(screen.getByText(/No deposits, withdrawals, stakes, or paid betting odds/i)).toBeInTheDocument();
  });

  it('shows both web dashboard and installable app formats', () => {
    render(<App />);

    expect(screen.getByRole('heading', { name: /built for browser use and installable app workflows/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3, name: /web dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3, name: /installable app/i })).toBeInTheDocument();
    expect(screen.getByText(/manifest, app icon, standalone display mode/i)).toBeInTheDocument();
  });

  it('shows the worldwide upcoming event feed', () => {
    render(<App />);

    const upcomingFeed = screen.getByRole('region', { name: /upcoming event feed/i });
    expect(upcomingFeed).toHaveTextContent('Badminton Horse Trials');
    expect(upcomingFeed).toHaveTextContent('CHIO Aachen');
    expect(upcomingFeed).toHaveTextContent('Daily FEI refresh ready');
    expect(within(upcomingFeed).getAllByText('FEI').length).toBeGreaterThan(0);
  });

  it('saves horse profile data to the horse profile table', async () => {
    const user = userEvent.setup();
    render(<App />);
    const horseData = screen.getByRole('region', { name: /add horse profile data/i });

    await user.type(within(horseData).getByLabelText(/^horse name$/i), 'Pocket Rocket');
    await user.type(within(horseData).getByLabelText(/^registered name$/i), 'Pocket Rocket II');
    await user.type(within(horseData).getByLabelText(/^fei id$/i), '107bh10');
    await user.clear(within(horseData).getByLabelText(/^country$/i));
    await user.type(within(horseData).getByLabelText(/^country$/i), 'gbr');
    await user.type(within(horseData).getByLabelText(/^sex$/i), 'Gelding');
    await user.type(within(horseData).getByLabelText(/^birth year$/i), '2014');
    await user.type(within(horseData).getByLabelText(/^owner$/i), 'Stone Eventing');
    await user.click(within(horseData).getByRole('button', { name: /save horse profile/i }));

    expect(horseData).toHaveTextContent('Pocket Rocket');
    expect(horseData).toHaveTextContent('107BH10');
    expect(horseData).toHaveTextContent('Gelding / 2014');
    expect(JSON.parse(window.localStorage.getItem('equibets.horseProfiles') ?? '[]')).toHaveLength(1);
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
    const savedResults = screen.getByRole('region', { name: /saved results/i });
    expect(within(savedResults).getAllByText('Oakley').length).toBeGreaterThan(0);
    expect(within(savedResults).queryByText('Copperfield')).not.toBeInTheDocument();
  });

  it('shows the current live public scoring feed', () => {
    render(<App />);

    expect(screen.getByRole('heading', { name: /live public scoring/i })).toBeInTheDocument();
    if (liveScores.result_count === 0) {
      expect(screen.getByText(/no live public results in the current window/i)).toBeInTheDocument();
      return;
    }

    const liveFeed = screen.getByRole('region', { name: /live public scoring/i });
    const firstEvent = liveScores.events[0];
    const leader = firstEvent.standings[0];
    expect(screen.getByText(liveScores.result_count.toString())).toBeInTheDocument();
    liveScores.events.forEach((event) => {
      expect(screen.getByRole('heading', { name: formatLiveEventTitle(event) })).toBeInTheDocument();
    });
    expect(screen.getAllByText(leader.horse_name).length).toBeGreaterThan(0);
    if (firstEvent.result_count > 8) {
      expect(liveFeed).toHaveTextContent(`Showing top 8 of ${firstEvent.result_count} public results.`);
      expect(within(liveFeed).queryByText(firstEvent.standings[8].horse_name)).not.toBeInTheDocument();
    }
  });
});
