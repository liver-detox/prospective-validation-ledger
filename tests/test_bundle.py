import json
import tempfile
import unittest
from pathlib import Path

from prospective_validation_ledger.bundle import StructuralError, load_bundle
from tests.support import write_bundle


class BundleLoaderTest(unittest.TestCase):
    def test_valid_bundle_loads_three_inputs_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle_dir = write_bundle(Path(temporary))
            (bundle_dir / "ignored.txt").write_text("not read", encoding="utf-8")
            bundle = load_bundle(bundle_dir)
            self.assertEqual(bundle.plan.experiment_id, "SYNTHETIC-DEMO-001")
            self.assertEqual(len(bundle.entries), 2)
            self.assertEqual(bundle.entries[0].line_number, 1)

    def test_duplicate_json_key_is_structurally_invalid(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle_dir = write_bundle(Path(temporary))
            (bundle_dir / "plan.json").write_text(
                '{"schema_version":"1","schema_version":"1"}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(StructuralError, "duplicate JSON key"):
                load_bundle(bundle_dir)

    def test_naive_timestamp_is_structurally_invalid(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle_dir = write_bundle(Path(temporary))
            path = bundle_dir / "plan.json"
            plan = json.loads(path.read_text(encoding="utf-8"))
            plan["as_of"] = "2026-08-15T00:00:00"
            path.write_text(json.dumps(plan) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(StructuralError, "timezone"):
                load_bundle(bundle_dir)

    def test_blank_ledger_line_is_structurally_invalid(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle_dir = write_bundle(Path(temporary))
            path = bundle_dir / "ledger.jsonl"
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(StructuralError, "blank ledger line"):
                load_bundle(bundle_dir)

    def test_structural_violations_are_rejected_without_echoing_input(self):
        def remove_plan(bundle_dir: Path) -> str:
            (bundle_dir / "plan.json").unlink()
            return "MISSING-REQUIRED-FILE-INJECTED"

        def add_bom(bundle_dir: Path) -> str:
            (bundle_dir / "plan.json").write_bytes(
                b'\xef\xbb\xbf{"marker":"BOM-INJECTED"}'
            )
            return "BOM-INJECTED"

        def write_invalid_utf8(bundle_dir: Path) -> str:
            (bundle_dir / "snapshot.json").write_bytes(
                b"INVALID-UTF8-INJECTED:\xff"
            )
            return "INVALID-UTF8-INJECTED"

        def write_truncated_json(bundle_dir: Path) -> str:
            (bundle_dir / "plan.json").write_text(
                '{"marker":"TRUNCATED-JSON-INJECTED"', encoding="utf-8"
            )
            return "TRUNCATED-JSON-INJECTED"

        def write_invalid_jsonl(bundle_dir: Path) -> str:
            (bundle_dir / "ledger.jsonl").write_text(
                '{"marker":"JSONL-INVALID-INJECTED"\n', encoding="utf-8"
            )
            return "JSONL-INVALID-INJECTED"

        def write_non_object_plan(bundle_dir: Path) -> str:
            (bundle_dir / "plan.json").write_text(
                '["NON-OBJECT-PLAN-INJECTED"]\n', encoding="utf-8"
            )
            return "NON-OBJECT-PLAN-INJECTED"

        def write_non_object_snapshot(bundle_dir: Path) -> str:
            (bundle_dir / "snapshot.json").write_text(
                '["NON-OBJECT-SNAPSHOT-INJECTED"]\n', encoding="utf-8"
            )
            return "NON-OBJECT-SNAPSHOT-INJECTED"

        def add_unknown_field(bundle_dir: Path) -> str:
            path = bundle_dir / "plan.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["unknown_field"] = "UNKNOWN-FIELD-INJECTED"
            path.write_text(json.dumps(value) + "\n", encoding="utf-8")
            return "UNKNOWN-FIELD-INJECTED"

        def change_schema_version(bundle_dir: Path) -> str:
            path = bundle_dir / "plan.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["schema_version"] = "UNSUPPORTED-SCHEMA-INJECTED"
            path.write_text(json.dumps(value) + "\n", encoding="utf-8")
            return "UNSUPPORTED-SCHEMA-INJECTED"

        def make_sample_ids_unsorted(bundle_dir: Path) -> str:
            path = bundle_dir / "plan.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["sample_ids"] = ["z-UNSORTED-INJECTED", "a-UNSORTED-INJECTED"]
            path.write_text(json.dumps(value) + "\n", encoding="utf-8")
            return "z-UNSORTED-INJECTED"

        def duplicate_sample_ids(bundle_dir: Path) -> str:
            path = bundle_dir / "plan.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["sample_ids"] = ["DUPLICATE-INJECTED", "DUPLICATE-INJECTED"]
            path.write_text(json.dumps(value) + "\n", encoding="utf-8")
            return "DUPLICATE-INJECTED"

        def make_record_count_boolean(bundle_dir: Path) -> str:
            path = bundle_dir / "snapshot.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["record_count"] = True
            path.write_text(json.dumps(value) + "\n", encoding="utf-8")
            return "True"

        def write_invalid_digest(bundle_dir: Path) -> str:
            path = bundle_dir / "plan.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["snapshot_digest"] = "INVALID-DIGEST-INJECTED"
            path.write_text(json.dumps(value) + "\n", encoding="utf-8")
            return "INVALID-DIGEST-INJECTED"

        def null_payload_digest(bundle_dir: Path) -> str:
            path = bundle_dir / "ledger.jsonl"
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows[0]["payload_digest"] = None
            path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            return "None"

        def reverse_arrival(bundle_dir: Path) -> str:
            path = bundle_dir / "ledger.jsonl"
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows[0]["arrived_at"] = "2026-08-10T08:00:00Z"
            path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            return "2026-08-10T08:00:00Z"

        cases = (
            ("missing required file", remove_plan),
            ("UTF-8 byte-order mark", add_bom),
            ("invalid UTF-8 bytes", write_invalid_utf8),
            ("truncated or syntactically invalid JSON object", write_truncated_json),
            ("invalid JSON on one JSONL line", write_invalid_jsonl),
            ("non-object plan", write_non_object_plan),
            ("non-object snapshot", write_non_object_snapshot),
            ("unknown field", add_unknown_field),
            ("unsupported schema version", change_schema_version),
            ("unsorted sample IDs", make_sample_ids_unsorted),
            ("duplicate sample IDs", duplicate_sample_ids),
            ("Boolean record_count", make_record_count_boolean),
            ("invalid digest text", write_invalid_digest),
            ("payload_digest set to null", null_payload_digest),
            ("arrival earlier than event", reverse_arrival),
        )
        for name, mutate in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                bundle_dir = write_bundle(Path(temporary))
                injected = mutate(bundle_dir)
                with self.assertRaises(StructuralError) as caught:
                    load_bundle(bundle_dir)
                self.assertNotIn(injected, str(caught.exception))

    def test_missing_payload_digest_loads_successfully(self):
        entries = [
            {
                "entry_id": "entry-without-payload",
                "sample_id": "sample-A",
                "event_at": "2026-08-10T09:00:00Z",
                "arrived_at": "2026-08-10T09:05:00Z",
            }
        ]
        with tempfile.TemporaryDirectory() as temporary:
            bundle = load_bundle(write_bundle(Path(temporary), entries))
        self.assertNotIn("payload_digest", bundle.entries[0].raw)

    def test_valid_field_digest_loads_successfully(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle_dir = write_bundle(Path(temporary))
            path = bundle_dir / "snapshot.json"
            snapshot = json.loads(path.read_text(encoding="utf-8"))
            snapshot["field_digest"] = "a" * 64
            path.write_text(json.dumps(snapshot) + "\n", encoding="utf-8")
            bundle = load_bundle(bundle_dir)
        self.assertEqual(bundle.snapshot.raw["field_digest"], "a" * 64)

    def test_invalid_field_digest_is_structurally_invalid(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle_dir = write_bundle(Path(temporary))
            path = bundle_dir / "snapshot.json"
            snapshot = json.loads(path.read_text(encoding="utf-8"))
            snapshot["field_digest"] = "INVALID-FIELD-DIGEST-INJECTED"
            path.write_text(json.dumps(snapshot) + "\n", encoding="utf-8")
            with self.assertRaises(StructuralError) as caught:
                load_bundle(bundle_dir)
        self.assertNotIn("INVALID-FIELD-DIGEST-INJECTED", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
