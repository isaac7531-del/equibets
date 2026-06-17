export type LiveScoreStanding = {
  rank: number;
  rider_name: string;
  horse_name: string;
  finishing_score: number;
  dressage_score: number;
  show_jumping_penalties: number;
  cross_country_penalties: number;
  source_id: string;
  collected_at: string;
};

export type LiveScoreEvent = {
  event_name: string;
  event_date: string;
  level: string;
  country: string;
  result_count: number;
  source_ids: string[];
  latest_collected_at: string | null;
  standings: LiveScoreStanding[];
};

export type LiveScorePayload = {
  version: number;
  generated_at: string | null;
  window: {
    start_date: string | null;
    end_date: string | null;
  };
  event_count: number;
  result_count: number;
  source_ids: string[];
  latest_collected_at: string | null;
  events: LiveScoreEvent[];
};

export const getLiveEvents = (payload: LiveScorePayload) => payload.events ?? [];

export const getFeaturedLiveEvent = (payload: LiveScorePayload) => getLiveEvents(payload)[0];

export const getLiveLeader = (payload: LiveScorePayload) => getFeaturedLiveEvent(payload)?.standings[0];

export const formatDate = (value: string | null | undefined) => {
  if (!value) {
    return 'Not set';
  }

  const dateParts = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  const date = dateParts
    ? new Date(Date.UTC(Number(dateParts[1]), Number(dateParts[2]) - 1, Number(dateParts[3])))
    : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(date);
};

export const formatDateTime = (value: string | null | undefined) => {
  if (!value) {
    return 'Not yet refreshed';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(date);
};

const sourceLabels: Record<string, string> = {
  data_fei: 'FEI Data',
};

export const formatSourceId = (sourceId: string) => sourceLabels[sourceId] ?? sourceId;

export const formatSourceList = (sourceIds: string[]) => sourceIds.map(formatSourceId).join(', ');

export const describeLiveFreshness = (payload: LiveScorePayload) => {
  if (payload.latest_collected_at) {
    return `Latest result pulled ${formatDateTime(payload.latest_collected_at)}`;
  }
  if (payload.generated_at) {
    return `Checked ${formatDateTime(payload.generated_at)}`;
  }
  return 'Waiting for first public-data refresh';
};

export const formatLiveWindow = (payload: LiveScorePayload) => {
  const { start_date: startDate, end_date: endDate } = payload.window;
  if (!startDate || !endDate) {
    return 'Current event window';
  }
  return `${formatDate(startDate)} - ${formatDate(endDate)}`;
};
