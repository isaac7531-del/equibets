import { FormEvent, useMemo, useState } from 'react';
import {
  calculateScore,
  formatSeconds,
  parseTimeToSeconds,
  sortByBestScore,
  type EventingScoreInput,
  type StoredResult,
} from './scoring';
import { currentEventFeed, searchCurrentEventResults, type CurrentEventScore } from './currentEvents';
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

const formatTenths = (value: number) => value.toFixed(1);

const secondsToTimeParts = (totalSeconds: number) => ({
  minutes: Math.floor(totalSeconds / 60).toString(),
  seconds: (totalSeconds % 60).toString(),
});

const scoreToCalculatorForm = (liveResult: CurrentEventScore): FormState => {
  const crossCountryTimeSeconds = Math.round((liveResult.crossCountryTimePenalties ?? 0) / 0.4);
  const actualTime = secondsToTimeParts(crossCountryTimeSeconds);

  return {
    rider: liveResult.riderName,
    horse: liveResult.horseName,
    eventName: liveResult.eventName,
    date: liveResult.eventDate,
    dressagePercentage:
      liveResult.dressageScore === null ? defaultFormState.dressagePercentage : formatTenths(100 - liveResult.dressageScore),
    showJumpingPenalties:
      liveResult.showJumpingPenalties === null ? '0' : formatTenths(liveResult.showJumpingPenalties),
    crossCountryJumpPenalties:
      liveResult.crossCountryJumpPenalties === null ? '0' : formatTenths(liveResult.crossCountryJumpPenalties),
    optimumMinutes: '0',
    optimumSeconds: '0',
    actualMinutes: actualTime.minutes,
    actualSeconds: actualTime.seconds,
    notes: `Pulled from ${liveResult.sourceId} current-event feed at ${liveResult.collectedAt}. ${liveResult.phaseLabel}.`,
  };
};

const formatCollectedAt = (value: string) =>
  new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));

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
  const [currentEventQuery, setCurrentEventQuery] = useState('');
  const scoreInput = useMemo(() => createScoreInput(form), [form]);
  const currentScore = useMemo(() => calculateScore(scoreInput), [scoreInput]);
  const sortedResults = useMemo(() => sortByBestScore(results), [results]);
  const liveScores = useMemo(() => searchCurrentEventResults(''), []);
  const currentEventMatches = useMemo(() => searchCurrentEventResults(currentEventQuery), [currentEventQuery]);
  const bestResult = sortedResults[0];
  const liveLeader = liveScores[0];

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

  const pullCurrentEventScore = (liveResult: CurrentEventScore) => {
    setForm(scoreToCalculatorForm(liveResult));
  };

  return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">Equibets</p>
          <h1>Eventing score calculator and results tracker</h1>
          <p className="hero-copy">
            Capture dressage, show jumping, and cross-country penalties in one place, search current-event feeds, and
            pull live scores into your local record.
          </p>
        </div>
        <div className="hero-card" aria-live="polite">
          <span>Live total</span>
          <strong>{formatTenths(currentScore.totalPenalties)}</strong>
          <p>penalties</p>
        </div>
      </section>

      <section className="dashboard" aria-label="Score summary">
        <article>
          <span>Dressage</span>
          <strong>{formatTenths(currentScore.dressagePenalties)}</strong>
          <p>100 minus percentage score</p>
        </article>
        <article>
          <span>Jumping</span>
          <strong>{formatTenths(currentScore.showJumpingPenalties + currentScore.crossCountryJumpPenalties)}</strong>
          <p>Stadium plus XC jumping penalties</p>
        </article>
        <article>
          <span>XC time</span>
          <strong>{formatTenths(currentScore.crossCountryTimePenalties)}</strong>
          <p>
            {formatSeconds(scoreInput.actualTimeSeconds)} against {formatSeconds(scoreInput.optimumTimeSeconds)}
          </p>
        </article>
        <article>
          <span>Best saved</span>
          <strong>{bestResult ? formatTenths(bestResult.score.totalPenalties) : '--'}</strong>
          <p>{bestResult ? `${bestResult.horse} at ${bestResult.eventName}` : 'Save a round to start tracking'}</p>
        </article>
        <article>
          <span>Current leader</span>
          <strong>{liveLeader ? formatTenths(liveLeader.score.totalPenalties) : '--'}</strong>
          <p>{liveLeader ? `${liveLeader.horseName}, ${liveLeader.phaseLabel}` : 'No current feed loaded'}</p>
        </article>
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

        <div className="results-stack">
          <section className="current-events-card results-card" aria-labelledby="current-events-heading">
            <div className="results-header">
              <div>
                <p className="eyebrow">Live scoring</p>
                <h2 id="current-events-heading">Current event feed</h2>
              </div>
              <span className="freshness-badge">Updated {formatCollectedAt(currentEventFeed.collectedAt)}</span>
            </div>

            <p className="feed-summary">{currentEventFeed.sourceSummary}</p>

            <label className="search-field">
              Search current-event results
              <input
                value={currentEventQuery}
                onChange={(event) => setCurrentEventQuery(event.target.value)}
                placeholder="Horse, rider, event, country, source"
              />
            </label>

            {currentEventMatches.length === 0 ? (
              <div className="empty-state">
                <strong>No current results found.</strong>
                <p>Try another horse, rider, event, country, level, or source.</p>
              </div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Combination</th>
                      <th>Event</th>
                      <th>Live total</th>
                      <th>Phase</th>
                      <th aria-label="Actions" />
                    </tr>
                  </thead>
                  <tbody>
                    {currentEventMatches.map((liveResult) => (
                      <tr key={liveResult.id}>
                        <td>
                          <strong>{liveResult.horseName}</strong>
                          <span>{liveResult.riderName}</span>
                        </td>
                        <td>
                          <strong>{liveResult.eventName}</strong>
                          <span>
                            {liveResult.level} / {liveResult.country} / {liveResult.sourceId}
                          </span>
                        </td>
                        <td className="total-cell">{formatTenths(liveResult.score.totalPenalties)}</td>
                        <td>
                          <strong>{liveResult.phaseLabel}</strong>
                          <span>{formatCollectedAt(liveResult.collectedAt)}</span>
                        </td>
                        <td>
                          <button className="link-button" type="button" onClick={() => pullCurrentEventScore(liveResult)}>
                            Pull live score
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

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
        </div>
      </section>
    </main>
  );
}
