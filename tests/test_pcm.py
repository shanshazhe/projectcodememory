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
        draft = self.write_draft(
            identifier,
            keywords=[keyword],
            paths=[source.name],
            summary=f"Memory for {identifier}",
            facts=[f"Fact for {identifier}"],
        )
        result, _, _ = self.capture(pcm.save_record, self.root, str(draft))
        self.assertEqual(0, result)
        return source

    def write_draft(
        self,
        identifier: str,
        *,
        keywords: list[str],
        paths: list[str],
        summary: str,
        facts: list[str],
        symbols: list[str] | None = None,
        flows: list[str] | None = None,
        invariants: list[str] | None = None,
        side_effects: list[str] | None = None,
        verification: list[str] | None = None,
    ) -> Path:
        self.capture(pcm.init_memory, self.root, False)
        draft = self.root / pcm.MEMORY_DIR / "drafts" / f"{identifier}.json"
        draft.write_text(
            json.dumps(
                {
                    "id": identifier,
                    "keywords": keywords,
                    "paths": paths,
                    "symbols": symbols or [],
                    "summary": summary,
                    "facts": facts,
                    "flows": flows or [],
                    "invariants": invariants or [],
                    "side_effects": side_effects or [],
                    "verification": verification or ["Unit fixture"],
                }
            ),
            encoding="utf-8",
        )
        return draft

    def record(self, identifier: str) -> Path:
        return self.root / pcm.MEMORY_DIR / "records" / f"{identifier}.json"

    def index_text(self) -> str:
        return (self.root / pcm.MEMORY_DIR / "index.tsv").read_text(encoding="utf-8")

    def index_rows(self) -> list[str]:
        return [line for line in self.index_text().splitlines() if line and not line.startswith("#")]

    def test_save_skips_highly_similar_duplicate(self) -> None:
        source = self.root / "task_history.py"
        source.write_text("HISTORY_ID = 'BIGINT'\n", encoding="utf-8")
        first = self.write_draft(
            "task-history",
            keywords=["task", "history", "id"],
            paths=[source.name],
            symbols=["TaskHistory#historyId"],
            summary="Task history identifier persistence type",
            facts=["History identifiers use BIGINT"],
        )
        self.capture(pcm.save_record, self.root, str(first))
        original = self.record("task-history").read_bytes()
        duplicate = self.write_draft(
            "task-history-id",
            keywords=["TASK", "HISTORY", "ID"],
            paths=[source.name],
            symbols=["TaskHistory#historyId"],
            summary="Task history identifier persistence type",
            facts=["History identifiers use BIGINT"],
        )

        result, stdout, _ = self.capture(pcm.save_record, self.root, str(duplicate))

        self.assertEqual(0, result)
        self.assertIn("UNCHANGED task-history-id duplicate-of=task-history", stdout)
        self.assertEqual(original, self.record("task-history").read_bytes())
        self.assertFalse(self.record("task-history-id").exists())
        self.assertFalse(duplicate.exists())
        self.assertEqual(1, len(self.index_rows()))

    def test_save_merges_incremental_knowledge_into_existing_topic(self) -> None:
        source = self.root / "task_history.py"
        mapping = self.root / "task_history_dto.py"
        source.write_text("HISTORY_ID = 'BIGINT'\n", encoding="utf-8")
        mapping.write_text("history_id: int\n", encoding="utf-8")
        first = self.write_draft(
            "task-history",
            keywords=["task", "history", "id"],
            paths=[source.name],
            symbols=["TaskHistory#historyId"],
            summary="Task history identifier persistence type",
            facts=["History identifiers use BIGINT"],
            verification=["Checked migration"],
        )
        self.capture(pcm.save_record, self.root, str(first))
        incremental = self.write_draft(
            "task-history-type",
            keywords=["task", "history", "id", "java"],
            paths=[source.name, mapping.name],
            symbols=["TaskHistory#historyId"],
            summary="Task history identifier persistence type",
            facts=["History identifiers use BIGINT", "Java maps history identifiers to long"],
            verification=["Checked migration", "Checked DTO"],
        )

        result, stdout, _ = self.capture(pcm.save_record, self.root, str(incremental))

        self.assertEqual(0, result)
        self.assertIn("MERGED task-history-type into=task-history", stdout)
        merged = pcm.load_record(self.record("task-history"))
        self.assertEqual(["task", "history", "id", "java"], merged["k"])
        self.assertEqual([source.name, mapping.name], merged["p"])
        self.assertEqual(
            ["History identifiers use BIGINT", "Java maps history identifiers to long"],
            merged["f"],
        )
        self.assertEqual(["Checked migration", "Checked DTO"], merged["verify"])
        self.assertEqual(set(merged["p"]), set(merged["fp"]))
        self.assertFalse(self.record("task-history-type").exists())
        self.assertFalse(incremental.exists())
        self.assertEqual(1, len(self.index_rows()))

    def test_save_preserves_distinct_topics_in_same_file(self) -> None:
        source = self.root / "tasks.py"
        source.write_text("TASKS = []\n", encoding="utf-8")
        history = self.write_draft(
            "task-history",
            keywords=["task", "history", "id"],
            paths=[source.name],
            symbols=["TaskHistoryDao#insert"],
            summary="Task history identifier behavior",
            facts=["History IDs are persisted"],
        )
        self.capture(pcm.save_record, self.root, str(history))
        pagination = self.write_draft(
            "task-pagination",
            keywords=["task", "history", "id"],
            paths=[source.name],
            symbols=["TaskController#list"],
            summary="Task history identifier behavior",
            facts=["History results use pagination"],
        )

        result, stdout, _ = self.capture(pcm.save_record, self.root, str(pagination))

        self.assertEqual(0, result)
        self.assertIn("SAVED task-pagination", stdout)
        self.assertTrue(self.record("task-history").exists())
        self.assertTrue(self.record("task-pagination").exists())
        self.assertEqual(2, len(self.index_rows()))

    def test_save_preserves_topics_with_unrelated_summaries(self) -> None:
        source = self.root / "tasks.py"
        source.write_text("TASKS = []\n", encoding="utf-8")
        retention = self.write_draft(
            "task-retention",
            keywords=["task"],
            paths=[source.name],
            symbols=["TaskService#update"],
            summary="Retention cleanup schedule",
            facts=["Task updates share one service"],
        )
        self.capture(pcm.save_record, self.root, str(retention))
        assignees = self.write_draft(
            "task-assignees",
            keywords=["task"],
            paths=[source.name],
            symbols=["TaskService#update"],
            summary="Assignee authorization rules",
            facts=["Task updates share one service", "Assignee updates require authorization"],
        )

        result, stdout, _ = self.capture(pcm.save_record, self.root, str(assignees))

        self.assertEqual(0, result)
        self.assertIn("SAVED task-assignees", stdout)
        self.assertEqual(2, len(self.index_rows()))

    def test_save_merges_no_symbol_topic_that_gains_scope(self) -> None:
        source = self.root / "task_history.py"
        mapping = self.root / "task_history_dto.py"
        source.write_text("HISTORY_ID = 'BIGINT'\n", encoding="utf-8")
        mapping.write_text("history_id: int\n", encoding="utf-8")
        first = self.write_draft(
            "task-history",
            keywords=["task", "history", "id"],
            paths=[source.name],
            summary="Task history identifier persistence type",
            facts=["History identifiers use BIGINT"],
        )
        self.capture(pcm.save_record, self.root, str(first))
        expanded = self.write_draft(
            "task-history-expanded",
            keywords=["task", "history", "id"],
            paths=[source.name, mapping.name],
            symbols=["TaskHistory#historyId"],
            summary="Task history identifier persistence type",
            facts=["History identifiers use BIGINT", "Java maps history identifiers to long"],
        )

        result, stdout, _ = self.capture(pcm.save_record, self.root, str(expanded))

        self.assertEqual(0, result)
        self.assertIn("MERGED task-history-expanded into=task-history", stdout)
        merged = pcm.load_record(self.record("task-history"))
        self.assertEqual([source.name, mapping.name], merged["p"])
        self.assertEqual(["TaskHistory#historyId"], merged["s"])
        self.assertEqual(1, len(self.index_rows()))

    def test_save_rejects_extreme_structural_subset_as_duplicate(self) -> None:
        sources = [self.root / f"task_{number}.py" for number in range(3)]
        for source in sources:
            source.write_text("TASKS = []\n", encoding="utf-8")
        narrow = self.write_draft(
            "narrow-task-topic",
            keywords=["task", "state"],
            paths=[sources[0].name],
            symbols=["TaskService#read"],
            summary="Task state ownership and routing",
            facts=["Task state belongs to a user"],
        )
        self.capture(pcm.save_record, self.root, str(narrow))
        broad = self.write_draft(
            "broad-task-topic",
            keywords=["task", "state"],
            paths=[source.name for source in sources],
            symbols=["TaskService#read", "TaskService#write", "TaskService#delete"],
            summary="Task state ownership and routing",
            facts=["Task state belongs to a user", "Task state supports multiple operations"],
        )

        result, stdout, _ = self.capture(pcm.save_record, self.root, str(broad))

        self.assertEqual(0, result)
        self.assertIn("SAVED broad-task-topic", stdout)
        self.assertEqual(2, len(self.index_rows()))

    def test_save_prunes_invalid_record_before_committing(self) -> None:
        self.save("broken", "broken-keyword")
        self.record("broken").write_text("{not-json", encoding="utf-8")
        source = self.root / "current.py"
        source.write_text("VALUE = 'current'\n", encoding="utf-8")
        current = self.write_draft(
            "current",
            keywords=["current-keyword"],
            paths=[source.name],
            summary="Current memory",
            facts=["Current fact"],
        )

        result, stdout, _ = self.capture(pcm.save_record, self.root, str(current))

        self.assertEqual(0, result)
        self.assertIn("ERROR broken", stdout)
        self.assertIn("PRUNED broken", stdout)
        self.assertIn("SAVED current", stdout)
        self.assertFalse(self.record("broken").exists())
        self.assertTrue(self.record("current").exists())
        self.assertFalse(current.exists())
        self.assertEqual(1, len(self.index_rows()))

    def test_save_replaces_same_id_instead_of_merging(self) -> None:
        source = self.root / "task_history.py"
        source.write_text("HISTORY_ID = 'BIGINT'\n", encoding="utf-8")
        first = self.write_draft(
            "task-history",
            keywords=["old"],
            paths=[source.name],
            summary="Old summary",
            facts=["Old fact"],
        )
        self.capture(pcm.save_record, self.root, str(first))
        replacement = self.write_draft(
            "task-history",
            keywords=["new"],
            paths=[source.name],
            summary="New summary",
            facts=["New fact"],
        )

        result, stdout, _ = self.capture(pcm.save_record, self.root, str(replacement))

        self.assertEqual(0, result)
        self.assertIn("SAVED task-history", stdout)
        replaced = pcm.load_record(self.record("task-history"))
        self.assertEqual(["new"], replaced["k"])
        self.assertEqual("New summary", replaced["sum"])
        self.assertEqual(["New fact"], replaced["f"])
        self.assertFalse(replacement.exists())
        self.assertEqual(1, len(self.index_rows()))

    def test_save_prunes_stale_similar_record_before_saving(self) -> None:
        source = self.root / "task_history.py"
        source.write_text("HISTORY_ID = 'BIGINT'\n", encoding="utf-8")
        first = self.write_draft(
            "old-task-history",
            keywords=["task", "history", "id"],
            paths=[source.name],
            symbols=["TaskHistory#historyId"],
            summary="Task history identifier persistence type",
            facts=["History identifiers use BIGINT"],
        )
        self.capture(pcm.save_record, self.root, str(first))
        source.write_text("HISTORY_ID = 'UUID'\n", encoding="utf-8")
        current = self.write_draft(
            "current-task-history",
            keywords=["task", "history", "id"],
            paths=[source.name],
            symbols=["TaskHistory#historyId"],
            summary="Task history identifier persistence type",
            facts=["History identifiers use UUID"],
        )

        result, stdout, _ = self.capture(pcm.save_record, self.root, str(current))

        self.assertEqual(0, result)
        self.assertIn("STALE old-task-history", stdout)
        self.assertIn("PRUNED old-task-history", stdout)
        self.assertIn("SAVED current-task-history", stdout)
        self.assertFalse(self.record("old-task-history").exists())
        self.assertTrue(self.record("current-task-history").exists())
        self.assertFalse(current.exists())
        self.assertEqual(1, len(self.index_rows()))

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
