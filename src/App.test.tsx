import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import App from './App';

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
    await user.type(screen.getByLabelText(/^rider$/i), result.rider);
    await user.type(screen.getByLabelText(/^horse$/i), result.horse);
    await user.type(screen.getByLabelText(/^event$/i), result.event);
    await user.selectOptions(screen.getByLabelText(/^level$/i), result.level);
    if (result.country) {
      await user.clear(screen.getByLabelText(/^country$/i));
      await user.type(screen.getByLabelText(/^country$/i), result.country);
    }
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
      country: 'USA',
      dressage: '70',
      showJumping: '4',
      xcJumping: '0',
    });

    expect(screen.getAllByRole('cell', { name: '34.0' }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Juniper').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/^Training - USA/)).toBeInTheDocument();
    expect(screen.getByRole('region', { name: /consolidated form guide/i })).not.toHaveTextContent('Juniper');
    expect(JSON.parse(window.localStorage.getItem('equibets.results') ?? '[]')).toHaveLength(1);
  });

  it('shows FEI results and prediction from FEI-only consolidated data', () => {
    render(<App />);

    expect(screen.getByRole('heading', { name: /likely finishing score/i })).toBeInTheDocument();
    expect(screen.getAllByText('Atlas Bay').length).toBeGreaterThan(0);
    expect(screen.getAllByText('FEI').length).toBeGreaterThan(0);
    expect(screen.getByText(/low confidence/i)).toBeInTheDocument();
    expect(screen.queryByText('British Eventing')).not.toBeInTheDocument();
    expect(screen.queryByText('USEA')).not.toBeInTheDocument();
  });

  it('searches FEI combinations by rider or horse and selects the match', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/search combinations by rider or horse/i), 'Sophie');

    const searchResults = screen.getByRole('region', { name: /combination search results/i });
    expect(searchResults).toHaveTextContent('Riverglass / Sophie Bell');
    expect(searchResults).not.toHaveTextContent('Atlas Bay / Mia Hughes');

    await user.click(within(searchResults).getByRole('button', { name: /Riverglass \/ Sophie Bell/i }));

    expect(screen.getByText(/Based on 1 recent consolidated starts for Riverglass and Sophie Bell/i)).toBeInTheDocument();
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
});
