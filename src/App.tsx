import { FormEvent, useMemo, useState } from 'react';
import {
  calculateScore,
  formatSeconds,
  parseTimeToSeconds,
  sortByBestScore,
  type EventingScoreInput,
  type StoredResult,
} from './scoring';
import { publicResults } from './publicResults';
import {
  combinationOptions,
  consolidateResults,
  filterResults,
  finishingScore,
  latestCollectedAt,
  predictFinishingScore,
  resultFromStoredResult,
  SOURCE_LABELS,
} from './results';
import { loadResults, saveResults } from './storage';

type FormState = {
  rider: string;
  horse: string;
  eventName: string;
  date: string;
  level: string;
  country: string;
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
  level: 'CCI2-S',
  country: 'GBR',
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
const sourceLabel = (sourceId: string) => SOURCE_LABELS[sourceId] ?? sourceId;
const formatDate = (value: string) => new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric' }).format(new Date(value));
const formatDateTime = (value: string | null) =>
  value
    ? new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value))
    : 'No public data yet';

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
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCombination, setSelectedCombination] = useState('');
  const scoreInput = useMemo(() => createScoreInput(form), [form]);
  const currentScore = useMemo(() => calculateScore(scoreInput), [scoreInput]);
  const sortedResults = useMemo(() => sortByBestScore(results), [results]);
  const bestResult = sortedResults[0];
  const savedResultRecords = useMemo(() => results.map(resultFromStoredResult), [results]);
  const allResultRecords = useMemo(() => [...publicResults, ...savedResultRecords], [savedResultRecords]);
  const consolidatedResults = useMemo(() => consolidateResults(allResultRecords), [allResultRecords]);
  const filteredConsolidatedResults = useMemo(
    () => filterResults(consolidatedResults, searchQuery),
    [consolidatedResults, searchQuery],
  );
  const publicSourceCount = new Set(publicResults.map((result) => result.sourceId)).size;
  const latestRefresh = latestCollectedAt(publicResults);
  const options = combinationOptions(consolidatedResults);
  const activeCombination = selectedCombination || options[0]?.key || '';
  const prediction = useMemo(
    () => predictFinishingScore(consolidatedResults, activeCombination),
    [consolidatedResults, activeCombination],
  );

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
      level: form.level.trim(),
      country: form.country.trim().toUpperCase(),
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
          <h1>Eventing form guide and score tracker</h1>
          <p className="hero-copy">
            Capture your own scores, combine them with public eventing results, and estimate a horse-and-rider
            combination's likely finishing score.
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
          <span>Public data</span>
          <strong>{publicResults.length}</strong>
          <p>{publicSourceCount} sources, refreshed {formatDateTime(latestRefresh)}</p>
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
            <label>
              Level
              <input required value={form.level} onChange={(event) => updateField('level', event.target.value)} placeholder="CCI2-S" />
            </label>
            <label>
              Country
              <input
                required
                value={form.country}
                onChange={(event) => updateField('country', event.target.value)}
                placeholder="GBR"
                maxLength={3}
              />
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
                        <span>
                          {result.date} - {result.level || 'Unspecified'} {result.country || ''}
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
          )}
        </section>
      </section>

      <section className="form-guide-grid" aria-label="Consolidated form guide">
        <section className="prediction-card" aria-labelledby="prediction-heading">
          <div className="section-heading">
            <p className="eyebrow">Prediction</p>
            <h2 id="prediction-heading">Likely finishing score</h2>
          </div>

          <label>
            Combination
            <select
              value={activeCombination}
              onChange={(event) => setSelectedCombination(event.target.value)}
              disabled={options.length === 0}
            >
              {options.map((option) => (
                <option key={option.key} value={option.key}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          {prediction ? (
            <div className="prediction-summary">
              <span className={`confidence-pill confidence-${prediction.confidence}`}>{prediction.confidence} confidence</span>
              <strong>{prediction.likelyFinishingScore.toFixed(1)}</strong>
              <p>
                Based on {prediction.recentResultCount} recent consolidated starts for {prediction.horseName} and{' '}
                {prediction.riderName}.
              </p>
              <dl>
                <div>
                  <dt>Best recent</dt>
                  <dd>{prediction.bestRecentScore.toFixed(1)}</dd>
                </div>
                <div>
                  <dt>Worst recent</dt>
                  <dd>{prediction.worstRecentScore.toFixed(1)}</dd>
                </div>
                <div>
                  <dt>Sources</dt>
                  <dd>{prediction.sourceIds.map(sourceLabel).join(', ')}</dd>
                </div>
              </dl>
            </div>
          ) : (
            <div className="empty-state">
              <strong>No prediction yet.</strong>
              <p>Save or import results for a combination to calculate its likely score.</p>
            </div>
          )}
        </section>

        <section className="results-card consolidated-card" aria-labelledby="consolidated-results-heading">
          <div className="results-header">
            <div>
              <p className="eyebrow">Consolidated data</p>
              <h2 id="consolidated-results-heading">Recent form guide</h2>
            </div>
            <label className="search-box">
              Search
              <input
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Horse, rider, event, source"
              />
            </label>
          </div>

          {filteredConsolidatedResults.length === 0 ? (
            <div className="empty-state">
              <strong>No matching results.</strong>
              <p>Try another horse, rider, event, country, level, or source.</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Combination</th>
                    <th>Event</th>
                    <th>Level</th>
                    <th>Source</th>
                    <th>Total</th>
                    <th>Phases</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredConsolidatedResults.map((result) => (
                    <tr key={`${result.sourceId}-${result.sourceRecordId}`}>
                      <td>
                        <strong>{result.horseName}</strong>
                        <span>{result.riderName}</span>
                      </td>
                      <td>
                        <strong>{result.eventName}</strong>
                        <span>{formatDate(result.eventDate)}</span>
                      </td>
                      <td>
                        <strong>{result.level}</strong>
                        <span>{result.country}</span>
                      </td>
                      <td>
                        <span className={`source-badge ${result.isUserEntered ? 'source-user' : ''}`}>
                          {sourceLabel(result.sourceId)}
                        </span>
                      </td>
                      <td className="total-cell">{finishingScore(result).toFixed(1)}</td>
                      <td className="breakdown-cell">
                        D {result.dressageScore.toFixed(1)} / SJ {result.showJumpingPenalties.toFixed(1)} / XC{' '}
                        {(result.crossCountryJumpPenalties + result.crossCountryTimePenalties).toFixed(1)}
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
