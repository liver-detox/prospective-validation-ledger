import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from prospective_validation_ledger.bundle import load_bundle
from prospective_validation_ledger.cli import main


def _write_draft(root: Path, *, late_arrival: bool = False) -> Path:
    draft = root / "draft"
    draft.mkdir(parents=True)
    snapshot = {
        "schema_version": "1",
        "as_of": "2026-08-15T00:00:00Z",
        "record_count": 2,
        "source_digest": "0" * 64,
    }
    plan = {
        "schema_version": "1",
        "experiment_id": "SYNTHETIC-DEMO-001",
        "rule_version": "1",
        "frozen_at": "2026-08-01T00:00:00Z",
        "as_of": snapshot["as_of"],
        "sample_ids": ["sample-A", "sample-B"],
    }
    entries = [
        {
            "entry_id": "entry-001",
            "sample_id": "sample-A",
            "event_at": "2026-08-10T09:00:00Z",
            "arrived_at": (
                "2026-08-16T09:00:00Z"
                if late_arrival
                else "2026-08-10T09:05:00Z"
            ),
            "payload_digest": "1" * 64,
        },
        {
            "entry_id": "entry-002",
            "sample_id": "sample-B",
            "event_at": "2026-08-11T09:00:00Z",
            "arrived_at": "2026-08-11T09:05:00Z",
            "payload_digest": "2" * 64,
        },
    ]
    (draft / "plan.json").write_text(json.dumps(plan) + "\n", encoding="utf-8")
    (draft / "snapshot.json").write_text(
        json.dumps(snapshot) + "\n", encoding="utf-8"
    )
    (draft / "ledger.jsonl").write_text(
        "".join(json.dumps(entry) + "\n" for entry in entries), encoding="utf-8"
    )
    return draft


class CreateCommandTest(unittest.TestCase):
    def test_late_arrival_example_is_generated_and_rejected_only_for_lateness(self):
        repository = Path(__file__).parents[1]
        draft = repository / "examples" / "SYNTHETIC_late_arrival_draft"
        expected_bundle = repository / "examples" / "SYNTHETIC_late_arrival"
        expected_receipt = json.loads(
            (
                repository / "examples" / "SYNTHETIC_late_arrival_expected_receipt.json"
            ).read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "bundle"
            receipt_path = root / "receipt.json"

            self.assertEqual(main(["create", str(draft), "--out", str(bundle)]), 0)
            for filename in ("plan.json", "snapshot.json", "ledger.jsonl"):
                self.assertEqual(
                    (bundle / filename).read_bytes(),
                    (expected_bundle / filename).read_bytes(),
                )

            self.assertNotEqual(
                main(["verify", str(bundle), "--out", str(receipt_path)]), 0
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

        self.assertEqual(receipt, expected_receipt)
        self.assertEqual(receipt["accepted_count"], 1)
        self.assertEqual(receipt["rejected_count"], 1)
        self.assertEqual(
            receipt["violations"],
            [{"entry_index": 1, "sample_id": "sample-A", "code": "LATE_ARRIVAL"}],
        )

    def test_create_makes_an_eligible_bundle_with_generated_digests(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            draft = _write_draft(root)
            bundle = root / "bundle"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = main(["create", str(draft), "--out", str(bundle)])

            self.assertEqual(result, 0)
            self.assertEqual(stdout.getvalue(), "created\n")
            self.assertEqual(
                json.loads((bundle / "plan.json").read_text(encoding="utf-8"))["snapshot_digest"],
                "5f015e2aafd94d2f2e6525f245a45bb2fa68019996ab7d3143cd48b59e420edf",
            )
            rows = [
                json.loads(line)
                for line in (bundle / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(rows[0]["previous_entry_digest"], "GENESIS")
            self.assertEqual(
                rows[0]["entry_digest"],
                "b427efca9957038edbad4b33fbb24296903fd4c80c34009400ad8f1ff03f43e8",
            )
            self.assertEqual(rows[1]["previous_entry_digest"], rows[0]["entry_digest"])
            self.assertEqual(
                rows[1]["entry_digest"],
                "57fe707aee812f943b9c4e76ac2428cef9af50d37e4bf98938fee92a783d0980",
            )
            self.assertEqual(load_bundle(bundle).plan.experiment_id, "SYNTHETIC-DEMO-001")

            receipt = root / "receipt.json"
            self.assertEqual(main(["verify", str(bundle), "--out", str(receipt)]), 0)
            self.assertEqual(json.loads(receipt.read_text(encoding="utf-8"))["status"], "eligible")

    def test_create_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first_draft = _write_draft(root / "first")
            second_draft = _write_draft(root / "second")
            first_bundle = root / "first-bundle"
            second_bundle = root / "second-bundle"

            self.assertEqual(main(["create", str(first_draft), "--out", str(first_bundle)]), 0)
            self.assertEqual(main(["create", str(second_draft), "--out", str(second_bundle)]), 0)

            for filename in ("plan.json", "snapshot.json", "ledger.jsonl"):
                self.assertEqual(
                    (first_bundle / filename).read_bytes(),
                    (second_bundle / filename).read_bytes(),
                )

    def test_create_never_replaces_an_existing_output_or_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            draft = _write_draft(root)
            for name in ("file", "directory", "symlink"):
                with self.subTest(name=name):
                    output = root / name
                    if name == "file":
                        output.write_bytes(b"sentinel\n")
                    elif name == "directory":
                        output.mkdir()
                    else:
                        target = root / "target"
                        target.write_bytes(b"sentinel\n")
                        output.symlink_to(target.name)

                    self.assertNotEqual(
                        main(["create", str(draft), "--out", str(output)]), 0
                    )
                    self.assertTrue(output.exists() or output.is_symlink())
                    if name == "file":
                        self.assertEqual(output.read_bytes(), b"sentinel\n")
                    elif name == "directory":
                        self.assertTrue(output.is_dir())
                    else:
                        self.assertTrue(output.is_symlink())
                        self.assertEqual(target.read_bytes(), b"sentinel\n")

    def test_create_preserves_a_directory_created_during_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            draft = _write_draft(root)
            output = root / "bundle"
            raced_inode = None
            real_mkdir = Path.mkdir

            def create_before_mkdir(path, *args, **kwargs):
                nonlocal raced_inode
                if path == output and raced_inode is None:
                    real_mkdir(path)
                    raced_inode = path.stat().st_ino
                return real_mkdir(path, *args, **kwargs)

            with mock.patch.object(Path, "mkdir", create_before_mkdir):
                result = main(["create", str(draft), "--out", str(output)])

            self.assertNotEqual(result, 0)
            self.assertIsNotNone(raced_inode)
            self.assertTrue(output.is_dir())
            self.assertEqual(output.stat().st_ino, raced_inode)

    def test_create_cleans_its_unchanged_files_after_publication_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            draft = _write_draft(root)
            output = root / "bundle"
            failed_path = output / "snapshot.json"
            real_open = Path.open

            def fail_second_output(path, *args, **kwargs):
                if path == failed_path:
                    raise OSError("injected write failure")
                return real_open(path, *args, **kwargs)

            with mock.patch.object(Path, "open", fail_second_output):
                result = main(["create", str(draft), "--out", str(output)])

            self.assertNotEqual(result, 0)
            self.assertFalse(output.exists())
            self.assertFalse(output.is_symlink())

    def test_invalid_draft_has_no_output_and_does_not_echo_input(self):
        injected = "UNTRUSTED-DRAFT-TEXT"
        cases = (
            ("generated plan digest", lambda draft: _add_plan_digest(draft)),
            ("generated entry digest", lambda draft: _add_entry_digest(draft)),
            ("unknown field", lambda draft: _add_unknown_field(draft, injected)),
            ("missing field", _remove_experiment_id),
            ("duplicate key", lambda draft: _write_duplicate_key(draft, injected)),
        )
        for name, mutate in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                draft = _write_draft(root)
                mutate(draft)
                output = root / "bundle"
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    self.assertNotEqual(
                        main(["create", str(draft), "--out", str(output)]), 0
                    )
                self.assertFalse(output.exists())
                self.assertFalse(output.is_symlink())
                self.assertNotIn(injected, stderr.getvalue())

    def test_create_allows_a_semantic_violation_that_verify_rejects(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            draft = _write_draft(root, late_arrival=True)
            bundle = root / "bundle"
            receipt = root / "receipt.json"

            self.assertEqual(main(["create", str(draft), "--out", str(bundle)]), 0)
            self.assertNotEqual(main(["verify", str(bundle), "--out", str(receipt)]), 0)
            self.assertEqual(json.loads(receipt.read_text(encoding="utf-8"))["status"], "rejected")


def _add_plan_digest(draft: Path) -> None:
    path = draft / "plan.json"
    plan = json.loads(path.read_text(encoding="utf-8"))
    plan["snapshot_digest"] = "0" * 64
    path.write_text(json.dumps(plan) + "\n", encoding="utf-8")


def _add_entry_digest(draft: Path) -> None:
    path = draft / "ledger.jsonl"
    entries = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    entries[0]["entry_digest"] = "0" * 64
    path.write_text("".join(json.dumps(entry) + "\n" for entry in entries), encoding="utf-8")


def _add_unknown_field(draft: Path, injected: str) -> None:
    path = draft / "plan.json"
    plan = json.loads(path.read_text(encoding="utf-8"))
    plan["unknown"] = injected
    path.write_text(json.dumps(plan) + "\n", encoding="utf-8")


def _remove_experiment_id(draft: Path) -> None:
    path = draft / "plan.json"
    plan = json.loads(path.read_text(encoding="utf-8"))
    del plan["experiment_id"]
    path.write_text(json.dumps(plan) + "\n", encoding="utf-8")


def _write_duplicate_key(draft: Path, injected: str) -> None:
    (draft / "plan.json").write_text(
        '{"schema_version":"1","schema_version":"%s"}\n' % injected,
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
