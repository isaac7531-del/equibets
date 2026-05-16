import { roundToTenths } from './scoring';

export type PhaseStatus = 'not_started' | 'in_progress' | 'complete';
export type LiveStatus = 'entered' | 'live' | 'complete' | 'withdrawn' | 'eliminated' | 'retired';

export type LiveEventScore = {
  sourceId: string;
  sourceRecordId: string;
  sourcePriority: number;
  riderName: string;
  horseName: string;
  eventName: string;
  eventDate: string;
  level: string;
  country: string;
  status: LiveStatus;
  dressageScore: number | null;
  showJumpingPenalties: number | null;
  crossCountryJumpPenalties: number | null;
  crossCountryTimePenalties: number | null;
  phaseStatuses: {
    dressage: PhaseStatus;
    showJumping: PhaseStatus;
    crossCountry: PhaseStatus;
  };
  collectedAt: string;
  sourceUrl: string | null;
};

export type LiveScoreFeed = {
  generatedAt: string | null;
  sourceIds: string[];
  scores: LiveEventScore[];
};

const DEFAULT_LIVE_FEED_URL = '/current-events.json';
const COMPETITIVE_STATUSES = new Set<LiveStatus>(['entered', 'live', 'complete']);
const LIVE_STATUSES = new Set<LiveStatus>(['entered', 'live', 'complete', 'withdrawn', 'eliminated', 'retired']);
const PHASE_STATUSES = new Set<PhaseStatus>(['not_started', 'in_progress', 'complete']);

type RawRecord = Record<string, unknown>;

export const liveTotal = (score: LiveEventScore) =>
  roundToTenths(
    [
      score.dressageScore,
      score.showJumpingPenalties,
      score.crossCountryJumpPenalties,
      score.crossCountryTimePenalties,
    ].reduce<number>((total, value) => total + (typeof value === 'number' ? value : 0), 0),
  );

export const completedPhaseCount = (score: LiveEventScore) =>
  Object.values(score.phaseStatuses).filter((status) => status === 'complete').length;

export const formatLiveStatus = (status: LiveStatus | PhaseStatus) =>
  status
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');

export const sortLiveScores = (scores: LiveEventScore[]) =>
  [...scores].sort((a, b) => {
    const aCompetitive = COMPETITIVE_STATUSES.has(a.status);
    const bCompetitive = COMPETITIVE_STATUSES.has(b.status);
    if (aCompetitive !== bCompetitive) {
      return aCompetitive ? -1 : 1;
    }

    const phaseDifference = completedPhaseCount(b) - completedPhaseCount(a);
    if (phaseDifference !== 0) {
      return phaseDifference;
    }

    const totalDifference = liveTotal(a) - liveTotal(b);
    if (totalDifference !== 0) {
      return totalDifference;
    }

    return `${a.riderName} ${a.horseName}`.localeCompare(`${b.riderName} ${b.horseName}`);
  });

export const searchLiveScores = (scores: LiveEventScore[], query: string, limit?: number) => {
  const tokens = query
    .split(/\s+/)
    .map(slug)
    .filter(Boolean);

  const matches =
    tokens.length === 0
      ? sortLiveScores(scores)
      : sortLiveScores(
          scores.filter((score) => {
            const haystack = slug(
              [
                score.riderName,
                score.horseName,
                score.eventName,
                score.level,
                score.country,
                score.sourceId,
                score.status,
              ].join(' '),
            );
            return tokens.every((token) => haystack.includes(token));
          }),
        );

  return typeof limit === 'number' ? matches.slice(0, limit) : matches;
};

export const normalizeLiveFeed = (payload: unknown): LiveScoreFeed => {
  const record = asRecord(payload);
  if (!record) {
    return emptyFeed();
  }

  const scores = dedupeLiveScores([...scoresFromEvents(record), ...scoresFromResults(record)]);
  return {
    generatedAt: stringField(record, ['generated_at', 'generatedAt']) ?? null,
    sourceIds: stringArray(record.source_ids ?? record.sourceIds) ?? [...new Set(scores.map((score) => score.sourceId))].sort(),
    scores: sortLiveScores(scores),
  };
};

export const loadLiveScoreFeed = async (urls: string | string[] = DEFAULT_LIVE_FEED_URL): Promise<LiveScoreFeed> => {
  if (typeof fetch === 'undefined') {
    return emptyFeed();
  }

  const feedUrls = (Array.isArray(urls) ? urls : [urls]).filter(Boolean);
  const feeds = await Promise.all(
    feedUrls.map(async (url) => {
      try {
        const response = await fetch(url);
        if (!response.ok) {
          return emptyFeed();
        }
        return normalizeLiveFeed(await response.json());
      } catch {
        return emptyFeed();
      }
    }),
  );

  const scores = dedupeLiveScores(feeds.flatMap((feed) => feed.scores));
  const generatedAt = feeds
    .map((feed) => feed.generatedAt)
    .filter((value): value is string => typeof value === 'string')
    .sort()
    .at(-1);

  return {
    generatedAt: generatedAt ?? null,
    sourceIds: [...new Set(feeds.flatMap((feed) => feed.sourceIds))].sort(),
    scores: sortLiveScores(scores),
  };
};

const scoresFromEvents = (record: RawRecord) => {
  if (!Array.isArray(record.events)) {
    return [];
  }

  return record.events.flatMap((event) => {
    const eventRecord = asRecord(event);
    if (!eventRecord || !Array.isArray(eventRecord.results)) {
      return [];
    }

    const defaults = {
      source_id: eventRecord.source_id,
      sourceId: eventRecord.sourceId,
      source_priority: eventRecord.source_priority,
      sourcePriority: eventRecord.sourcePriority,
      event_name: eventRecord.event_name ?? eventRecord.name,
      eventName: eventRecord.eventName ?? eventRecord.name,
      event_date: eventRecord.event_date ?? eventRecord.date,
      eventDate: eventRecord.eventDate ?? eventRecord.date,
      level: eventRecord.level,
      country: eventRecord.country,
      status: eventRecord.status,
      source_url: eventRecord.source_url,
      sourceUrl: eventRecord.sourceUrl,
      collected_at: eventRecord.collected_at,
      collectedAt: eventRecord.collectedAt,
    };

    return eventRecord.results
      .map((result) => {
        const resultRecord = asRecord(result);
        return resultRecord ? scoreFromRecord({ ...defaults, ...resultRecord }) : null;
      })
      .filter((score): score is LiveEventScore => score !== null);
  });
};

const scoresFromResults = (record: RawRecord) => {
  if (!Array.isArray(record.results)) {
    return [];
  }

  return record.results
    .map((result) => {
      const resultRecord = asRecord(result);
      return resultRecord ? scoreFromRecord(resultRecord) : null;
    })
    .filter((score): score is LiveEventScore => score !== null);
};

const scoreFromRecord = (record: RawRecord): LiveEventScore | null => {
  const sourceId = stringField(record, ['source_id', 'sourceId']);
  const sourceRecordId = stringField(record, ['source_record_id', 'sourceRecordId', 'id']);
  const riderName = stringField(record, ['rider_name', 'riderName', 'rider']);
  const horseName = stringField(record, ['horse_name', 'horseName', 'horse']);
  const eventName = stringField(record, ['event_name', 'eventName']);
  const eventDate = stringField(record, ['event_date', 'eventDate']);
  const level = stringField(record, ['level']);
  const country = stringField(record, ['country']);
  const collectedAt = stringField(record, ['collected_at', 'collectedAt']) ?? new Date().toISOString();

  if (!sourceId || !sourceRecordId || !riderName || !horseName || !eventName || !eventDate || !level || !country) {
    return null;
  }

  const dressageScore = numberField(record, ['dressage_score', 'dressageScore']);
  const showJumpingPenalties = numberField(record, ['show_jumping_penalties', 'showJumpingPenalties']);
  const crossCountryJumpPenalties = numberField(record, [
    'cross_country_jump_penalties',
    'crossCountryJumpPenalties',
  ]);
  const crossCountryTimePenalties = numberField(record, [
    'cross_country_time_penalties',
    'crossCountryTimePenalties',
  ]);
  const phaseStatuses = phaseStatusesFromRecord(record, {
    dressageScore,
    showJumpingPenalties,
    crossCountryJumpPenalties,
    crossCountryTimePenalties,
  });

  return {
    sourceId,
    sourceRecordId,
    sourcePriority: numberField(record, ['source_priority', 'sourcePriority']) ?? 50,
    riderName,
    horseName,
    eventName,
    eventDate,
    level,
    country,
    status: statusField(record, phaseStatuses),
    dressageScore,
    showJumpingPenalties,
    crossCountryJumpPenalties,
    crossCountryTimePenalties,
    phaseStatuses,
    collectedAt,
    sourceUrl: stringField(record, ['source_url', 'sourceUrl']) ?? null,
  };
};

const phaseStatusesFromRecord = (
  record: RawRecord,
  scores: Pick<
    LiveEventScore,
    'dressageScore' | 'showJumpingPenalties' | 'crossCountryJumpPenalties' | 'crossCountryTimePenalties'
  >,
) => {
  const phaseRecord = asRecord(record.phase_statuses) ?? asRecord(record.phaseStatuses) ?? {};
  return {
    dressage: phaseStatusField(phaseRecord, ['dressage'], scores.dressageScore),
    showJumping: phaseStatusField(phaseRecord, ['show_jumping', 'showJumping'], scores.showJumpingPenalties),
    crossCountry: phaseStatusField(
      phaseRecord,
      ['cross_country', 'crossCountry'],
      scores.crossCountryJumpPenalties ?? scores.crossCountryTimePenalties,
    ),
  };
};

const statusField = (record: RawRecord, phaseStatuses: LiveEventScore['phaseStatuses']): LiveStatus => {
  const value = stringField(record, ['status']);
  if (value && LIVE_STATUSES.has(value as LiveStatus)) {
    return value as LiveStatus;
  }

  return Object.values(phaseStatuses).every((status) => status === 'complete') ? 'complete' : 'live';
};

const phaseStatusField = (record: RawRecord, keys: string[], score: number | null): PhaseStatus => {
  const value = stringField(record, keys);
  if (value && PHASE_STATUSES.has(value as PhaseStatus)) {
    return value as PhaseStatus;
  }

  return typeof score === 'number' ? 'complete' : 'not_started';
};

const dedupeLiveScores = (scores: LiveEventScore[]) => {
  const selected = new Map<string, LiveEventScore>();
  scores.forEach((score) => {
    const existing = selected.get(scoreKey(score));
    if (!existing || isBetterScore(score, existing)) {
      selected.set(scoreKey(score), score);
    }
  });
  return [...selected.values()];
};

const isBetterScore = (candidate: LiveEventScore, existing: LiveEventScore) => {
  if (candidate.sourcePriority !== existing.sourcePriority) {
    return candidate.sourcePriority < existing.sourcePriority;
  }

  const phaseDifference = completedPhaseCount(candidate) - completedPhaseCount(existing);
  if (phaseDifference !== 0) {
    return phaseDifference > 0;
  }

  return candidate.collectedAt.localeCompare(existing.collectedAt) > 0;
};

const scoreKey = (score: LiveEventScore) =>
  [score.riderName, score.horseName, score.eventName, score.eventDate, score.level].map(slug).join('::');

const emptyFeed = (): LiveScoreFeed => ({
  generatedAt: null,
  sourceIds: [],
  scores: [],
});

const asRecord = (value: unknown): RawRecord | null =>
  typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as RawRecord) : null;

const stringField = (record: RawRecord, keys: string[]) => {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }
  return undefined;
};

const stringArray = (value: unknown) =>
  Array.isArray(value) && value.every((item) => typeof item === 'string') ? [...value] : null;

const numberField = (record: RawRecord, keys: string[]) => {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
  }
  return null;
};

const slug = (value: string) => value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
