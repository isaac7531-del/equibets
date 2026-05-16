import sourceRegistry from '../data/event_sources.json';
import { calculateScore, sortByBestScore, type StoredResult } from './scoring';

type SourceRegistry = {
  sources: SourceRecord[];
};

type SourceRecord = {
  id: string;
  name: string;
  priority: number;
  regions: string[];
  base_url: string | null;
  status: string;
};

export type CurrentEventSearchInput = {
  eventName?: string;
  rider?: string;
  horse?: string;
  region?: string;
  year?: number;
};

export type CurrentEventSearch = {
  sourceId: string;
  sourceName: string;
  sourcePriority: number;
  query: string;
  searchUrl: string;
};

export type LiveResultRecord = {
  source_id: string;
  source_record_id?: string;
  source_priority?: number;
  source_name?: string;
  source_url?: string;
  rider_name: string;
  horse_name: string;
  event_name: string;
  event_date: string;
  level?: string;
  country?: string;
  dressage_score: number;
  show_jumping_penalties: number;
  cross_country_jump_penalties: number;
  cross_country_time_penalties: number;
  collected_at?: string;
};

export type LiveResult = StoredResult & {
  sourceId: string;
  sourceName: string;
  sourcePriority: number;
  sourceRecordId: string;
  collectedAt: string;
  isLiveResult: true;
};

const registry = sourceRegistry as SourceRegistry;

const normalizeRegion = (value: string | undefined) => (value ?? 'global').trim().toLowerCase().replace(/\s+/g, '_');

const sourceHost = (source: SourceRecord) => {
  if (!source.base_url) {
    return undefined;
  }

  try {
    return new URL(source.base_url).host;
  } catch {
    return undefined;
  }
};

const sourceLookup = new Map(registry.sources.map((source) => [source.id, source]));

const sourcesForRegion = (region: string) => {
  const normalizedRegion = normalizeRegion(region);
  const sources = normalizedRegion === 'global'
    ? registry.sources
    : registry.sources.filter(
        (source) => source.regions.includes('global') || source.regions.includes(normalizedRegion),
      );

  return [...sources]
    .filter((source) => source.status === 'active' || source.status === 'planned')
    .sort((a, b) => a.priority - b.priority || (a.id === 'data_fei' ? -1 : b.id === 'data_fei' ? 1 : a.id.localeCompare(b.id)));
};

export const buildCurrentEventSearches = (
  input: CurrentEventSearchInput,
  limit = 5,
): CurrentEventSearch[] => {
  const terms = [
    input.eventName?.trim(),
    input.rider?.trim(),
    input.horse?.trim(),
    'eventing results',
    String(input.year ?? new Date().getFullYear()),
  ].filter((term): term is string => Boolean(term));

  return sourcesForRegion(input.region ?? 'global')
    .slice(0, limit)
    .map((source) => {
      const host = sourceHost(source);
      const query = [...terms, source.name, host ? `site:${host}` : undefined]
        .filter((term): term is string => Boolean(term))
        .join(' ');

      return {
        sourceId: source.id,
        sourceName: source.name,
        sourcePriority: source.priority,
        query,
        searchUrl: `https://duckduckgo.com/?q=${encodeURIComponent(query)}`,
      };
    });
};

export const liveResultFromRecord = (record: LiveResultRecord): LiveResult => {
  const source = sourceLookup.get(record.source_id);
  const sourcePriority = record.source_priority ?? source?.priority ?? 50;
  const score = calculateScore({
    dressagePercentage: 100 - record.dressage_score,
    showJumpingPenalties: record.show_jumping_penalties,
    crossCountryJumpPenalties: record.cross_country_jump_penalties,
    optimumTimeSeconds: 0,
    actualTimeSeconds: 0,
  });
  const totalPenalties = score.totalPenalties + record.cross_country_time_penalties;
  const collectedAt = record.collected_at ?? new Date().toISOString();
  const sourceRecordId =
    record.source_record_id ??
    `${record.source_id}:${record.event_date}:${record.rider_name}:${record.horse_name}`;

  return {
    id: `live:${sourceRecordId}`,
    rider: record.rider_name,
    horse: record.horse_name,
    eventName: record.event_name,
    date: record.event_date,
    level: record.level,
    country: record.country,
    notes: `Pulled from ${record.source_name ?? source?.name ?? record.source_id}`,
    createdAt: collectedAt,
    sourceId: record.source_id,
    sourceName: record.source_name ?? source?.name ?? record.source_id,
    sourcePriority,
    sourceUrl: record.source_url ?? source?.base_url ?? undefined,
    sourceRecordId,
    collectedAt,
    isLiveResult: true,
    dressagePercentage: 100 - record.dressage_score,
    showJumpingPenalties: record.show_jumping_penalties,
    crossCountryJumpPenalties: record.cross_country_jump_penalties,
    optimumTimeSeconds: 0,
    actualTimeSeconds: 0,
    score: {
      ...score,
      crossCountryTimePenalties: record.cross_country_time_penalties,
      totalPenalties: Math.round(totalPenalties * 10) / 10,
    },
  };
};

export const parseLiveResultsPayload = (payload: unknown): LiveResult[] => {
  const records = Array.isArray(payload)
    ? payload
    : payload && typeof payload === 'object' && Array.isArray((payload as { results?: unknown }).results)
      ? (payload as { results: unknown[] }).results
      : [];

  return sortByBestScore(records.map((record) => liveResultFromRecord(record as LiveResultRecord))) as LiveResult[];
};

export const pullLiveResultsFromUrl = async (
  url: string,
  fetcher: typeof fetch = fetch,
): Promise<LiveResult[]> => {
  const response = await fetcher(url, {
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Unable to pull live results (${response.status})`);
  }

  return parseLiveResultsPayload(await response.json());
};
