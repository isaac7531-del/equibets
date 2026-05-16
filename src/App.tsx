import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import {
  completedPhaseCount,
  formatLiveStatus,
  liveTotal,
  loadLiveScoreFeed,
  searchLiveScores,
  type LiveScoreFeed,
} from './liveScoring';
import {
  calculateScore,
  formatSeconds,
  parseTimeToSeconds,
  sortByBestScore,
  type EventingScoreInput,
  type StoredResult,
} from './scoring';
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

const emptyLiveFeed: LiveScoreFeed = {
  generatedAt: null,
  sourceIds: [],
  scores: [],
};

const liveFeedUrls = ['/current-events.json', import.meta.env.VITE_LIVE_RESULTS_URL].filter(
  (url): url is string => typeof url === 'string' && url.length > 0,
);
const liveRefreshIntervalMs = 60_000;

const numberValue = (value: string) => Number.parseFloat(value || '0');

const createScoreInput = (form: FormState): EventingScoreInput => ({
  dressagePercentage: numberValue(form.dressagePercentage),
  showJumpingPenalties: numberValue(form.showJumpingPenalties),
  crossCountryJumpPenalties: numberValue(form.crossCountryJumpPenalties),
  optimumTimeSeconds: parseTimeToSeconds(numberValue(form.optimumMinutes), numberValue(form.optimumSeconds)),
  actualTimeSeconds: parseTimeToSeconds(numberValue(form.actualMinutes), numberValue(form.actualSeconds)),
});

const formatFeedTime = (value: string | null) => {
  if (!value) {
    return 'No live refresh yet';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
};

const formatFeedStatus = (status: 'loading' | 'ready' | 'error') => {
  if (status === 'loading') {
    return 'Refreshing';
  }
  if (status === 'error') {
    return 'Feed error';
  }
  return 'Feed ready';
};

export default function App() {
  const [form, setForm] = useState<FormState>(defaultFormState);
  const [results, setResults] = useState<StoredResult[]>(() => loadResults());
  const [liveFeed, setLiveFeed] = useState<LiveScoreFeed>(emptyLiveFeed);
  const [liveSearch, setLiveSearch] = useState('');
  const [liveFeedStatus, setLiveFeedStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const scoreInput = useMemo(() => createScoreInput(form), [form]);
  const currentScore = useMemo(() => calculateScore(scoreInput), [scoreInput]);
  const sortedResults = useMemo(() => sortByBestScore(results), [results]);
  const bestResult = sortedResults[0];
  const searchedLiveScores = useMemo(() => searchLiveScores(liveFeed.scores, liveSearch, 8), [liveFeed.scores, liveSearch]);
  const bestLiveScore = searchedLiveScores[0];

  const refreshLiveScores = useCallback(async () => {
    setLiveFeedStatus('loading');
    try {
      const nextFeed = await loadLiveScoreFeed(liveFeedUrls);
      setLiveFeed(nextFeed);
      setLiveFeedStatus('ready');
    } catch {
      setLiveFeedStatus('error');
    }
  }, []);

  useEffect(() => {
    let isActive = true;

    const refresh = async () => {
      if (!isActive) {
        return;
      }
      await refreshLiveScores();
    };

    refresh();
    const intervalId = window.setInterval(refresh, liveRefreshIntervalMs);

    return () => {
      isActive = false;
      window.clearInterval(intervalId);
    };
  }, [refreshLiveScores]);

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
          <span>Live leader</span>
          <strong>{bestLiveScore ? liveTotal(bestLiveScore).toFixed(1) : '--'}</strong>
          <p>{bestLiveScore ? `${bestLiveScore.horseName} at ${bestLiveScore.eventName}` : 'Awaiting current-event feed'}</p>
        </article>
      </section>

      <section className="live-card" aria-labelledby="live-scoring-heading">
        <div className="results-header">
          <div>
            <p className="eyebrow">Current events</p>
            <h2 id="live-scoring-heading">Live scoring</h2>
          </div>
          <button className="secondary-button" type="button" onClick={refreshLiveScores} disabled={liveFeedStatus === 'loading'}>
            {liveFeedStatus === 'loading' ? 'Refreshing...' : 'Refresh feed'}
          </button>
        </div>

        <div className="live-toolbar">
          <label>
            Search live leaderboard
            <input
              value={liveSearch}
              onChange={(event) => setLiveSearch(event.target.value)}
              placeholder="Horse, rider, event, level, country, or source"
            />
          </label>
          <div className="feed-meta" aria-live="polite">
            <span className={`status-pill status-pill--${liveFeedStatus}`}>{formatFeedStatus(liveFeedStatus)}</span>
            <span>{formatFeedTime(liveFeed.generatedAt)}</span>
            <span>{liveFeed.sourceIds.length} source{liveFeed.sourceIds.length === 1 ? '' : 's'}</span>
          </div>
        </div>

        {searchedLiveScores.length === 0 ? (
          <div className="empty-state">
            <strong>No live scores loaded.</strong>
            <p>Publish a normalized current-event feed at /current-events.json or set VITE_LIVE_RESULTS_URL to pull live scoring data.</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Combination</th>
                  <th>Event</th>
                  <th>Status</th>
                  <th>Total</th>
                  <th>Phases</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {searchedLiveScores.map((score, index) => (
                  <tr key={`${score.sourceId}-${score.sourceRecordId}`}>
                    <td>#{index + 1}</td>
                    <td>
                      <strong>{score.horseName}</strong>
                      <span>{score.riderName}</span>
                    </td>
                    <td>
                      <strong>{score.eventName}</strong>
                      <span>
                        {score.eventDate} / {score.level} / {score.country}
                      </span>
                    </td>
                    <td>
                      <span className={`status-pill status-pill--${score.status}`}>{formatLiveStatus(score.status)}</span>
                    </td>
                    <td className="total-cell">{liveTotal(score).toFixed(1)}</td>
                    <td className="breakdown-cell">
                      {completedPhaseCount(score)}/3 complete
                      <span>
                        D {formatLiveStatus(score.phaseStatuses.dressage)} / SJ{' '}
                        {formatLiveStatus(score.phaseStatuses.showJumping)} / XC{' '}
                        {formatLiveStatus(score.phaseStatuses.crossCountry)}
                      </span>
                    </td>
                    <td>
                      {score.sourceUrl ? (
                        <a href={score.sourceUrl} target="_blank" rel="noreferrer">
                          {score.sourceId}
                        </a>
                      ) : (
                        score.sourceId
                      )}
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
