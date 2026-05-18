import { render, screen } from '@testing-library/react';
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

  it('shows the live public scoring empty state before public data is refreshed', () => {
    render(<App />);

    expect(screen.getByRole('heading', { name: /live public scoring/i })).toBeInTheDocument();
    expect(screen.getByText(/no live public results in the current window/i)).toBeInTheDocument();
  });
});
