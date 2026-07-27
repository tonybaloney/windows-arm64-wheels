import datetime
import json
import os
import tempfile
import unittest

from utils import load_history, update_history


class HistoryTests(unittest.TestCase):
    def test_seed_contains_every_historic_day(self):
        history = load_history(None)

        self.assertEqual(len(history), 469)
        self.assertEqual(history[0]["date"], "2025-04-10")
        self.assertEqual(history[-1]["date"], "2026-07-26")
        self.assertEqual({point["total"] for point in history}, {1000})

    def test_deployed_history_excludes_smaller_tracking_period(self):
        deployed = {
            "history": [
                {"date": "2025-04-09", "unsupported": 41, "total": 360},
                {"date": "2026-07-27", "unsupported": 48, "total": 1000},
            ]
        }

        self.assertEqual(load_history(deployed), deployed["history"][1:])

    def test_legacy_deployment_falls_back_to_seed(self):
        expected = [{"date": "2025-04-10", "unsupported": 124, "total": 1000}]
        with tempfile.TemporaryDirectory() as directory:
            file_name = os.path.join(directory, "history.json")
            with open(file_name, "w") as history_file:
                json.dump(expected, history_file)

            self.assertEqual(load_history({"data": []}, file_name), expected)

    def test_same_day_run_replaces_existing_point(self):
        history = [
            {"date": "2026-07-27", "unsupported": 2, "total": 3},
            {"date": "2026-07-26", "unsupported": 3, "total": 3},
        ]
        packages = [
            {"css_class": "warning"},
            {"css_class": "success"},
            {"css_class": "default"},
        ]
        now = datetime.datetime(2026, 7, 27, tzinfo=datetime.timezone.utc)

        updated = update_history(history, packages, now)

        self.assertEqual(
            updated,
            [
                {"date": "2026-07-26", "unsupported": 3, "total": 3},
                {"date": "2026-07-27", "unsupported": 1, "total": 3},
            ],
        )


if __name__ == "__main__":
    unittest.main()
