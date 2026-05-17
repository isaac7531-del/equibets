import { describe, expect, it } from 'vitest';
import { formatLeaderName, liveScoreSummary, type LiveScoreSnapshot } from './liveScores';

describe('live score snapshot helpers', () => {
  it('summarizes current events and the lowest live leader', () => {
    const snapshot = {
      version: 1,
      collected_at: '2026-05-17T08:00:29Z',
      as_of_date: '2026-05-17',
      source_id: 'startbox_eventing',
      source_name: 'StartBox Eventing live scores',
      archive_url: 'https://example.test/archive',
      fetched_archive_url: 'https://example.test/archive',
      events: [
        {
          event_name: 'Spring HT',
          date_label: 'May 17, 2026',
          start_date: '2026-05-17',
          end_date: '2026-05-17',
          location: 'Aiken, SC',
          status: 'current',
          source_id: 'startbox_eventing',
          source_url: 'https://example.test/spring',
          fetch_error: null,
          leaders: [
            {
              division: 'Training',
              phase: 'Scores',
              leader_name: 'Avery Stone Juniper',
              rider_name: null,
              horse_name: null,
              score_text: '29.4',
              score: 29.4,
              results_url: 'https://example.test/scores',
            },
          ],
        },
        {
          event_name: 'Local Derby',
          date_label: 'May 16, 2026',
          start_date: '2026-05-16',
          end_date: '2026-05-16',
          location: 'Lexington, KY',
          status: 'completed',
          source_id: 'startbox_eventing',
          source_url: 'https://example.test/derby',
          fetch_error: null,
          leaders: [
            {
              division: 'Novice',
              phase: 'Final Scores',
              leader_name: 'Marlow Reed / Blue Note',
              rider_name: 'Marlow Reed',
              horse_name: 'Blue Note',
              score_text: '26.2',
              score: 26.2,
              results_url: 'https://example.test/final',
            },
          ],
        },
      ],
    } satisfies LiveScoreSnapshot;

    const summary = liveScoreSummary(snapshot);

    expect(summary.eventCount).toBe(2);
    expect(summary.leaderCount).toBe(2);
    expect(summary.lowestLeader?.event.event_name).toBe('Local Derby');
    expect(formatLeaderName(summary.lowestLeader!.leader)).toBe('Marlow Reed / Blue Note');
  });
});
