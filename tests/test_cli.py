import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from prospective_validation_ledger.cli import main
from tests.support import write_bundle


class CliTest(unittest.TestCase):
    def test_eligible_bundle_writes_one_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = write_bundle(root)
            output = root / "receipt.json"
            self.assertEqual(main(["verify", str(bundle), "--out", str(output)]), 0)
            receipt = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "eligible")
            self.assertTrue(output.read_bytes().endswith(b"\n"))

    def test_structural_error_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = write_bundle(root)
            (bundle / "plan.json").write_text("not json", encoding="utf-8")
            output = root / "receipt.json"
            output.write_bytes(b"existing\n")
            self.assertNotEqual(
                main(["verify", str(bundle), "--out", str(output)]),
                0,
            )
            self.assertEqual(output.read_bytes(), b"existing\n")

    def test_output_cannot_replace_an_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = write_bundle(root)
            plan = bundle / "plan.json"
            original = plan.read_bytes()
            self.assertNotEqual(
                main(["verify", str(bundle), "--out", str(plan)]),
                0,
            )
            self.assertEqual(plan.read_bytes(), original)

    def test_output_symlink_is_replaced_without_touching_its_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = write_bundle(root)
            target = root / "unrelated.txt"
            target.write_bytes(b"sentinel\n")
            output = root / "receipt.json"
            output.symlink_to(target.name)

            self.assertEqual(main(["verify", str(bundle), "--out", str(output)]), 0)

            self.assertEqual(target.read_bytes(), b"sentinel\n")
            self.assertFalse(output.is_symlink())
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8"))["status"],
                "eligible",
            )

    def test_audit_violation_writes_rejected_receipt_and_returns_nonzero(self):
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
            root = Path(temporary)
            bundle = write_bundle(root, entries)
            output = root / "receipt.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = main(["verify", str(bundle), "--out", str(output)])

            self.assertNotEqual(result, 0)
            self.assertEqual(stdout.getvalue(), "rejected\n")
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8"))["status"], "rejected"
            )

    def test_missing_output_parent_writes_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = write_bundle(root)
            output = root / "missing" / "receipt.json"

            self.assertNotEqual(
                main(["verify", str(bundle), "--out", str(output)]),
                0,
            )
            self.assertFalse(output.exists())

    def test_directory_output_fails_without_deleting_the_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = write_bundle(root)
            output = root / "receipt-directory"
            output.mkdir()

            self.assertNotEqual(
                main(["verify", str(bundle), "--out", str(output)]),
                0,
            )
            self.assertTrue(output.is_dir())

    def test_repeated_verification_writes_identical_canonical_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = write_bundle(root)
            output = root / "receipt.json"

            self.assertEqual(main(["verify", str(bundle), "--out", str(output)]), 0)
            first = output.read_bytes()
            self.assertEqual(main(["verify", str(bundle), "--out", str(output)]), 0)
            self.assertEqual(output.read_bytes(), first)

    def test_eligible_stdout_is_only_the_status(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = write_bundle(root)
            output = root / "receipt.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = main(["verify", str(bundle), "--out", str(output)])

            self.assertEqual(result, 0)
            self.assertEqual(stdout.getvalue(), "eligible\n")

    def test_structural_failure_stderr_does_not_echo_input_text_or_digest(self):
        arbitrary_text = "untrusted-input-text"
        synthetic_digest = "a" * 64
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = write_bundle(root)
            (bundle / "plan.json").write_text(
                f'{{"note":"{arbitrary_text}","digest":"{synthetic_digest}"}}',
                encoding="utf-8",
            )
            output = root / "receipt.json"
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                result = main(["verify", str(bundle), "--out", str(output)])

            self.assertNotEqual(result, 0)
            self.assertNotIn(arbitrary_text, stderr.getvalue())
            self.assertNotIn(synthetic_digest, stderr.getvalue())

    def test_surrogate_input_preserves_output_and_has_controlled_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = write_bundle(root)
            plan_path = bundle / "plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            plan["rule_version"] = "\ud800"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            output = root / "receipt.json"
            output.write_bytes(b"sentinel\n")
            stdout = io.StringIO()
            stderr = io.StringIO()

            with (
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                result = main(["verify", str(bundle), "--out", str(output)])

            self.assertNotEqual(result, 0)
            self.assertEqual(output.read_bytes(), b"sentinel\n")
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(stderr.getvalue(), "error: invalid Unicode input\n")
            self.assertNotIn("Traceback", stderr.getvalue())
            self.assertNotIn("\\ud800", stderr.getvalue())

    def test_timestamp_overflow_preserves_output_and_has_controlled_error(self):
        injected = "9999-12-31T23:59:59-23:59"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = write_bundle(root)
            plan_path = bundle / "plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            plan["frozen_at"] = injected
            plan_path.write_text(json.dumps(plan) + "\n", encoding="utf-8")
            output = root / "receipt.json"
            output.write_bytes(b"sentinel\n")
            stdout = io.StringIO()
            stderr = io.StringIO()

            with (
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                result = main(["verify", str(bundle), "--out", str(output)])

            self.assertNotEqual(result, 0)
            self.assertEqual(output.read_bytes(), b"sentinel\n")
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(stderr.getvalue(), "error: invalid bundle structure\n")
            self.assertNotIn("Traceback", stderr.getvalue())
            self.assertNotIn(injected, stderr.getvalue())

    def test_symlink_loop_preserves_output_and_has_controlled_path_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            loop_a = root / "loop-a"
            loop_b = root / "loop-b"
            loop_a.symlink_to(loop_b.name)
            loop_b.symlink_to(loop_a.name)
            output = root / "receipt.json"
            output.write_bytes(b"sentinel\n")
            stdout = io.StringIO()
            stderr = io.StringIO()

            with (
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                result = main(["verify", str(loop_a), "--out", str(output)])

            self.assertNotEqual(result, 0)
            self.assertEqual(output.read_bytes(), b"sentinel\n")
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn(
                stderr.getvalue(),
                (
                    "error: unable to read or write requested path\n",
                    "error: invalid bundle structure\n",
                ),
            )
            self.assertNotIn("Traceback", stderr.getvalue())
            self.assertNotIn(str(loop_a), stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
