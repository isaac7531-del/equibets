import { FormEvent, useEffect, useMemo, useState } from 'react';
import {
  calculateScore,
  formatSeconds,
  parseTimeToSeconds,
  sortByBestScore,
  type EventingScoreInput,
  type StoredResult,
} from './scoring';
import {
  EMPTY_LIVE_SCORING_FEED,
  fetchLiveScoringFeed,
  formatFeedUpdatedAt,
  type LiveScoringFeed,
} from './liveScoring';
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
  const [liveFeed, setLiveFeed] = useState<LiveScoringFeed>(EMPTY_LIVE_SCORING_FEED);
  const [liveFeedStatus, setLiveFeedStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const scoreInput = useMemo(() => createScoreInput(form), [form]);
  const currentScore = useMemo(() => calculateScore(scoreInput), [scoreInput]);
  const sortedResults = useMemo(() => sortByBestScore(results), [results]);
  const bestResult = sortedResults[0];
  const liveEvents = liveFeed.events.slice(0, 3);
  const feedStatusLabel =
    liveFeedStatus === 'loading'
      ? 'Searching'
      : liveFeedStatus === 'error'
        ? 'Unavailable'
        : `Updated ${formatFeedUpdatedAt(liveFeed.updated_at)}`;

  useEffect(() => {
    let isMounted = true;

    fetchLiveScoringFeed()
      .then((feed) => {
        if (!isMounted) {
          return;
        }
        setLiveFeed(feed);
        setLiveFeedStatus('ready');
      })
      .catch(() => {
        if (!isMounted) {
          return;
        }
        setLiveFeedStatus('error');
      });

    return () => {
      isMounted = false;
    };
  }, []);

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
        <article>
          <span>Live events</span>
          <strong>{liveFeed.summary.leaderboard_count}</strong>
          <p>{liveFeed.summary.result_count} current scores found</p>
        </article>
      </section>

      <section className="live-results-card" aria-labelledby="live-results-heading">
        <div className="results-header">
          <div>
            <p className="eyebrow">Public data</p>
            <h2 id="live-results-heading">Current event live scoring</h2>
          </div>
          <span className={`feed-status feed-status-${liveFeedStatus}`}>{feedStatusLabel}</span>
        </div>

        {liveFeedStatus === 'loading' ? (
          <div className="empty-state">
            <strong>Searching current events.</strong>
            <p>Checking the latest published FEI result updates for in-progress and recent competitions.</p>
          </div>
        ) : liveEvents.length === 0 ? (
          <div className="empty-state">
            <strong>{liveFeedStatus === 'error' ? 'Live feed unavailable.' : 'No current event scores yet.'}</strong>
            <p>
              {liveFeedStatus === 'error'
                ? 'The app will retry on the next page load after the refresh job publishes a feed.'
                : 'The hourly refresh has not found published scores in the current event window.'}
            </p>
          </div>
        ) : (
          <div className="live-event-list">
            {liveEvents.map((event) => (
              <article key={event.event_key} className="live-event">
                <div className="live-event-heading">
                  <div>
                    <h3>{event.event_name}</h3>
                    <p>
                      {event.event_date} / {event.level} / {event.country}
                    </p>
                  </div>
                  <span>{event.leader_count} starters</span>
                </div>
                <ol>
                  {event.leaders.slice(0, 5).map((leader) => (
                    <li key={leader.source_record_id}>
                      <span>#{leader.rank}</span>
                      <strong>{leader.horse_name}</strong>
                      <span>{leader.rider_name}</span>
                      <b>{leader.finishing_score.toFixed(1)}</b>
                    </li>
                  ))}
                </ol>
              </article>
            ))}
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
