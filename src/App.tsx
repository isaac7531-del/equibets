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
import {
  createDefaultHorseProfileForm,
  horseProfileFromForm,
  sortHorseProfiles,
  type HorseProfileFormState,
} from './horseProfiles';
import { loadHorseProfiles, saveHorseProfiles } from './storage';
import { latestUpcomingEventRefresh, upcomingEvents } from './upcomingEvents';

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
    : 'No public data yet';
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
const freePlayMarkets = [
  'Win market',
  'Top 3',
  'Top 10',
  'Best dressage',
  'Clear show jumping',
  'Clear cross-country',
  'Head-to-head matchups',
  'Final score over/under',
];
const platformFormats = [
  {
    title: 'Web dashboard',
    status: 'Ready now',
    copy: 'Responsive analytics, score entry, form guide search, and free prediction roadmap in the browser.',
  },
  {
    title: 'Installable app',
    status: 'PWA shell',
    copy: 'Manifest, app icon, standalone display mode, and offline app-shell caching for mobile and desktop installs.',
  },
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
  const [horseProfileForm, setHorseProfileForm] = useState<HorseProfileFormState>(() => createDefaultHorseProfileForm());
  const [horseProfiles, setHorseProfiles] = useState(() => loadHorseProfiles());
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCombination, setSelectedCombination] = useState('');
  const [selectedRider, setSelectedRider] = useState('all');
  const scoreInput = useMemo(() => createScoreInput(form), [form]);
  const currentScore = useMemo(() => calculateScore(scoreInput), [scoreInput]);
  const sortedResults = useMemo(() => sortByBestScore(results), [results]);
  const sortedHorseProfiles = useMemo(() => sortHorseProfiles(horseProfiles), [horseProfiles]);
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
  const latestUpcomingRefresh = latestUpcomingEventRefresh(upcomingEvents);
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

  useEffect(() => {
    if (selectedRider !== 'all' && !riderOptions.includes(selectedRider)) {
      setSelectedRider('all');
    }
  }, [riderOptions, selectedRider]);

  const updateField = (field: keyof FormState, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const updateHorseProfileField = (field: keyof HorseProfileFormState, value: string) => {
    setHorseProfileForm((current) => ({ ...current, [field]: value }));
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

  const handleHorseProfileSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const profile = horseProfileFromForm(horseProfileForm, crypto.randomUUID(), new Date().toISOString());
    const nextProfiles = [profile, ...horseProfiles.filter((existing) => existing.name !== profile.name)];
    setHorseProfiles(nextProfiles);
    saveHorseProfiles(nextProfiles);
    setHorseProfileForm(createDefaultHorseProfileForm());
  };

  const removeHorseProfile = (id: string) => {
    const nextProfiles = horseProfiles.filter((profile) => profile.id !== id);
    setHorseProfiles(nextProfiles);
    saveHorseProfiles(nextProfiles);
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
        <article>
          <span>Upcoming</span>
          <strong>{upcomingEvents.length}</strong>
          <p>sample rows, refresh pipeline ready {formatDateTime(latestUpcomingRefresh)}</p>
        </article>
      </section>

      <section className="platform-strip" aria-labelledby="platform-formats-heading">
        <div>
          <p className="eyebrow">App and web</p>
          <h2 id="platform-formats-heading">Built for browser use and installable app workflows</h2>
        </div>
        <div className="platform-cards">
          {platformFormats.map((format) => (
            <article key={format.title}>
              <span>{format.status}</span>
              <h3>{format.title}</h3>
              <p>{format.copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="horse-data-card" aria-labelledby="horse-data-heading">
        <div className="results-header">
          <div>
            <p className="eyebrow">Horse data</p>
            <h2 id="horse-data-heading">Add horse profile data</h2>
          </div>
          <span className="data-pill">{sortedHorseProfiles.length} saved</span>
        </div>

        <form className="horse-profile-form" onSubmit={handleHorseProfileSubmit}>
          <div className="form-grid horse-profile-grid">
            <label>
              Horse name
              <input
                required
                value={horseProfileForm.name}
                onChange={(event) => updateHorseProfileField('name', event.target.value)}
                placeholder="Competition name"
              />
            </label>
            <label>
              Registered name
              <input
                value={horseProfileForm.registeredName}
                onChange={(event) => updateHorseProfileField('registeredName', event.target.value)}
                placeholder="Official registry name"
              />
            </label>
            <label>
              FEI ID
              <input
                value={horseProfileForm.feiId}
                onChange={(event) => updateHorseProfileField('feiId', event.target.value)}
                placeholder="e.g. 107BH10"
              />
            </label>
            <label>
              Country
              <input
                required
                value={horseProfileForm.country}
                onChange={(event) => updateHorseProfileField('country', event.target.value)}
                maxLength={3}
                placeholder="GBR"
              />
            </label>
            <label>
              Sex
              <input
                value={horseProfileForm.sex}
                onChange={(event) => updateHorseProfileField('sex', event.target.value)}
                placeholder="Mare, gelding, stallion"
              />
            </label>
            <label>
              Birth year
              <input
                inputMode="numeric"
                value={horseProfileForm.birthYear}
                onChange={(event) => updateHorseProfileField('birthYear', event.target.value)}
                placeholder="2014"
              />
            </label>
            <label>
              Color
              <input
                value={horseProfileForm.color}
                onChange={(event) => updateHorseProfileField('color', event.target.value)}
                placeholder="Bay"
              />
            </label>
            <label>
              Owner
              <input
                value={horseProfileForm.owner}
                onChange={(event) => updateHorseProfileField('owner', event.target.value)}
                placeholder="Owner or syndicate"
              />
            </label>
          </div>
          <label>
            Notes
            <textarea
              value={horseProfileForm.notes}
              onChange={(event) => updateHorseProfileField('notes', event.target.value)}
              placeholder="Pedigree notes, previous rider, quirks, or source links"
            />
          </label>
          <button type="submit">Save horse profile</button>
        </form>

        {sortedHorseProfiles.length === 0 ? (
          <div className="empty-state">
            <strong>No horse profiles yet.</strong>
            <p>Add horse records here, then connect them to public results and predictions as the backend comes online.</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="horse-profile-table">
              <thead>
                <tr>
                  <th>Horse</th>
                  <th>Registry</th>
                  <th>Profile</th>
                  <th>Owner</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {sortedHorseProfiles.map((profile) => (
                  <tr key={profile.id}>
                    <td>
                      <strong>{profile.name}</strong>
                      <span>{profile.country}</span>
                    </td>
                    <td>
                      <strong>{profile.feiId || 'No FEI ID'}</strong>
                      <span>{profile.registeredName || 'No registered name yet'}</span>
                    </td>
                    <td>
                      <strong>{[profile.sex, profile.birthYear].filter(Boolean).join(' / ') || 'Profile pending'}</strong>
                      <span>{profile.color || 'Color pending'}</span>
                    </td>
                    <td>
                      <strong>{profile.owner || 'Owner pending'}</strong>
                      <span>{profile.notes || 'No notes'}</span>
                    </td>
                    <td>
                      <button className="link-button" type="button" onClick={() => removeHorseProfile(profile.id)}>
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

      <section className="results-card upcoming-events-card" aria-labelledby="upcoming-events-heading">
        <div className="results-header">
          <div>
            <p className="eyebrow">Worldwide calendar</p>
            <h2 id="upcoming-events-heading">Upcoming event feed</h2>
          </div>
          <span className="data-pill">Daily FEI refresh ready</span>
        </div>
        <p className="supporting-copy">
          These are seed rows for the frontend contract. The scheduled refresh writes the full FEI calendar feed to
          `data/upcoming_events.json` and builds `data/horse_index.json` from every collected result before production
          promotion.
        </p>
        <div className="table-wrap">
          <table className="upcoming-events-table">
            <thead>
              <tr>
                <th>Event</th>
                <th>Dates</th>
                <th>Country</th>
                <th>Level</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {upcomingEvents.map((event) => (
                <tr key={event.sourceEventId}>
                  <td>
                    <strong>{event.name}</strong>
                    <span>{event.discipline}</span>
                  </td>
                  <td>
                    <strong>{formatDate(event.startDate)}</strong>
                    <span>{event.endDate ? `to ${formatDate(event.endDate)}` : 'single day'}</span>
                  </td>
                  <td>{event.country}</td>
                  <td>{event.level}</td>
                  <td>
                    <span className="source-badge">{sourceLabel(event.sourceId)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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

      <section className="market-roadmap" aria-labelledby="market-roadmap-heading">
        <div>
          <p className="eyebrow">Free play only</p>
          <h2 id="market-roadmap-heading">Prediction markets roadmap</h2>
          <p>
            Points-based predictions can sit on top of the probability model before any licensed real-money product
            exists.
          </p>
        </div>
        <ul>
          {freePlayMarkets.map((market) => (
            <li key={market}>{market}</li>
          ))}
        </ul>
        <strong>No deposits, withdrawals, stakes, or paid betting odds.</strong>
      </section>
    </main>
  );
}
