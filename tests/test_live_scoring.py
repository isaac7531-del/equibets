import unittest
from datetime import date

from equibets.live_scoring import (
    LiveEventScore,
    live_scores_from_payload,
    merge_completed_live_results,
    parse_startbox_calendar,
    parse_startbox_event_page,
    parse_startbox_scores_page,
    pull_startbox_current_event_scores,
    rank_live_scores,
    search_live_scores,
)
from equibets.results import EventingResult


def live_score(**overrides):
    values = {
        "source_id": "data_fei",
        "source_record_id": "fei-live-1",
        "source_priority": 0,
        "rider_name": "Avery Stone",
        "horse_name": "Juniper",
        "event_name": "Current Spring International",
        "event_date": "2026-05-16",
        "level": "CCI3",
        "country": "GBR",
        "dressage_score": 29.4,
        "show_jumping_penalties": None,
        "cross_country_jump_penalties": None,
        "cross_country_time_penalties": None,
        "phase_statuses": {
            "dressage": "complete",
            "show_jumping": "not_started",
            "cross_country": "not_started",
        },
        "collected_at": "2026-05-16T19:00:00+00:00",
        "status": "live",
    }
    values.update(overrides)
    return LiveEventScore.from_mapping(values)


def completed_result(**overrides):
    values = {
        "source_id": "usea",
        "source_record_id": "old-1",
        "source_priority": 50,
        "rider_name": "Avery Stone",
        "horse_name": "Juniper",
        "event_name": "Winter Horse Trials",
        "event_date": "2026-02-01",
        "level": "CCI3",
        "country": "USA",
        "dressage_score": 31.2,
        "show_jumping_penalties": 4,
        "cross_country_jump_penalties": 0,
        "cross_country_time_penalties": 1.2,
        "collected_at": "2026-02-02T00:00:00",
    }
    values.update(overrides)
    return EventingResult.from_mapping(values)


class LiveScoringTests(unittest.TestCase):
    def test_live_total_uses_available_phase_scores(self):
        score = live_score(show_jumping_penalties=4, phase_statuses={"dressage": "complete", "show_jumping": "complete"})

        self.assertEqual(score.live_total, 33.4)
        self.assertEqual(score.completed_phase_count, 2)
        self.assertFalse(score.is_complete)

    def test_event_payload_is_normalized_and_deduplicated_by_priority(self):
        payload = {
            "events": [
                {
                    "source_id": "usea",
                    "source_priority": 50,
                    "name": "Current Spring International",
                    "date": "2026-05-16",
                    "level": "CCI3",
                    "country": "GBR",
                    "collected_at": "2026-05-16T18:55:00+00:00",
                    "results": [
                        {
                            "source_record_id": "national-1",
                            "rider_name": "Avery Stone",
                            "horse_name": "Juniper",
                            "dressage_score": 31.0,
                        },
                        {
                            "source_id": "data_fei",
                            "source_record_id": "fei-1",
                            "source_priority": 0,
                            "rider_name": "Avery Stone",
                            "horse_name": "Juniper",
                            "dressage_score": 29.4,
                        },
                    ],
                }
            ]
        }

        scores = live_scores_from_payload(payload)

        self.assertEqual(len(scores), 1)
        self.assertEqual(scores[0].source_id, "data_fei")
        self.assertEqual(scores[0].live_total, 29.4)

    def test_search_matches_combination_event_and_source(self):
        scores = [
            live_score(),
            live_score(
                source_record_id="fei-live-2",
                rider_name="Jordan Lee",
                horse_name="River Fox",
                event_name="Autumn International",
            ),
        ]

        matches = search_live_scores(scores, "juniper current data_fei")

        self.assertEqual([match.horse_name for match in matches], ["Juniper"])

    def test_rank_live_scores_puts_more_complete_competitive_scores_first(self):
        scores = [
            live_score(source_record_id="entered", rider_name="Blake Quinn", horse_name="Ready", dressage_score=None),
            live_score(source_record_id="withdrawn", rider_name="Casey Mills", horse_name="Resting", status="withdrawn"),
            live_score(source_record_id="jumped", show_jumping_penalties=0, phase_statuses={"dressage": "complete", "show_jumping": "complete"}),
        ]

        ranked = rank_live_scores(scores)

        self.assertEqual(ranked[0].source_record_id, "jumped")
        self.assertEqual(ranked[-1].source_record_id, "withdrawn")

    def test_completed_live_scores_merge_into_results(self):
        live = live_score(
            status="complete",
            show_jumping_penalties=0,
            cross_country_jump_penalties=0,
            cross_country_time_penalties=2.0,
            phase_statuses={
                "dressage": "complete",
                "show_jumping": "complete",
                "cross_country": "complete",
            },
        )

        merged = merge_completed_live_results([completed_result()], [live])

        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[-1].finishing_score, 31.4)

    def test_startbox_calendar_and_scores_parse_to_live_scores(self):
        calendar_html = """
        <table>
          <tr>
            <td>May 16-17, 2026</td>
            <td><a href="spring/index.php">Results</a></td>
            <td><span class="calshowname">Current Spring Horse Trials</span>
                <span class="callocation">Aiken, SC US</span></td>
          </tr>
        </table>
        """
        event_html = """
        <table>
          <tr>
            <th>Division</th><th>Phase</th>
          </tr>
          <tr>
            <td>Training Rider</td>
            <td>Dressage <a href="division.php?division=TR&phase=2">Provisional Scores</a></td>
          </tr>
        </table>
        """
        scores_html = """
        <table>
          <tr><th>No.</th><th>Rider</th><th>Horse</th><th>Dressage</th><th>SJ</th><th>Total</th><th>Status</th></tr>
          <tr><td>12</td><td>Avery Stone</td><td>Juniper<br />Mare</td><td>29.4</td><td>0</td><td>29.4</td><td></td></tr>
        </table>
        """

        events = parse_startbox_calendar(calendar_html, as_of=date(2026, 5, 16))
        divisions = parse_startbox_event_page(event_html, base_url=events[0].result_url)
        entries = parse_startbox_scores_page(
            scores_html,
            division=divisions[0].name,
            source_url=divisions[0].scores_url or "",
        )

        self.assertEqual(events[0].name, "Current Spring Horse Trials")
        self.assertEqual(events[0].country, "USA")
        self.assertEqual(divisions[0].scores_url, "https://eventing.startboxscoring.com/spring/division.php?division=TR&phase=2")
        self.assertEqual(entries[0].horse_name, "Juniper")
        self.assertEqual(entries[0].total_penalties, 29.4)

    def test_startbox_pull_fetches_current_scores(self):
        pages = {
            "https://eventing.startboxscoring.com/": """
              <table>
                <tr><td>May 16, 2026</td><td><a href="spring">Live Scores</a></td>
                    <td><span class="calshowname">Spring Horse Trials</span><span class="callocation">Ocala, FL US</span></td></tr>
              </table>
            """,
            "https://eventing.startboxscoring.com/spring": """
              <table>
                <tr><td>Training</td><td><a href="scores.php?division=T">Scores</a></td></tr>
              </table>
            """,
            "https://eventing.startboxscoring.com/spring/scores.php?division=T": """
              <table>
                <tr><td>No.</td><td>Rider</td><td>Horse</td><td>Dr</td><td>SJ</td><td>Total</td><td>Status</td></tr>
                <tr><td>4</td><td>Jordan Lee</td><td>River Fox<br>Gelding</td><td>31.2</td><td>4</td><td>35.2</td><td></td></tr>
              </table>
            """,
        }

        def fake_fetch(url, *, timeout_seconds):
            return pages[url]

        import equibets.live_scoring as live_scoring

        original_fetch = live_scoring._fetch_startbox_url
        live_scoring._fetch_startbox_url = fake_fetch
        try:
            scores = pull_startbox_current_event_scores(as_of=date(2026, 5, 16))
        finally:
            live_scoring._fetch_startbox_url = original_fetch

        self.assertEqual(len(scores), 1)
        self.assertEqual(scores[0].source_id, "startbox_scoring")
        self.assertEqual(scores[0].event_name, "Spring Horse Trials")
        self.assertEqual(scores[0].horse_name, "River Fox")
        self.assertEqual(scores[0].live_total, 35.2)


if __name__ == "__main__":
    unittest.main()
