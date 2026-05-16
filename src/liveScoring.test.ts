import { describe, expect, it } from 'vitest';
import { getLiveLeaderRows, sortLiveLeaderRows, type LiveScoreFeed } from './liveScoring';

const feed = {
  version: 1,
  generated_at: '2026-05-16T22:00:00+00:00',
  as_of_date: '2026-05-16',
  source_id: 'startbox_current_events',
  source_name: 'StartBox current eventing scores',
  source_url: 'http://eventing.startboxscoring.com/',
  events: [
    {
      id: 'event-1',
      name: 'Current Horse Trial',
      date_label: 'May 16, 2026',
      start_date: '2026-05-16',
      end_date: '2026-05-16',
      location: 'Sandy, UT',
      country: 'US',
      status: 'Results',
      source_url: 'https://eventing.startboxscoring.com/eventsu/current/sht0526/',
      divisions: [
        {
          division: 'Training',
          phase: 'Final Scores',
          phase_links: [],
          leader: {
            rider: 'Alex Griffiths',
            horse: 'Kindle',
            score: 30.7,
          },
        },
        {
          division: 'Starter',
          phase: 'Times',
          phase_links: [],
          leader: null,
        },
      ],
    },
    {
      id: 'event-2',
      name: 'Weekend Horse Trial',
      date_label: 'May 16-17, 2026',
      start_date: '2026-05-16',
      end_date: '2026-05-17',
      location: 'Fresno, CA',
      country: 'US',
      status: 'Results',
      source_url: 'https://eventing.startboxscoring.com/eventsu/weekend/sht0526/',
      divisions: [
        {
          division: 'Novice',
          phase: 'Provisional Scores',
          phase_links: [],
          leader: {
            rider: 'Georgia Myers',
            horse: 'Cybele',
            score: 28.4,
          },
        },
      ],
    },
  ],
} satisfies LiveScoreFeed;

describe('live scoring feed helpers', () => {
  it('extracts rows that have current leaders', () => {
    expect(getLiveLeaderRows(feed)).toHaveLength(2);
  });

  it('sorts live leaders from lowest score to highest', () => {
    const sorted = sortLiveLeaderRows(getLiveLeaderRows(feed));

    expect(sorted.map((row) => row.leader.horse)).toEqual(['Cybele', 'Kindle']);
  });
});
