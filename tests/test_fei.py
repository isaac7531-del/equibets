import io
import unittest

from equibets.fei import (
    load_fei_results_csv,
    load_fei_search_pages,
    load_fei_world_rankings_csv,
)


class FEIImportTests(unittest.TestCase):
    def test_search_pages_include_requested_fei_urls(self):
        pages = load_fei_search_pages()

        self.assertEqual(pages["person_search"]["url"], "https://data.fei.org/Person/Search.aspx")
        self.assertEqual(pages["horse_search"]["url"], "https://data.fei.org/Horse/Search.aspx")
        self.assertEqual(pages["calendar_search"]["url"], "https://data.fei.org/Calendar/Search.aspx")
        self.assertEqual(pages["world_rankings"]["url"], "https://data.fei.org/Ranking/Search.aspx")

    def test_fei_csv_export_rows_normalize_to_eventing_results(self):
        export = io.StringIO(
            "\n".join(
                [
                    "rider_name,horse_name,event_name,event_date,level,country,dressage_score,show_jumping_penalties,cross_country_jump_penalties,cross_country_time_penalties,source_record_id",
                    "Ros Canter,Lordships Graffalo,Badminton Horse Trials,05/05/2024,CCI5*-L,GBR,26.0,3.7,0,5.6,fei-badminton-2024-ros",
                    "Laura Collett,London 52,Luhmuhlen Horse Trials,2023-06-18,CCI5*-L,GBR,20.3,0,0,0,fei-luhmuhlen-2023-laura",
                ]
            )
        )

        results = load_fei_results_csv(export, collected_at="2026-05-14T10:00:00")

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].source_id, "data_fei")
        self.assertEqual(results[0].event_date.isoformat(), "2024-05-05")
        self.assertEqual(results[0].finishing_score, 35.3)
        self.assertEqual(results[1].finishing_score, 20.3)

    def test_fei_world_ranking_export_rows_normalize(self):
        export = io.StringIO(
            "\n".join(
                [
                    "ranking_name,rank,rider_name,country,points,as_of",
                    "Eventing World Athlete Rankings,1,Ros Canter,GBR,612.0,2026-05-01",
                    "Eventing World Athlete Rankings,2,Laura Collett,GBR,588.5,2026-05-01",
                ]
            )
        )

        rankings = load_fei_world_rankings_csv(export)

        self.assertEqual(len(rankings), 2)
        self.assertEqual(rankings[0].rank, 1)
        self.assertEqual(rankings[0].rider_name, "Ros Canter")
        self.assertEqual(rankings[0].source_url, "https://data.fei.org/Ranking/Search.aspx")


if __name__ == "__main__":
    unittest.main()
