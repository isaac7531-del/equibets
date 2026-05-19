import feiResultsPayload from '../data/fei_results.json';
import { roundToTenths } from './scoring';

type JsonRecord = Record<string, unknown>;

export type PublicResultRecord = {
  source_id: string;
  source_record_id: string;
  rider_name: string;
  horse_name: string;
  event_name: string;
  event_date: string;
  level: string;
  country: string;
  dressage_score: number;
  show_jumping_penalties: number;
  cross_country_jump_penalties: number;
  cross_country_time_penalties: number;
  collected_at: string;
};

export type PublicScoreRow = {
  id: string;
  sourceId: string;
  riderName: string;
  horseName: string;
  eventName: string;
  eventDate: string;
  level: string;
  country: string;
  dressageScore: number;
  showJumpingPenalties: number;
  crossCountryJumpPenalties: number;
  crossCountryTimePenalties: number;
  totalPenalties: number;
  collectedAt: string;
};

export type PublicResultsSnapshot = {
  updatedAt: string | null;
  results: PublicScoreRow[];
};

const DEFAULT_CURRENT_EVENT_LOOKBACK_DAYS = 7;
const DEFAULT_CURRENT_EVENT_LOOKAHEAD_DAYS = 7;
const DEFAULT_RESULT_LIMIT = 8;

export const loadPublicResults = (payload: unknown = feiResultsPayload): PublicResultsSnapshot => {
  const source = isRecord(payload) ? payload : {};
  const records = Array.isArray(source.results) ? source.results : [];
  const results = records.filter(isPublicResultRecord).map(toPublicScoreRow).sort(sortPublicScores);

  return {
    updatedAt: typeof source.updated_at === 'string' ? source.updated_at : null,
    results,
  };
};

export const selectCurrentEventResults = (
  results: PublicScoreRow[],
  today: Date = new Date(),
  {
    lookbackDays = DEFAULT_CURRENT_EVENT_LOOKBACK_DAYS,
    lookaheadDays = DEFAULT_CURRENT_EVENT_LOOKAHEAD_DAYS,
    limit = DEFAULT_RESULT_LIMIT,
  }: {
    lookbackDays?: number;
    lookaheadDays?: number;
    limit?: number;
  } = {},
) => {
  const anchor = startOfUtcDay(today);
  const start = anchor - lookbackDays * 24 * 60 * 60 * 1000;
  const end = anchor + lookaheadDays * 24 * 60 * 60 * 1000;

  return results
    .filter((result) => {
      const eventTime = Date.parse(`${result.eventDate}T00:00:00Z`);
      return Number.isFinite(eventTime) && eventTime >= start && eventTime <= end;
    })
    .slice(0, limit);
};

export const formatPublicUpdatedAt = (updatedAt: string | null) => {
  if (!updatedAt) {
    return 'No public refresh yet';
  }

  const updatedDate = new Date(updatedAt);
  if (Number.isNaN(updatedDate.getTime())) {
    return 'Refresh time unavailable';
  }

  return `${updatedDate.toISOString().slice(0, 16).replace('T', ' ')} UTC`;
};

const toPublicScoreRow = (record: PublicResultRecord): PublicScoreRow => ({
  id: record.source_record_id,
  sourceId: record.source_id,
  riderName: record.rider_name,
  horseName: record.horse_name,
  eventName: record.event_name,
  eventDate: record.event_date,
  level: record.level,
  country: record.country,
  dressageScore: record.dressage_score,
  showJumpingPenalties: record.show_jumping_penalties,
  crossCountryJumpPenalties: record.cross_country_jump_penalties,
  crossCountryTimePenalties: record.cross_country_time_penalties,
  totalPenalties: roundToTenths(
    record.dressage_score +
      record.show_jumping_penalties +
      record.cross_country_jump_penalties +
      record.cross_country_time_penalties,
  ),
  collectedAt: record.collected_at,
});

const sortPublicScores = (left: PublicScoreRow, right: PublicScoreRow) => {
  if (left.eventDate !== right.eventDate) {
    return right.eventDate.localeCompare(left.eventDate);
  }
  if (left.totalPenalties !== right.totalPenalties) {
    return left.totalPenalties - right.totalPenalties;
  }

  return left.riderName.localeCompare(right.riderName);
};

const isPublicResultRecord = (value: unknown): value is PublicResultRecord => {
  if (!isRecord(value)) {
    return false;
  }

  return (
    isString(value.source_id) &&
    isString(value.source_record_id) &&
    isString(value.rider_name) &&
    isString(value.horse_name) &&
    isString(value.event_name) &&
    isIsoDate(value.event_date) &&
    isString(value.level) &&
    isString(value.country) &&
    isNumber(value.dressage_score) &&
    isNumber(value.show_jumping_penalties) &&
    isNumber(value.cross_country_jump_penalties) &&
    isNumber(value.cross_country_time_penalties) &&
    isString(value.collected_at)
  );
};

const isRecord = (value: unknown): value is JsonRecord =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const isString = (value: unknown): value is string => typeof value === 'string' && value.length > 0;

const isNumber = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);

const isIsoDate = (value: unknown): value is string =>
  isString(value) && /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(`${value}T00:00:00Z`));

const startOfUtcDay = (value: Date) =>
  Date.UTC(value.getUTCFullYear(), value.getUTCMonth(), value.getUTCDate());
