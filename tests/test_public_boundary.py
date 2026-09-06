import ast
import unittest
from pathlib import Path


class PublicBoundaryTest(unittest.TestCase):
    def test_source_has_no_network_or_process_imports(self):
        blocked = {"http", "requests", "httpx", "socket", "subprocess"}
        source = Path(__file__).parents[1] / "src"
        found = set()
        for path in source.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    found.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    found.add(node.module.split(".")[0])
        self.assertEqual(found & blocked, set())

    def test_examples_are_visibly_synthetic_and_have_no_private_path(self):
        root = Path(__file__).parents[1]
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (root / "examples").rglob("*")
            if path.is_file()
        )
        self.assertIn("SYNTHETIC", text)
        self.assertNotIn("/Users/", text)

    def test_packaging_contract_lists_every_synthetic_example(self):
        root = Path(__file__).parents[1]
        package_config = (root / "pyproject.toml").read_text(encoding="utf-8")
        manifest = (root / "MANIFEST.in").read_text(encoding="utf-8")
        fixtures = sorted(
            path.relative_to(root).as_posix()
            for path in (root / "examples").rglob("*")
            if path.is_file()
        )

        self.assertIn("recursive-include examples *.json *.jsonl", manifest)
        for fixture in fixtures:
            self.assertIn(fixture, package_config)


if __name__ == "__main__":
    unittest.main()
