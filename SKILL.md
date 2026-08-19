---
name: project-code-memory
description: Reuses SHA-256-verified knowledge to avoid repeated source scans in large codebases. Use before broad or cross-file repository analysis, unfamiliar debugging or implementation, architecture and invariant tracing, or recurring domain questions where prior analysis may exist. Do not use for non-code tasks or narrowly scoped work already pinned to one or two exact files or symbols, such as typos, mechanical edits, and direct lookups; avoid first-time setup in projects with 10 or fewer owned source/test files.
---

# Project Code Memory

Use `projectCodeMemory/` as a compact, ignored cache of verified code knowledge. Optimize total investigation cost, not the number of records. Current source is authoritative; a fingerprint-valid record is a trusted proxy only for the files and facts it covers.

## 1. Eligibility gate

Pin `PRIMARY_PROJECT_ROOT` once to the repository that owns the code the user asked about. Default to the nearest repository containing the task's initial working directory; change roots only when the user explicitly switches the target project.

Use this workflow only when the task benefits from broad, cross-file, unfamiliar, or repeated code reasoning. Skip it for localized work that can be completed with at most one or two known source reads.

Before the first source-content read:

1. If `<root>/projectCodeMemory/` already exists, skip counting and continue to **Query first**.
2. Otherwise, count repository-owned source and test file paths without reading their contents. Include tracked and non-ignored untracked files; exclude vendored dependencies, generated files, build outputs, and caches. Stop once the count reaches 11.
3. If the count is 10 or fewer, bypass this skill for the rest of the task. Do not initialize memory or modify `.gitignore`.

## 2. Query first

For an eligible project, make the memory query the first content-discovery operation. Build a focused query from the user's domain terms plus any known paths, classes, methods, event names, or error codes; avoid generic filler words.

```bash
python3 <skill-dir>/scripts/pcm.py query \
  --root <primary-project-root> \
  --limit 1 \
  "<focused task terms, paths, and symbols>"
```

Use `--limit 1` for a focused question or one flow; raise it to at most `3` only when the task genuinely spans independent topics. `query` initializes memory when absent, ensures the root `.gitignore` contains `/projectCodeMemory/`, validates matching fingerprints, and prunes matched stale or malformed records.

Choose one path:

- **Complete `VALID` hit:** For read-only work, answer directly from the record and do not reopen its evidence files merely to reconfirm it. For a code change, read only the exact edit sites and relevant tests.
- **Partial `VALID` hit:** Keep the valid facts and inspect only the explicitly missing behavior or symbols.
- **`NO_MATCH`, `EMPTY_INDEX`, `STALE`, or `ERROR`:** Inspect current source, starting with targeted symbol/path searches rather than a broad rescan.

Query again only when discovery exposes a genuinely new symbol or subsystem that could match a different record. Do not loop over paraphrased queries.

## 3. Use memory narrowly

- Treat a record as authority only for its stated facts, flows, invariants, side effects, and fingerprinted paths.
- Read current source for uncovered details, exact edit context, or behavior not stated in the record.
- Never infer that an omitted fact is false.
- Keep one fixed primary root. Code outside it is a secondary, read-only reference: never initialize memory there or store external-only behavior in the primary cache.

## 4. Save only high-value knowledge

Save a record only when all are true:

1. The task established new or changed knowledge through current-source inspection or a verified code change.
2. The knowledge is stable and likely to help a future task.
3. It captures a meaningful flow, ownership boundary, invariant, persistence/event side effect, configuration gate, or similarly non-obvious behavior.
4. A small set of repository files directly supports every stored claim.

Do **not** save line numbers, code dumps, localized implementation trivia, transient failures, guesses, secrets, routine DTO plumbing, mechanical edits, or facts already covered by an unchanged complete hit.

When the save gate passes, read [references/record-format.md](references/record-format.md) completely, create the draft there described, and run `save`. Otherwise finish without a memory write. If future value is uncertain, do not save.

For code changes:

- Update a loaded record when the change alters its reusable knowledge.
- If an evidence path changed but the facts did not, refresh the record only when it was task-relevant and revalidation is cheap; otherwise let a future query prune it.
- Do not run a full audit after an ordinary change or single save.

## 5. Integrity and maintenance

- A fingerprint mismatch always overrides remembered conclusions.
- Never edit stored fingerprints, compact records, or `index.tsv` by hand; use the CLI.
- Keep every cache artifact under `<root>/projectCodeMemory/` and never commit it.
- `query` may write only that cache plus the root ignore rule; it must not modify source or project configuration.
- Run `audit --root <root>` only for deliberate full-cache maintenance, broad refactors likely to stale many records, or suspected corruption.
