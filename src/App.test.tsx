import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import App from './App';

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

    expect(screen.getAllByRole('cell', { name: '34.0' }).length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('Juniper')).toHaveLength(2);
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
});
