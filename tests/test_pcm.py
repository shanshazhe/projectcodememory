from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "pcm.py"
SPEC = importlib.util.spec_from_file_location("pcm", SCRIPT)
assert SPEC and SPEC.loader
pcm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pcm)


class ProjectCodeMemoryCleanupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = (Path(self.temporary.name) / "repo").resolve()
        self.root.mkdir()

    def capture(self, function, *args):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = function(*args)
        return result, stdout.getvalue(), stderr.getvalue()

    def save(self, identifier: str, keyword: str) -> Path:
        source = self.root / f"{identifier}.py"
        source.write_text(f"VALUE = {identifier!r}\n", encoding="utf-8")
        self.capture(pcm.init_memory, self.root, False)
        draft = self.root / pcm.MEMORY_DIR / "drafts" / f"{identifier}.json"
        draft.write_text(
            json.dumps(
                {
                    "id": identifier,
                    "keywords": [keyword],
                    "paths": [source.name],
                    "symbols": [],
                    "summary": f"Memory for {identifier}",
                    "facts": [f"Fact for {identifier}"],
                    "flows": [],
                    "invariants": [],
                    "side_effects": [],
                    "verification": ["Unit fixture"],
                }
            ),
            encoding="utf-8",
        )
        result, _, _ = self.capture(pcm.save_record, self.root, str(draft))
        self.assertEqual(0, result)
        return source

    def record(self, identifier: str) -> Path:
        return self.root / pcm.MEMORY_DIR / "records" / f"{identifier}.json"

    def index_text(self) -> str:
        return (self.root / pcm.MEMORY_DIR / "index.tsv").read_text(encoding="utf-8")

    def test_query_prunes_record_when_source_changes(self) -> None:
        source = self.save("changed", "changed-keyword")
        source.write_text("VALUE = 'new'\n", encoding="utf-8")

        result, stdout, _ = self.capture(pcm.query_memory, self.root, "changed-keyword", 3)

        self.assertEqual(0, result)
        self.assertIn("STALE changed changed.py:changed", stdout)
        self.assertIn("PRUNED changed", stdout)
        self.assertFalse(self.record("changed").exists())
        self.assertNotIn("changed\t", self.index_text())
        _, second_stdout, _ = self.capture(pcm.query_memory, self.root, "changed-keyword", 3)
        self.assertIn("EMPTY_INDEX", second_stdout)

    def test_query_prunes_record_when_source_is_missing(self) -> None:
        source = self.save("missing", "missing-keyword")
        source.unlink()

        result, stdout, _ = self.capture(pcm.query_memory, self.root, "missing-keyword", 3)

        self.assertEqual(0, result)
        self.assertIn("STALE missing missing.py:missing", stdout)
        self.assertIn("PRUNED missing", stdout)
        self.assertFalse(self.record("missing").exists())
        self.assertNotIn("missing\t", self.index_text())

    def test_query_prunes_invalid_record(self) -> None:
        self.save("broken", "broken-keyword")
        self.record("broken").write_text("{not-json", encoding="utf-8")

        result, stdout, _ = self.capture(pcm.query_memory, self.root, "broken-keyword", 3)

        self.assertEqual(0, result)
        self.assertIn("ERROR broken", stdout)
        self.assertIn("PRUNED broken", stdout)
        self.assertFalse(self.record("broken").exists())
        self.assertNotIn("broken\t", self.index_text())

    def test_query_prunes_non_utf8_record(self) -> None:
        self.save("binary", "binary-keyword")
        self.record("binary").write_bytes(b"\xff")

        result, stdout, _ = self.capture(pcm.query_memory, self.root, "binary-keyword", 3)

        self.assertEqual(0, result)
        self.assertIn("ERROR binary", stdout)
        self.assertIn("PRUNED binary", stdout)
        self.assertFalse(self.record("binary").exists())
        self.assertNotIn("binary\t", self.index_text())

    def test_query_removes_index_entry_for_missing_record(self) -> None:
        self.save("orphan", "orphan-keyword")
        self.record("orphan").unlink()

        result, stdout, _ = self.capture(pcm.query_memory, self.root, "orphan-keyword", 3)

        self.assertEqual(0, result)
        self.assertIn("ERROR orphan", stdout)
        self.assertIn("PRUNED orphan", stdout)
        self.assertNotIn("orphan\t", self.index_text())

    def test_query_preserves_valid_and_unmatched_stale_records(self) -> None:
        self.save("wanted", "wanted-keyword")
        unrelated_source = self.save("unrelated", "unrelated-keyword")
        unrelated_source.write_text("VALUE = 'stale'\n", encoding="utf-8")
        wanted_before = self.record("wanted").read_bytes()

        result, stdout, _ = self.capture(pcm.query_memory, self.root, "wanted-keyword", 3)

        self.assertEqual(0, result)
        self.assertIn("VALID wanted", stdout)
        self.assertEqual(wanted_before, self.record("wanted").read_bytes())
        self.assertTrue(self.record("unrelated").is_file())
        self.assertIn("unrelated\t", self.index_text())

    def test_query_repairs_malformed_index_without_following_unsafe_id(self) -> None:
        self.capture(pcm.init_memory, self.root, False)
        sentinel = Path(self.temporary.name) / "sentinel.json"
        sentinel.write_text("keep", encoding="utf-8")
        index = self.root / pcm.MEMORY_DIR / "index.tsv"
        index.write_text(
            "#bad-header\n"
            + "../../../sentinel\tattack\tpath\tsymbol\tunsafe id\n"
            + "malformed-row\n",
            encoding="utf-8",
        )

        result, stdout, stderr = self.capture(pcm.query_memory, self.root, "attack", 3)

        self.assertEqual(0, result)
        self.assertIn("EMPTY_INDEX", stdout)
        self.assertIn("malformed index header", stderr)
        self.assertIn("invalid index id", stderr)
        self.assertIn("malformed index row", stderr)
        self.assertEqual("keep", sentinel.read_text(encoding="utf-8"))
        self.assertEqual(pcm.INDEX_HEADER, self.index_text())

    def test_audit_prunes_all_invalid_records_and_rebuilds_index(self) -> None:
        self.save("valid", "valid-keyword")
        stale_source = self.save("stale", "stale-keyword")
        self.save("broken", "broken-keyword")
        stale_source.write_text("VALUE = 'changed-after-save'\n", encoding="utf-8")
        self.record("broken").write_text("[]", encoding="utf-8")

        result, stdout, _ = self.capture(pcm.audit_memory, self.root)

        self.assertEqual(0, result)
        self.assertIn("VALID valid", stdout)
        self.assertIn("PRUNED stale", stdout)
        self.assertIn("PRUNED broken", stdout)
        self.assertTrue(self.record("valid").is_file())
        self.assertFalse(self.record("stale").exists())
        self.assertFalse(self.record("broken").exists())
        self.assertIn("valid\t", self.index_text())
        self.assertNotIn("stale\t", self.index_text())
        self.assertNotIn("broken\t", self.index_text())

    def test_audit_prunes_record_whose_filename_does_not_match_id(self) -> None:
        self.save("original", "original-keyword")
        alias = self.record("alias")
        self.record("original").rename(alias)

        result, stdout, _ = self.capture(pcm.audit_memory, self.root)

        self.assertEqual(0, result)
        self.assertIn("record filename does not match id", stdout)
        self.assertIn("PRUNED alias", stdout)
        self.assertFalse(alias.exists())
        self.assertNotIn("original\t", self.index_text())


if __name__ == "__main__":
    unittest.main()
