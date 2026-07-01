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
import { publicResults } from './publicResults';
import {
  combinationKey,
  combinationOptions,
  consolidateResults,
  filterResults,
  finishingScore,
  latestCollectedAt,
  predictFinishingScore,
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

const createDefaultFormState = (): FormState => ({
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
});

const numberValue = (value: string) => Number.parseFloat(value || '0');
const sourceLabel = (sourceId: string) => SOURCE_LABELS[sourceId] ?? sourceId;
const formatDate = (value: string) => new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric' }).format(new Date(value));
const formatDateTime = (value: string | null) =>
  value
    ? new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value))
    : 'No FEI data yet';
const levelOptions = [
  'Starter',
  'Beginner Novice',
  'Novice',
  'Training',
  'Modified',
  'Preliminary',
  'Intermediate',
  'Advanced',
  'CCI1-S',
  'CCI2-S',
  'CCI3-S',
  'CCI4-S',
  'CCI5-L',
];

const createScoreInput = (form: FormState): EventingScoreInput => ({
  dressagePercentage: numberValue(form.dressagePercentage),
  showJumpingPenalties: numberValue(form.showJumpingPenalties),
  crossCountryJumpPenalties: numberValue(form.crossCountryJumpPenalties),
  optimumTimeSeconds: parseTimeToSeconds(numberValue(form.optimumMinutes), numberValue(form.optimumSeconds)),
  actualTimeSeconds: parseTimeToSeconds(numberValue(form.actualMinutes), numberValue(form.actualSeconds)),
});

export default function App() {
  const [form, setForm] = useState<FormState>(() => createDefaultFormState());
  const [results, setResults] = useState<StoredResult[]>(() => loadResults());
  const [searchQuery, setSearchQuery] = useState('');
  const [combinationSearch, setCombinationSearch] = useState('');
  const [selectedCombination, setSelectedCombination] = useState('');
  const [selectedRider, setSelectedRider] = useState('all');
  const [selectedLevelFilter, setSelectedLevelFilter] = useState('all');
  const [selectedCountryFilter, setSelectedCountryFilter] = useState('all');
  const [selectedStatusFilter, setSelectedStatusFilter] = useState('all');
  const [startDateFilter, setStartDateFilter] = useState('');
  const [endDateFilter, setEndDateFilter] = useState('');
  const [selectedEventKey, setSelectedEventKey] = useState('');
  const [adminEventUrl, setAdminEventUrl] = useState('');
  const [adminHorseName, setAdminHorseName] = useState('');
  const [adminStatus, setAdminStatus] = useState('');
  const scoreInput = useMemo(() => createScoreInput(form), [form]);
  const currentScore = useMemo(() => calculateScore(scoreInput), [scoreInput]);
  const sortedResults = useMemo(() => sortByBestScore(results), [results]);
  const bestResult = sortedResults[0];
  const allResultRecords = useMemo(() => publicResults.filter((result) => result.sourceId === 'data_fei'), []);
  const consolidatedResults = useMemo(() => consolidateResults(allResultRecords), [allResultRecords]);
  const filteredConsolidatedResults = useMemo(
    () =>
      filterResults(consolidatedResults, searchQuery).filter((result) => {
        const matchesLevel = selectedLevelFilter === 'all' || result.level === selectedLevelFilter;
        const matchesCountry = selectedCountryFilter === 'all' || result.country === selectedCountryFilter;
        const matchesStatus = selectedStatusFilter === 'all' || (result.status ?? 'completed') === selectedStatusFilter;
        const matchesStart = !startDateFilter || result.eventDate >= startDateFilter;
        const matchesEnd = !endDateFilter || result.eventDate <= endDateFilter;
        return matchesLevel && matchesCountry && matchesStatus && matchesStart && matchesEnd;
      }),
    [consolidatedResults, endDateFilter, searchQuery, selectedCountryFilter, selectedLevelFilter, selectedStatusFilter, startDateFilter],
  );
  const latestRefresh = latestCollectedAt(publicResults);
  const options = combinationOptions(consolidatedResults);
  const activeCombination = selectedCombination || options[0]?.key || '';
  const prediction = useMemo(
    () => predictFinishingScore(consolidatedResults, activeCombination),
    [consolidatedResults, activeCombination],
  );
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
  const levelFilters = useMemo(() => [...new Set(consolidatedResults.map((result) => result.level))].sort(), [consolidatedResults]);
  const countryFilters = useMemo(() => [...new Set(consolidatedResults.map((result) => result.country))].sort(), [consolidatedResults]);
  const eventSummaries = useMemo(() => buildEventSummaries(consolidatedResults), [consolidatedResults]);
  const combinationSummaries = useMemo(() => buildCombinationSummaries(consolidatedResults), [consolidatedResults]);
  const filteredCombinationSummaries = useMemo(
    () => filterCombinationSummaries(combinationSummaries, combinationSearch),
    [combinationSearch, combinationSummaries],
  );
  const today = new Date().toISOString().slice(0, 10);
  const upcomingEvents = eventSummaries.filter((event) => event.date >= today);
  const pastEvents = eventSummaries.filter((event) => event.date < today);
  const activeEvent = eventSummaries.find((event) => event.key === selectedEventKey) ?? eventSummaries[0];
  const activeEventResults = activeEvent
    ? consolidatedResults.filter((result) => eventKey(result) === activeEvent.key)
    : [];
  const activeCombinationHistory = activeCombination
    ? consolidatedResults.filter((result) => combinationKey(result) === activeCombination)
    : [];

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

  const runAdminAction = async (path: string, body: object) => {
    setAdminStatus('Running admin job...');
    try {
      const response = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      setAdminStatus('Admin job queued successfully.');
    } catch (error) {
      setAdminStatus(error instanceof Error ? error.message : 'Admin job failed.');
    }
  };

  return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">Equibets</p>
          <h1>Eventing form guide and score tracker</h1>
          <p className="hero-copy">
            Mirror FEI Eventing results in one searchable database, track horse performance history, and estimate
            a horse-and-rider combination's likely finishing score.
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
          <span>FEI rows</span>
          <strong>{publicResults.length}</strong>
          <p>FEI only, refreshed {formatDateTime(latestRefresh)}</p>
        </article>
      </section>

      <section className="pipeline-grid" aria-label="FEI Eventing database">
        <article className="results-card">
          <div className="results-header">
            <div>
              <p className="eyebrow">FEI pipeline</p>
              <h2>Events and combinations</h2>
            </div>
            <span className="source-badge">Daily 12-month crawl</span>
          </div>
          <label className="combination-search">
            Search combinations by rider or horse
            <input
              value={combinationSearch}
              onChange={(event) => setCombinationSearch(event.target.value)}
              placeholder="Horse, rider, FEI ID, or horse/rider pair"
            />
          </label>
          <div className="combination-search-results" role="region" aria-label="Combination search results">
            {filteredCombinationSummaries.slice(0, 8).map((combination) => (
              <button
                className={`combination-result-button ${combination.key === activeCombination ? 'combination-result-active' : ''}`}
                key={combination.key}
                type="button"
                onClick={() => setSelectedCombination(combination.key)}
              >
                <strong>{combination.horseName} / {combination.riderName}</strong>
                <span>
                  {combination.resultCount} FEI results / latest {combination.latestEventDate} / {combination.levels.join(', ')}
                </span>
              </button>
            ))}
            {filteredCombinationSummaries.length === 0 ? (
              <p className="muted-copy">No FEI combinations match that rider or horse search.</p>
            ) : null}
          </div>
          <div className="event-columns">
            <div>
              <h3>Upcoming events</h3>
              {upcomingEvents.length === 0 ? (
                <p className="muted-copy">Upcoming entries appear here after FEI start lists are imported.</p>
              ) : (
                upcomingEvents.map((event) => (
                  <button className="event-button" key={event.key} type="button" onClick={() => setSelectedEventKey(event.key)}>
                    {event.name}
                    <span>{event.levels.join(', ')} / {event.country}</span>
                  </button>
                ))
              )}
            </div>
            <div>
              <h3>Past events with results</h3>
              {pastEvents.slice(0, 6).map((event) => (
                <button className="event-button" key={event.key} type="button" onClick={() => setSelectedEventKey(event.key)}>
                  {event.name}
                  <span>{event.date} / {event.levels.join(', ')} / {event.resultCount} combinations</span>
                </button>
              ))}
            </div>
          </div>
          {activeEvent ? (
            <div className="event-detail">
              <h3>{activeEvent.name}</h3>
              <p>{activeEvent.country} - {activeEvent.date} - {activeEvent.levels.join(', ')}</p>
              <div className="combination-chip-list">
                {activeEventResults.map((result) => (
                  <button key={result.sourceRecordId} type="button" onClick={() => setSelectedCombination(combinationKey(result))}>
                    {result.horseName} / {result.riderName}
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </article>

        <article className="prediction-card admin-card">
          <div className="section-heading">
            <p className="eyebrow">Admin</p>
            <h2>Manual FEI rerun</h2>
          </div>
          <label>
            Event result URL
            <input value={adminEventUrl} onChange={(event) => setAdminEventUrl(event.target.value)} placeholder="https://data.fei.org/Result/ResultList.aspx?..." />
          </label>
          <button type="button" disabled={!adminEventUrl} onClick={() => runAdminAction('/admin/scrape/event', { event_url: adminEventUrl })}>
            Re-run event scrape
          </button>
          <label>
            Horse name
            <input value={adminHorseName} onChange={(event) => setAdminHorseName(event.target.value)} placeholder="Horse name or FEI history target" />
          </label>
          <button type="button" disabled={!adminHorseName} onClick={() => runAdminAction('/admin/scrape/horse', { horse_name: adminHorseName })}>
            Re-run horse history
          </button>
          {adminStatus ? <p className="muted-copy" role="status">{adminStatus}</p> : null}
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
                <table className="saved-results-table">
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
                            {resultLevel(result)} - {result.country || 'N/A'} - {result.date}
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
              <p>
                Predicted range {prediction.predictedLowScore.toFixed(1)}-{prediction.predictedHighScore.toFixed(1)} with{' '}
                {prediction.evidence.levelReliability} level reliability and a {prediction.evidence.trendDirection} trend.
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
                <div>
                  <dt>XC clear rate</dt>
                  <dd>{Math.round(prediction.evidence.xcClearJumpingRate * 100)}%</dd>
                </div>
                <div>
                  <dt>Completion</dt>
                  <dd>{Math.round(prediction.evidence.completionRate * 100)}%</dd>
                </div>
                <div>
                  <dt>Recent 3 avg</dt>
                  <dd>{prediction.evidence.recent3RunAverage?.toFixed(1) ?? 'n/a'}</dd>
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
          <div className="filter-grid" aria-label="Filter FEI results">
            <label>
              Filter level
              <select value={selectedLevelFilter} onChange={(event) => setSelectedLevelFilter(event.target.value)}>
                <option value="all">All levels</option>
                {levelFilters.map((level) => (
                  <option key={level} value={level}>{level}</option>
                ))}
              </select>
            </label>
            <label>
              Filter country
              <select value={selectedCountryFilter} onChange={(event) => setSelectedCountryFilter(event.target.value)}>
                <option value="all">All countries</option>
                {countryFilters.map((country) => (
                  <option key={country} value={country}>{country}</option>
                ))}
              </select>
            </label>
            <label>
              Status
              <select value={selectedStatusFilter} onChange={(event) => setSelectedStatusFilter(event.target.value)}>
                <option value="all">All statuses</option>
                <option value="completed">Completed</option>
                <option value="eliminated">Eliminated</option>
                <option value="retired">Retired</option>
                <option value="withdrawn">Withdrawn</option>
              </select>
            </label>
            <label>
              From
              <input type="date" value={startDateFilter} onChange={(event) => setStartDateFilter(event.target.value)} />
            </label>
            <label>
              To
              <input type="date" value={endDateFilter} onChange={(event) => setEndDateFilter(event.target.value)} />
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
                        <span>{result.status ?? 'completed'}{result.merStatus ? ` - MER ${result.merStatus}` : ''}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </section>

      <section className="results-card history-card" aria-labelledby="history-heading">
        <div className="results-header">
          <div>
            <p className="eyebrow">Horse history</p>
            <h2 id="history-heading">Selected combination evidence</h2>
          </div>
        </div>
        {activeCombinationHistory.length === 0 ? (
          <div className="empty-state">
            <strong>No combination history.</strong>
            <p>Select a horse/rider combination after FEI results are imported.</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Event</th>
                  <th>Level</th>
                  <th>Status</th>
                  <th>D</th>
                  <th>XC</th>
                  <th>SJ</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {activeCombinationHistory.map((result) => (
                  <tr key={`history-${result.sourceRecordId}`}>
                    <td>
                      <strong>{result.eventName}</strong>
                      <span>{result.eventDate} - {result.country}</span>
                    </td>
                    <td>{result.level}</td>
                    <td>{result.status ?? 'completed'}</td>
                    <td>{result.dressageScore.toFixed(1)}</td>
                    <td>{(result.crossCountryJumpPenalties + result.crossCountryTimePenalties).toFixed(1)}</td>
                    <td>{(result.showJumpingPenalties + (result.showJumpingTimePenalties ?? 0)).toFixed(1)}</td>
                    <td className="total-cell">{finishingScore(result).toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}

type EventSummary = {
  key: string;
  name: string;
  date: string;
  country: string;
  levels: string[];
  resultCount: number;
};

type CombinationSummary = {
  key: string;
  riderName: string;
  riderFeiId: string;
  horseName: string;
  horseFeiId: string;
  latestEventDate: string;
  levels: string[];
  countries: string[];
  resultCount: number;
};

const eventKey = (result: { eventName: string; eventDate: string; country: string }) =>
  `${result.eventName}::${result.eventDate}::${result.country}`;

const buildEventSummaries = (records: ReturnType<typeof consolidateResults>): EventSummary[] =>
  [...records.reduce((events, result) => {
    const key = eventKey(result);
    const existing = events.get(key);
    if (existing) {
      existing.resultCount += 1;
      if (!existing.levels.includes(result.level)) {
        existing.levels.push(result.level);
      }
    } else {
      events.set(key, {
        key,
        name: result.eventName,
        date: result.eventDate,
        country: result.country,
        levels: [result.level],
        resultCount: 1,
      });
    }
    return events;
  }, new Map<string, EventSummary>()).values()].sort((a, b) => b.date.localeCompare(a.date));

const buildCombinationSummaries = (records: ReturnType<typeof consolidateResults>): CombinationSummary[] =>
  [...records.reduce((combinations, result) => {
    const key = combinationKey(result);
    const existing = combinations.get(key);
    if (existing) {
      existing.resultCount += 1;
      if (result.eventDate > existing.latestEventDate) {
        existing.latestEventDate = result.eventDate;
      }
      if (!existing.levels.includes(result.level)) {
        existing.levels.push(result.level);
      }
      if (!existing.countries.includes(result.country)) {
        existing.countries.push(result.country);
      }
    } else {
      combinations.set(key, {
        key,
        riderName: result.riderName,
        riderFeiId: result.riderFeiId ?? '',
        horseName: result.horseName,
        horseFeiId: result.horseFeiId ?? '',
        latestEventDate: result.eventDate,
        levels: [result.level],
        countries: [result.country],
        resultCount: 1,
      });
    }
    return combinations;
  }, new Map<string, CombinationSummary>()).values()].sort((a, b) => {
    if (a.latestEventDate !== b.latestEventDate) {
      return b.latestEventDate.localeCompare(a.latestEventDate);
    }
    return `${a.horseName} ${a.riderName}`.localeCompare(`${b.horseName} ${b.riderName}`);
  });

const filterCombinationSummaries = (combinations: CombinationSummary[], query: string) => {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) {
    return combinations;
  }
  return combinations.filter((combination) =>
    [
      combination.riderName,
      combination.horseName,
      combination.riderFeiId,
      combination.horseFeiId,
      `${combination.horseName} ${combination.riderName}`,
      `${combination.riderName} ${combination.horseName}`,
    ]
      .join(' ')
      .toLowerCase()
      .includes(normalizedQuery),
  );
};
