import json
import tempfile
import unittest
from pathlib import Path

from equibets.compliance import SourceComplianceError, require_source_approval


class SourceComplianceTests(unittest.TestCase):
    def test_default_fei_policy_blocks_automated_ingest(self):
        with self.assertRaisesRegex(SourceComplianceError, "not approved"):
            require_source_approval("data_fei", "calendar")

    def test_approved_policy_allows_configured_job_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source_compliance.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "sources": [
                            {
                                "source_id": "data_fei",
                                "display_name": "FEI Database",
                                "base_url": "https://data.fei.org/",
                                "robots_url": "https://data.fei.org/robots.txt",
                                "terms_url": "https://inside.fei.org/fei/terms-and-conditions",
                                "approved_for_ingest": True,
                                "raw_storage_allowed": False,
                                "allowed_job_types": ["calendar"],
                                "reviewed_at": "2026-06-30T00:00:00Z",
                                "reviewed_by": "compliance-admin",
                                "notes": "Approved for calendar import test.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            policy = require_source_approval("data_fei", "calendar", path=path)

        self.assertEqual(policy.source_id, "data_fei")
        self.assertEqual(policy.allowed_job_types, ("calendar",))

    def test_blocks_unapproved_job_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source_compliance.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "sources": [
                            {
                                "source_id": "data_fei",
                                "display_name": "FEI Database",
                                "base_url": None,
                                "robots_url": None,
                                "terms_url": None,
                                "approved_for_ingest": True,
                                "raw_storage_allowed": False,
                                "allowed_job_types": ["calendar"],
                                "reviewed_at": "2026-06-30T00:00:00Z",
                                "reviewed_by": "compliance-admin",
                                "notes": "Calendar only.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(SourceComplianceError, "not approved for results"):
                require_source_approval("data_fei", "results", path=path)


if __name__ == "__main__":
    unittest.main()
