import json
import tempfile
import unittest
from pathlib import Path

from prospective_validation_ledger import __version__
from prospective_validation_ledger.bundle import load_bundle
from prospective_validation_ledger.canonical import canonical_json_bytes, sha256_json
from prospective_validation_ledger.verify import verify_bundle
from tests.support import write_bundle


class VerifyBundleTest(unittest.TestCase):
    def read_ledger(self, path):
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
        ]

    def write_ledger(self, path, rows):
        path.write_bytes(
            b"".join(canonical_json_bytes(row) + b"\n" for row in rows)
        )

    def assert_codes(self, receipt, expected):
        self.assertEqual(receipt["status"], "rejected")
        self.assertEqual(
            [item["code"] for item in receipt["violations"]],
            expected,
        )

    def test_valid_bundle_has_deterministic_eligible_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = load_bundle(write_bundle(Path(temporary)))
            first = verify_bundle(bundle, __version__)
            second = verify_bundle(bundle, __version__)
            self.assertEqual(first, second)
            self.assertEqual(first["status"], "eligible")
            self.assertEqual(first["accepted_count"], 2)
            self.assertEqual(first["rejected_count"], 0)
            self.assertEqual(first["violations"], [])
            self.assertEqual(
                first["receipt_digest"],
                "0c9efe5552d09c0441d8f7cd1ff397d4f0e523c74961ca4c2c9c6d66d45483e5",
            )

    def test_late_arrival_rejects_the_ledger_line(self):
        entries = [
            {
                "entry_id": "entry-001",
                "sample_id": "sample-A",
                "event_at": "2026-08-10T09:00:00Z",
                "arrived_at": "2026-08-16T09:00:00Z",
                "payload_digest": "1" * 64,
            }
        ]
        with tempfile.TemporaryDirectory() as temporary:
            bundle = load_bundle(write_bundle(Path(temporary), entries))
            receipt = verify_bundle(bundle, "0.1.0")

        self.assert_codes(receipt, ["LATE_ARRIVAL"])
        self.assertEqual(
            receipt["violations"],
            [
                {
                    "entry_index": 1,
                    "sample_id": "sample-A",
                    "code": "LATE_ARRIVAL",
                }
            ],
        )

    def test_post_cutoff_event_rejects_the_ledger_line(self):
        entries = [
            {
                "entry_id": "entry-001",
                "sample_id": "sample-A",
                "event_at": "2026-08-16T09:00:00Z",
                "arrived_at": "2026-08-16T09:05:00Z",
                "payload_digest": "1" * 64,
            }
        ]
        with tempfile.TemporaryDirectory() as temporary:
            bundle = load_bundle(write_bundle(Path(temporary), entries))
            receipt = verify_bundle(bundle, "0.1.0")

        self.assert_codes(receipt, ["POST_CUTOFF_EVENT"])
        self.assertEqual(receipt["violations"][0]["entry_index"], 1)

    def test_unknown_sample_rejects_the_ledger_line(self):
        entries = [
            {
                "entry_id": "entry-001",
                "sample_id": "sample-Z",
                "event_at": "2026-08-10T09:00:00Z",
                "arrived_at": "2026-08-10T09:05:00Z",
                "payload_digest": "1" * 64,
            }
        ]
        with tempfile.TemporaryDirectory() as temporary:
            bundle = load_bundle(write_bundle(Path(temporary), entries))
            receipt = verify_bundle(bundle, "0.1.0")

        self.assert_codes(receipt, ["UNKNOWN_SAMPLE"])
        self.assertEqual(receipt["violations"][0]["entry_index"], 1)

    def test_later_logical_duplicate_rejects_only_the_third_line(self):
        entries = [
            {
                "entry_id": "entry-001",
                "sample_id": "sample-A",
                "event_at": "2026-08-10T09:00:00Z",
                "arrived_at": "2026-08-10T09:05:00Z",
                "payload_digest": "1" * 64,
            },
            {
                "entry_id": "entry-002",
                "sample_id": "sample-B",
                "event_at": "2026-08-11T09:00:00Z",
                "arrived_at": "2026-08-11T09:05:00Z",
                "payload_digest": "2" * 64,
            },
            {
                "entry_id": "entry-003",
                "sample_id": "sample-B",
                "event_at": "2026-08-11T09:00:00Z",
                "arrived_at": "2026-08-11T10:00:00Z",
                "payload_digest": "3" * 64,
            },
        ]
        with tempfile.TemporaryDirectory() as temporary:
            bundle = load_bundle(write_bundle(Path(temporary), entries))
            receipt = verify_bundle(bundle, "0.1.0")

        self.assert_codes(receipt, ["DUPLICATE_ENTRY"])
        self.assertEqual(receipt["violations"][0]["entry_index"], 3)

    def test_repeated_entry_id_rejects_only_the_later_distinct_logical_key(self):
        entries = [
            {
                "entry_id": "entry-001",
                "sample_id": "sample-A",
                "event_at": "2026-08-10T09:00:00Z",
                "arrived_at": "2026-08-10T09:05:00Z",
                "payload_digest": "1" * 64,
            },
            {
                "entry_id": "entry-001",
                "sample_id": "sample-B",
                "event_at": "2026-08-11T09:00:00Z",
                "arrived_at": "2026-08-11T09:05:00Z",
                "payload_digest": "2" * 64,
            },
        ]
        with tempfile.TemporaryDirectory() as temporary:
            bundle = load_bundle(write_bundle(Path(temporary), entries))
            receipt = verify_bundle(bundle, "0.1.0")

        self.assert_codes(receipt, ["DUPLICATE_ENTRY"])
        self.assertEqual(
            receipt["violations"],
            [
                {
                    "entry_index": 2,
                    "sample_id": "sample-B",
                    "code": "DUPLICATE_ENTRY",
                }
            ],
        )
        self.assertEqual(receipt["accepted_count"], 1)
        self.assertEqual(receipt["rejected_count"], 1)

    def test_payload_mutation_after_digest_calculation_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle_dir = write_bundle(Path(temporary))
            ledger_path = bundle_dir / "ledger.jsonl"
            rows = self.read_ledger(ledger_path)
            rows[0]["payload_digest"] = "9" * 64
            self.write_ledger(ledger_path, rows)
            receipt = verify_bundle(load_bundle(bundle_dir), "0.1.0")

        self.assert_codes(receipt, ["DIGEST_MISMATCH"])
        self.assertEqual(
            receipt["violations"][0],
            {
                "entry_index": 1,
                "sample_id": "sample-A",
                "code": "DIGEST_MISMATCH",
            },
        )

    def test_recalculated_entry_with_wrong_previous_digest_is_a_ledger_gap(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle_dir = write_bundle(Path(temporary))
            ledger_path = bundle_dir / "ledger.jsonl"
            rows = self.read_ledger(ledger_path)
            rows[1]["previous_entry_digest"] = "0" * 64
            unsigned = {
                key: value for key, value in rows[1].items() if key != "entry_digest"
            }
            rows[1]["entry_digest"] = sha256_json(unsigned)
            self.write_ledger(ledger_path, rows)
            receipt = verify_bundle(load_bundle(bundle_dir), "0.1.0")

        self.assert_codes(receipt, ["LEDGER_GAP"])
        self.assertEqual(receipt["violations"][0]["entry_index"], 2)

    def test_global_snapshot_mismatch_does_not_change_entry_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle_dir = write_bundle(Path(temporary))
            plan_path = bundle_dir / "plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            plan["snapshot_digest"] = "0" * 64
            plan_path.write_bytes(canonical_json_bytes(plan) + b"\n")
            receipt = verify_bundle(load_bundle(bundle_dir), "0.1.0")

        self.assert_codes(receipt, ["DIGEST_MISMATCH"])
        self.assertEqual(
            receipt["violations"],
            [
                {
                    "entry_index": None,
                    "sample_id": None,
                    "code": "DIGEST_MISMATCH",
                }
            ],
        )
        self.assertEqual(receipt["accepted_count"], 2)
        self.assertEqual(receipt["rejected_count"], 0)

    def test_equivalent_timezone_strings_share_one_logical_duplicate_key(self):
        entries = [
            {
                "entry_id": "entry-001",
                "sample_id": "sample-A",
                "event_at": "2026-08-10T09:00:00Z",
                "arrived_at": "2026-08-10T09:05:00Z",
                "payload_digest": "1" * 64,
            },
            {
                "entry_id": "entry-002",
                "sample_id": "sample-A",
                "event_at": "2026-08-10T17:00:00+08:00",
                "arrived_at": "2026-08-10T17:06:00+08:00",
                "payload_digest": "2" * 64,
            },
        ]
        with tempfile.TemporaryDirectory() as temporary:
            bundle = load_bundle(write_bundle(Path(temporary), entries))
            receipt = verify_bundle(bundle, "0.1.0")

        self.assert_codes(receipt, ["DUPLICATE_ENTRY"])
        self.assertEqual(receipt["violations"][0]["entry_index"], 2)

    def test_declared_digest_change_breaks_that_line_and_the_following_link(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle_dir = write_bundle(Path(temporary))
            ledger_path = bundle_dir / "ledger.jsonl"
            rows = self.read_ledger(ledger_path)
            rows[0]["entry_digest"] = "f" * 64
            self.write_ledger(ledger_path, rows)
            receipt = verify_bundle(load_bundle(bundle_dir), "0.1.0")

        self.assert_codes(receipt, ["DIGEST_MISMATCH", "LEDGER_GAP"])
        self.assertEqual(
            [item["entry_index"] for item in receipt["violations"]],
            [1, 2],
        )
        self.assertEqual(
            receipt["ledger_tip_digest"],
            "57fe707aee812f943b9c4e76ac2428cef9af50d37e4bf98938fee92a783d0980",
        )
        self.assertEqual(receipt["accepted_count"], 0)
        self.assertEqual(receipt["rejected_count"], 2)

    def test_one_entry_can_have_multiple_alphabetically_sorted_codes(self):
        entries = [
            {
                "entry_id": "entry-001",
                "sample_id": "sample-Z",
                "event_at": "2026-08-16T09:00:00Z",
                "arrived_at": "2026-08-16T09:05:00Z",
                "payload_digest": "1" * 64,
            }
        ]
        with tempfile.TemporaryDirectory() as temporary:
            bundle_dir = write_bundle(Path(temporary), entries)
            ledger_path = bundle_dir / "ledger.jsonl"
            rows = self.read_ledger(ledger_path)
            rows[0]["entry_digest"] = "f" * 64
            self.write_ledger(ledger_path, rows)
            receipt = verify_bundle(load_bundle(bundle_dir), "0.1.0")

        self.assert_codes(
            receipt,
            ["DIGEST_MISMATCH", "POST_CUTOFF_EVENT", "UNKNOWN_SAMPLE"],
        )
        self.assertEqual(receipt["accepted_count"], 0)
        self.assertEqual(receipt["rejected_count"], 1)
        for violation in receipt["violations"]:
            self.assertEqual(
                set(violation),
                {"entry_index", "sample_id", "code"},
            )
            self.assertTrue(
                {"payload_digest", "event_at", "arrived_at"}.isdisjoint(violation)
            )

    def test_first_occurrence_is_accepted_and_later_duplicates_are_rejected(self):
        entries = [
            {
                "entry_id": f"entry-00{index}",
                "sample_id": "sample-A",
                "event_at": "2026-08-10T09:00:00Z",
                "arrived_at": f"2026-08-10T09:0{index}:00Z",
                "payload_digest": str(index) * 64,
            }
            for index in (1, 2, 3)
        ]
        with tempfile.TemporaryDirectory() as temporary:
            bundle = load_bundle(write_bundle(Path(temporary), entries))
            receipt = verify_bundle(bundle, "0.1.0")

        self.assert_codes(receipt, ["DUPLICATE_ENTRY", "DUPLICATE_ENTRY"])
        self.assertEqual(
            [item["entry_index"] for item in receipt["violations"]],
            [2, 3],
        )
        self.assertEqual(receipt["accepted_count"], 1)
        self.assertEqual(receipt["rejected_count"], 2)

    def test_empty_ledger_is_eligible_with_genesis_tip_and_zero_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = load_bundle(write_bundle(Path(temporary), []))
            receipt = verify_bundle(bundle, "0.1.0")

        self.assertEqual(receipt["status"], "eligible")
        self.assertEqual(receipt["ledger_tip_digest"], "GENESIS")
        self.assertEqual(receipt["accepted_count"], 0)
        self.assertEqual(receipt["rejected_count"], 0)
        self.assertEqual(receipt["violations"], [])

    def test_tool_version_changes_the_receipt_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = load_bundle(write_bundle(Path(temporary)))
            first = verify_bundle(bundle, "0.2.0")
            second = verify_bundle(bundle, "0.2.1")

        self.assertEqual(first["tool_version"], "0.2.0")
        self.assertEqual(second["tool_version"], "0.2.1")
        self.assertNotEqual(first["receipt_digest"], second["receipt_digest"])
