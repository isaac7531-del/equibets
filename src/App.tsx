import { FormEvent, useEffect, useMemo, useState } from 'react';
import {
  buildRiderLevelDirectory,
  calculateScore,
  formatSeconds,
  parseTimeToSeconds,
  resultLevel,
  sortByBestScore,
  type EventingScoreInput,
  type StoredResult,
} from './scoring';
import { loadResults, saveResults } from './storage';
import liveScorePayload from './data/live_scores.json';

type FormState = {
  rider: string;
  horse: string;
  eventName: string;
  level: string;
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

type LiveScoreResult = {
  rank: number;
  rider_name: string;
  horse_name: string;
  total_penalties: number;
  dressage_score: number;
  show_jumping_penalties: number;
  cross_country_jump_penalties: number;
  cross_country_time_penalties: number;
  collected_at: string;
};

type LiveScoreEvent = {
  event_name: string;
  event_date: string;
  level: string;
  country: string;
  result_count: number;
  leader: LiveScoreResult | null;
  results: LiveScoreResult[];
};

type LiveScoresPayload = {
  generated_at: string;
  window_start: string;
  window_end: string;
  event_count: number;
  result_count: number;
  events: LiveScoreEvent[];
};

const createDefaultFormState = (): FormState => ({
  rider: '',
  horse: '',
  eventName: '',
  level: 'Starter',
  date: new Date().toISOString().slice(0, 10),
  dressagePercentage: '68.5',
  showJumpingPenalties: '0',
  crossCountryJumpPenalties: '0',
  optimumMinutes: '5',
  optimumSeconds: '30',
  actualMinutes: '5',
  actualSeconds: '30',
  notes: '',
});

const numberValue = (value: string) => Number.parseFloat(value || '0');
const liveScores = liveScorePayload as LiveScoresPayload;
const levelOptions = [
  'Starter',
  'Beginner Novice',
  'Novice',
  'Training',
  'Modified',
  'Preliminary',
  'Intermediate',
  'Advanced',
];

const createScoreInput = (form: FormState): EventingScoreInput => ({
  dressagePercentage: numberValue(form.dressagePercentage),
  showJumpingPenalties: numberValue(form.showJumpingPenalties),
  crossCountryJumpPenalties: numberValue(form.crossCountryJumpPenalties),
  optimumTimeSeconds: parseTimeToSeconds(numberValue(form.optimumMinutes), numberValue(form.optimumSeconds)),
  actualTimeSeconds: parseTimeToSeconds(numberValue(form.actualMinutes), numberValue(form.actualSeconds)),
});

const formatDate = (value: string) =>
  new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(`${value}T00:00:00Z`));

const formatDateTime = (value: string) =>
  new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZone: 'UTC',
    timeZoneName: 'short',
  }).format(new Date(value));

export default function App() {
  const [form, setForm] = useState<FormState>(() => createDefaultFormState());
  const [results, setResults] = useState<StoredResult[]>(() => loadResults());
  const [selectedRider, setSelectedRider] = useState('all');
  const scoreInput = useMemo(() => createScoreInput(form), [form]);
  const currentScore = useMemo(() => calculateScore(scoreInput), [scoreInput]);
  const sortedResults = useMemo(() => sortByBestScore(results), [results]);
  const bestResult = sortedResults[0];
  const riderOptions = useMemo(
    () => [...new Set(results.map((result) => result.rider))].sort((a, b) => a.localeCompare(b)),
    [results],
  );
  const riderDirectory = useMemo(
    () => buildRiderLevelDirectory(results, selectedRider),
    [results, selectedRider],
  );
  const visibleResults = useMemo(
    () =>
      selectedRider === 'all'
        ? sortedResults
        : sortedResults.filter((result) => result.rider === selectedRider),
    [selectedRider, sortedResults],
  );
  const featuredLiveEvent = liveScores.events[0];
  const liveWindow = `${formatDate(liveScores.window_start)} - ${formatDate(liveScores.window_end)}`;
  const liveUpdatedAt = formatDateTime(liveScores.generated_at);

  useEffect(() => {
    if (selectedRider !== 'all' && !riderOptions.includes(selectedRider)) {
      setSelectedRider('all');
    }
  }, [riderOptions, selectedRider]);

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
      level: form.level,
      date: form.date,
      notes: form.notes.trim(),
      createdAt: new Date().toISOString(),
      score: currentScore,
    };

    const nextResults = [newResult, ...results];
    setResults(nextResults);
    saveResults(nextResults);
    setForm(createDefaultFormState());
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
      </section>

      <section className="live-scoring-card" aria-labelledby="live-scoring-heading">
        <div className="live-header">
          <div>
            <p className="eyebrow">Current events</p>
            <h2 id="live-scoring-heading">Live public scoring</h2>
            <p>
              FEI results pulled for {liveWindow}. Standings rank public combinations from lowest penalties to highest.
            </p>
          </div>
          <div className="live-source-badge">
            <span>Source</span>
            <strong>data.fei.org</strong>
          </div>
        </div>

        <div className="live-stats" aria-label="Live public scoring summary">
          <article>
            <span>Public events</span>
            <strong>{liveScores.event_count}</strong>
          </article>
          <article>
            <span>Public results</span>
            <strong>{liveScores.result_count}</strong>
          </article>
          <article>
            <span>Updated</span>
            <strong>{liveUpdatedAt}</strong>
          </article>
        </div>

        {featuredLiveEvent ? (
          <div className="live-content-grid">
            <article className="live-feature">
              <div className="live-event-heading">
                <div>
                  <span>
                    {featuredLiveEvent.level} · {featuredLiveEvent.country} · {formatDate(featuredLiveEvent.event_date)}
                  </span>
                  <h3>{featuredLiveEvent.event_name}</h3>
                </div>
                <strong>{featuredLiveEvent.result_count} results</strong>
              </div>

              {featuredLiveEvent.leader ? (
                <div className="leader-card">
                  <span>Current leader</span>
                  <strong>{featuredLiveEvent.leader.horse_name}</strong>
                  <p>
                    {featuredLiveEvent.leader.rider_name} on{' '}
                    {featuredLiveEvent.leader.total_penalties.toFixed(1)} penalties
                  </p>
                </div>
              ) : null}

              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Combination</th>
                      <th>Total</th>
                      <th>Breakdown</th>
                    </tr>
                  </thead>
                  <tbody>
                    {featuredLiveEvent.results.slice(0, 8).map((result) => (
                      <tr key={`${featuredLiveEvent.event_name}-${result.rank}-${result.horse_name}-${result.rider_name}`}>
                        <td>#{result.rank}</td>
                        <td>
                          <strong>{result.horse_name}</strong>
                          <span>{result.rider_name}</span>
                        </td>
                        <td className="total-cell">{result.total_penalties.toFixed(1)}</td>
                        <td className="breakdown-cell">
                          D {result.dressage_score.toFixed(1)} / SJ {result.show_jumping_penalties.toFixed(1)} / XC{' '}
                          {(result.cross_country_jump_penalties + result.cross_country_time_penalties).toFixed(1)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>

            <aside className="live-event-list" aria-label="Current public events">
              <h3>Events in this refresh</h3>
              <div>
                {liveScores.events.map((event) => (
                  <article key={`${event.event_name}-${event.event_date}-${event.level}`}>
                    <strong>{event.event_name}</strong>
                    <span>
                      {event.level} · {formatDate(event.event_date)} · {event.result_count} results
                    </span>
                    {event.leader ? (
                      <p>
                        Leader: {event.leader.horse_name} / {event.leader.rider_name} ({event.leader.total_penalties.toFixed(1)})
                      </p>
                    ) : null}
                  </article>
                ))}
              </div>
            </aside>
          </div>
        ) : (
          <div className="empty-state">
            <strong>No current public results in this refresh.</strong>
            <p>The next FEI refresh will populate this section when current event result pages are available.</p>
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
              Level
              <select required value={form.level} onChange={(event) => updateField('level', event.target.value)}>
                {levelOptions.map((level) => (
                  <option key={level} value={level}>
                    {level}
                  </option>
                ))}
              </select>
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
            <>
              <section className="rider-browser" aria-labelledby="rider-browser-heading">
                <div className="browser-heading">
                  <div>
                    <h3 id="rider-browser-heading">Browse horses by rider</h3>
                    <p>Pick a rider to see every saved horse grouped by level.</p>
                  </div>
                  <label>
                    Rider menu
                    <select value={selectedRider} onChange={(event) => setSelectedRider(event.target.value)}>
                      <option value="all">All riders</option>
                      {riderOptions.map((rider) => (
                        <option key={rider} value={rider}>
                          {rider}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                <div className="rider-directory">
                  {riderDirectory.map((riderGroup) => (
                    <article key={riderGroup.rider}>
                      <h4>{riderGroup.rider}</h4>
                      <div className="level-list">
                        {riderGroup.levels.map((levelGroup) => (
                          <div key={levelGroup.level}>
                            <span>{levelGroup.level}</span>
                            <p>{levelGroup.horses.join(', ')}</p>
                          </div>
                        ))}
                      </div>
                    </article>
                  ))}
                </div>
              </section>

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
                    {visibleResults.map((result, index) => (
                      <tr key={result.id}>
                        <td>#{index + 1}</td>
                        <td>
                          <strong>{result.horse}</strong>
                          <span>{result.rider}</span>
                        </td>
                        <td className="event-cell">
                          <strong>{result.eventName}</strong>
                          <span>
                            {resultLevel(result)} · {result.date}
                          </span>
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
            </>
          )}
        </section>
      </section>
    </main>
  );
}
