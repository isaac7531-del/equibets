import { describe, expect, it } from 'vitest';
import {
  describeLiveFreshness,
  formatLiveWindow,
  getLiveLeader,
  type LiveScorePayload,
} from './liveScores';

const payload: LiveScorePayload = {
  version: 1,
  generated_at: '2026-05-18T13:00:00+00:00',
  window: {
    start_date: '2026-05-17',
    end_date: '2026-05-19',
  },
  event_count: 1,
  result_count: 1,
  source_ids: ['data_fei'],
  latest_collected_at: '2026-05-18T12:00:00+00:00',
  events: [
    {
      event_name: 'Current Horse Trials',
      event_date: '2026-05-18',
      level: 'CCI3*-S',
      country: 'GBR',
      result_count: 1,
      source_ids: ['data_fei'],
      latest_collected_at: '2026-05-18T12:00:00+00:00',
      standings: [
        {
          rank: 1,
          rider_name: 'Alex Rider',
          horse_name: 'Pocket Rocket',
          finishing_score: 35.8,
          dressage_score: 30.2,
          show_jumping_penalties: 4,
          cross_country_penalties: 1.6,
          source_id: 'data_fei',
          collected_at: '2026-05-18T12:00:00+00:00',
        },
      ],
    },
  ],
};

describe('live score helpers', () => {
  it('selects the first current-event leader', () => {
    expect(getLiveLeader(payload)?.horse_name).toBe('Pocket Rocket');
  });

  it('describes freshness from the latest collected result', () => {
    expect(describeLiveFreshness(payload)).toContain('Latest result pulled');
  });

  it('formats the current scoring window', () => {
    expect(formatLiveWindow(payload)).toContain('2026');
  });
});
