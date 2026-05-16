import { FormEvent, useMemo, useState } from 'react';
import {
  calculateScore,
  formatSeconds,
  parseTimeToSeconds,
  sortByBestScore,
  type EventingScoreInput,
  type StoredResult,
} from './scoring';
import { buildCurrentEventSearches, pullLiveResultsFromUrl, type LiveResult } from './liveResults';
import { loadResults, saveResults } from './storage';

type FormState = {
  rider: string;
  horse: string;
  eventName: string;
  date: string;
  dressagePercentage: string;
  showJumpingPenalties: string;
  crossCountryJumpPenalties: string;
  optimumMinutes: string;
  optimumSeconds: string;
  actualMinutes: string;
  actualSeconds: string;
  notes: string;
};

const defaultFormState: FormState = {
  rider: '',
  horse: '',
  eventName: '',
  date: new Date().toISOString().slice(0, 10),
  dressagePercentage: '68.5',
  showJumpingPenalties: '0',
  crossCountryJumpPenalties: '0',
  optimumMinutes: '5',
  optimumSeconds: '30',
  actualMinutes: '5',
  actualSeconds: '30',
  notes: '',
};

const numberValue = (value: string) => Number.parseFloat(value || '0');

const createScoreInput = (form: FormState): EventingScoreInput => ({
  dressagePercentage: numberValue(form.dressagePercentage),
  showJumpingPenalties: numberValue(form.showJumpingPenalties),
  crossCountryJumpPenalties: numberValue(form.crossCountryJumpPenalties),
  optimumTimeSeconds: parseTimeToSeconds(numberValue(form.optimumMinutes), numberValue(form.optimumSeconds)),
  actualTimeSeconds: parseTimeToSeconds(numberValue(form.actualMinutes), numberValue(form.actualSeconds)),
});

export default function App() {
  const [form, setForm] = useState<FormState>(defaultFormState);
  const [results, setResults] = useState<StoredResult[]>(() => loadResults());
  const [liveRegion, setLiveRegion] = useState('global');
  const [liveFeedUrl, setLiveFeedUrl] = useState('');
  const [liveResults, setLiveResults] = useState<LiveResult[]>([]);
  const [liveStatus, setLiveStatus] = useState('Search official sources, then pull a JSON results feed to score live standings.');
  const [isPullingLiveResults, setIsPullingLiveResults] = useState(false);
  const scoreInput = useMemo(() => createScoreInput(form), [form]);
  const currentScore = useMemo(() => calculateScore(scoreInput), [scoreInput]);
  const sortedResults = useMemo(() => sortByBestScore(results), [results]);
  const currentEventSearches = useMemo(
    () =>
      buildCurrentEventSearches({
        eventName: form.eventName,
        rider: form.rider,
        horse: form.horse,
        region: liveRegion,
      }),
    [form.eventName, form.horse, form.rider, liveRegion],
  );
  const bestResult = sortedResults[0];

  const updateField = (field: keyof FormState, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const newResult: StoredResult = {
      ...scoreInput,
      id: crypto.randomUUID(),
      rider: form.rider.trim(),
      horse: form.horse.trim(),
      eventName: form.eventName.trim(),
      date: form.date,
      notes: form.notes.trim(),
      createdAt: new Date().toISOString(),
      score: currentScore,
    };

    const nextResults = [newResult, ...results];
    setResults(nextResults);
    saveResults(nextResults);
    setForm(defaultFormState);
  };

  const removeResult = (id: string) => {
    const nextResults = results.filter((result) => result.id !== id);
    setResults(nextResults);
    saveResults(nextResults);
  };

  const clearResults = () => {
    setResults([]);
    saveResults([]);
  };

  const handlePullLiveResults = async () => {
    const trimmedUrl = liveFeedUrl.trim();
    if (!trimmedUrl) {
      setLiveStatus('Add a JSON feed URL before pulling live results.');
      return;
    }

    setIsPullingLiveResults(true);
    setLiveStatus('Pulling latest public result records...');

    try {
      const pulledResults = await pullLiveResultsFromUrl(trimmedUrl);
      setLiveResults(pulledResults);
      setLiveStatus(
        pulledResults.length === 0
          ? 'The feed loaded, but it did not include any result records.'
          : `Pulled ${pulledResults.length} live score${pulledResults.length === 1 ? '' : 's'}.`,
      );
    } catch (error) {
      setLiveStatus(error instanceof Error ? error.message : 'Unable to pull live results.');
    } finally {
      setIsPullingLiveResults(false);
    }
  };

  const saveLiveResult = (liveResult: LiveResult) => {
    const savedResult: StoredResult = {
      ...liveResult,
      id: crypto.randomUUID(),
      createdAt: new Date().toISOString(),
      notes: `${liveResult.notes}${liveResult.sourceUrl ? ` (${liveResult.sourceUrl})` : ''}`,
    };
    const nextResults = [savedResult, ...results];
    setResults(nextResults);
    saveResults(nextResults);
  };

  return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">Equibets</p>
          <h1>Eventing score calculator and results tracker</h1>
          <p className="hero-copy">
            Capture dressage, show jumping, and cross-country penalties in one place, then keep a local record of
            horse-and-rider results.
          </p>
        </div>
        <div className="hero-card" aria-live="polite">
          <span>Live total</span>
          <strong>{currentScore.totalPenalties.toFixed(1)}</strong>
          <p>penalties</p>
        </div>
      </section>

      <section className="dashboard" aria-label="Score summary">
        <article>
          <span>Dressage</span>
          <strong>{currentScore.dressagePenalties.toFixed(1)}</strong>
          <p>100 minus percentage score</p>
        </article>
        <article>
          <span>Jumping</span>
          <strong>{(currentScore.showJumpingPenalties + currentScore.crossCountryJumpPenalties).toFixed(1)}</strong>
          <p>Stadium plus XC jumping penalties</p>
        </article>
        <article>
          <span>XC time</span>
          <strong>{currentScore.crossCountryTimePenalties.toFixed(1)}</strong>
          <p>
            {formatSeconds(scoreInput.actualTimeSeconds)} against {formatSeconds(scoreInput.optimumTimeSeconds)}
          </p>
        </article>
        <article>
          <span>Best saved</span>
          <strong>{bestResult ? bestResult.score.totalPenalties.toFixed(1) : '--'}</strong>
          <p>{bestResult ? `${bestResult.horse} at ${bestResult.eventName}` : 'Save a round to start tracking'}</p>
        </article>
      </section>

      <section className="live-card" aria-labelledby="live-results-heading">
        <div className="results-header">
          <div>
            <p className="eyebrow">Current events</p>
            <h2 id="live-results-heading">Live result search and scoring</h2>
          </div>
          <span className="status-pill">{liveResults.length} pulled</span>
        </div>

        <div className="live-controls">
          <label>
            Region
            <select value={liveRegion} onChange={(event) => setLiveRegion(event.target.value)}>
              <option value="global">Global</option>
              <option value="europe">Europe</option>
              <option value="uk">UK</option>
              <option value="australia">Australia</option>
              <option value="new_zealand">New Zealand</option>
              <option value="usa">USA</option>
            </select>
          </label>
          <label>
            Results feed URL
            <input
              type="url"
              value={liveFeedUrl}
              onChange={(event) => setLiveFeedUrl(event.target.value)}
              placeholder="https://example.com/current-event-results.json"
            />
          </label>
          <button type="button" onClick={handlePullLiveResults} disabled={isPullingLiveResults}>
            {isPullingLiveResults ? 'Pulling...' : 'Pull latest scores'}
          </button>
        </div>

        <p className="live-status" role="status">
          {liveStatus}
        </p>

        <div className="source-search-grid" aria-label="Official result searches">
          {currentEventSearches.map((search) => (
            <a key={search.sourceId} href={search.searchUrl} target="_blank" rel="noreferrer">
              <strong>{search.sourceName}</strong>
              <span>{search.query}</span>
            </a>
          ))}
        </div>

        {liveResults.length > 0 && (
          <div className="table-wrap live-table">
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Combination</th>
                  <th>Event</th>
                  <th>Source</th>
                  <th>Total</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {liveResults.map((result, index) => (
                  <tr key={result.id}>
                    <td>#{index + 1}</td>
                    <td>
                      <strong>{result.horse}</strong>
                      <span>{result.rider}</span>
                    </td>
                    <td>
                      <strong>{result.eventName}</strong>
                      <span>
                        {[result.date, result.level, result.country].filter(Boolean).join(' / ')}
                      </span>
                    </td>
                    <td>
                      <strong>{result.sourceName}</strong>
                      <span>Collected {new Date(result.collectedAt).toLocaleDateString()}</span>
                    </td>
                    <td className="total-cell">{result.score.totalPenalties.toFixed(1)}</td>
                    <td>
                      <button className="link-button" type="button" onClick={() => saveLiveResult(result)}>
                        Save
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="workspace-grid">
        <form className="calculator-card" onSubmit={handleSubmit}>
          <div className="section-heading">
            <p className="eyebrow">Calculator</p>
            <h2>Add a result</h2>
          </div>

          <div className="form-grid">
            <label>
              Rider
              <input
                required
                value={form.rider}
                onChange={(event) => updateField('rider', event.target.value)}
                placeholder="Rider name"
              />
            </label>
            <label>
              Horse
              <input
                required
                value={form.horse}
                onChange={(event) => updateField('horse', event.target.value)}
                placeholder="Horse name"
              />
            </label>
            <label>
              Event
              <input
                required
                value={form.eventName}
                onChange={(event) => updateField('eventName', event.target.value)}
                placeholder="e.g. Rocking Horse HT"
              />
            </label>
            <label>
              Date
              <input type="date" required value={form.date} onChange={(event) => updateField('date', event.target.value)} />
            </label>
          </div>

          <div className="score-panel">
            <h3>Penalty inputs</h3>
            <div className="form-grid">
              <label>
                Dressage %
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={form.dressagePercentage}
                  onChange={(event) => updateField('dressagePercentage', event.target.value)}
                />
              </label>
              <label>
                Show jumping
                <input
                  type="number"
                  min="0"
                  step="0.1"
                  value={form.showJumpingPenalties}
                  onChange={(event) => updateField('showJumpingPenalties', event.target.value)}
                />
              </label>
              <label>
                XC jumping
                <input
                  type="number"
                  min="0"
                  step="0.1"
                  value={form.crossCountryJumpPenalties}
                  onChange={(event) => updateField('crossCountryJumpPenalties', event.target.value)}
                />
              </label>
            </div>
          </div>

          <div className="time-grid">
            <fieldset>
              <legend>Optimum time</legend>
              <label>
                Min
                <input
                  type="number"
                  min="0"
                  value={form.optimumMinutes}
                  onChange={(event) => updateField('optimumMinutes', event.target.value)}
                />
              </label>
              <label>
                Sec
                <input
                  type="number"
                  min="0"
                  max="59"
                  value={form.optimumSeconds}
                  onChange={(event) => updateField('optimumSeconds', event.target.value)}
                />
              </label>
            </fieldset>
            <fieldset>
              <legend>Actual time</legend>
              <label>
                Min
                <input
                  type="number"
                  min="0"
                  value={form.actualMinutes}
                  onChange={(event) => updateField('actualMinutes', event.target.value)}
                />
              </label>
              <label>
                Sec
                <input
                  type="number"
                  min="0"
                  max="59"
                  value={form.actualSeconds}
                  onChange={(event) => updateField('actualSeconds', event.target.value)}
                />
              </label>
            </fieldset>
          </div>

          <label>
            Notes
            <textarea
              value={form.notes}
              onChange={(event) => updateField('notes', event.target.value)}
              placeholder="Add conditions, division, or reminders"
            />
          </label>

          <button type="submit">Save result</button>
        </form>

        <section className="results-card" aria-labelledby="saved-results-heading">
          <div className="results-header">
            <div>
              <p className="eyebrow">Data storage</p>
              <h2 id="saved-results-heading">Saved results</h2>
            </div>
            <button className="secondary-button" type="button" onClick={clearResults} disabled={results.length === 0}>
              Clear all
            </button>
          </div>

          {sortedResults.length === 0 ? (
            <div className="empty-state">
              <strong>No saved results yet.</strong>
              <p>Complete the calculator to build a local score history for each horse and rider.</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Combination</th>
                    <th>Event</th>
                    <th>Total</th>
                    <th>Breakdown</th>
                    <th aria-label="Actions" />
                  </tr>
                </thead>
                <tbody>
                  {sortedResults.map((result, index) => (
                    <tr key={result.id}>
                      <td>#{index + 1}</td>
                      <td>
                        <strong>{result.horse}</strong>
                        <span>{result.rider}</span>
                      </td>
                      <td>
                        <strong>{result.eventName}</strong>
                        <span>{result.date}</span>
                      </td>
                      <td className="total-cell">{result.score.totalPenalties.toFixed(1)}</td>
                      <td className="breakdown-cell">
                        D {result.score.dressagePenalties.toFixed(1)} / SJ{' '}
                        {result.score.showJumpingPenalties.toFixed(1)} / XC{' '}
                        {(result.score.crossCountryJumpPenalties + result.score.crossCountryTimePenalties).toFixed(1)}
                      </td>
                      <td>
                        <button className="link-button" type="button" onClick={() => removeResult(result.id)}>
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}
