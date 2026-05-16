import { describe, expect, it } from 'vitest';
import {
  formatDateRange,
  liveEntryTotal,
  rankLiveEntries,
  scoreStatusLabel,
  summarizeLiveSnapshot,
  type LiveScoringSnapshot,
} from './liveScoring';

const snapshot = {
  version: 1,
  generated_at: '2026-05-16T14:01:00Z',
  sources: [{ id: 'startbox_scoring', name: 'StartBox', url: 'https://example.com' }],
  events: [
    {
      id: 'event-1',
      source_id: 'startbox_scoring',
      source_name: 'StartBox',
      name: 'Current Horse Trial',
      date_label: 'May 16-17, 2026',
      starts_on: '2026-05-16',
      ends_on: '2026-05-17',
      location: 'Fresno, CA US',
      country: 'US',
      status: 'live',
      score_status: 'results',
      result_url: 'https://example.com/results',
      divisions: [
        {
          name: 'Open Training',
          phase_status: 'Dressage: 7:30 AM Sat. Ring 1',
          entry_status_url: null,
          times_url: null,
        },
      ],
      entries: [
        {
          id: 'entry-2',
          riderName: 'Riley West',
          horseName: 'Cedar',
          division: 'Open Training',
          status: 'provisional',
          score: {
            dressagePenalties: 31.2,
            showJumpingPenalties: 0,
            crossCountryJumpPenalties: 0,
            crossCountryTimePenalties: 1.2,
          },
        },
        {
          id: 'entry-1',
          riderName: 'Jordan Hill',
          horseName: 'Beacon',
          division: 'Open Training',
          status: 'provisional',
          score: {
            totalPenalties: 29.8,
          },
        },
        {
          id: 'entry-3',
          riderName: 'Taylor Snow',
          horseName: 'Aspen',
          division: 'Open Training',
          status: 'scheduled',
          score: null,
        },
      ],
    },
  ],
} satisfies LiveScoringSnapshot;

describe('live scoring snapshot helpers', () => {
  it('calculates live entry totals from phase penalties', () => {
    expect(liveEntryTotal(snapshot.events[0].entries[0])).toBe(32.4);
    expect(liveEntryTotal(snapshot.events[0].entries[2])).toBeNull();
  });

  it('ranks scored entries ahead of unscored entries by lowest penalties', () => {
    expect(rankLiveEntries(snapshot).map((ranked) => ranked.entry.horseName)).toEqual(['Beacon', 'Cedar', 'Aspen']);
  });

  it('summarizes current-event coverage', () => {
    expect(summarizeLiveSnapshot(snapshot)).toEqual({
      eventCount: 1,
      liveEventCount: 1,
      divisionCount: 1,
      entryCount: 3,
      scoredEntryCount: 2,
      sourceCount: 1,
    });
  });

  it('formats status labels and date ranges for display', () => {
    expect(scoreStatusLabel('entry_status')).toBe('Entry Status');
    expect(formatDateRange(snapshot.events[0])).toBe('2026-05-16 to 2026-05-17');
  });
});
