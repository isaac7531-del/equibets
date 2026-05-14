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

  it('searches current-event results and pulls a live score into the calculator', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/search current-event results/i), 'Copper');
    expect(screen.getByText('Copper Chance')).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: '38.6' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /pull live score/i }));

    expect(screen.getByDisplayValue('Mara Ellison')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Copper Chance')).toBeInTheDocument();
    expect(screen.getByDisplayValue('68.2')).toBeInTheDocument();
    expect(screen.getAllByText('38.6').length).toBeGreaterThan(0);
  });
});
