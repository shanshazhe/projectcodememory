---
name: project-code-memory
description: ALWAYS load this skill FIRST, before any repository code analysis, debugging, implementation, fix, refactor, test, or read-only exploration — including before dispatching an Explore/general-purpose agent or running rg/grep/find over the codebase. MUST TRIGGER before that first broad source scan on any project with more than 10 repository-owned source and test files. Query the projectCodeMemory index before rereading source; reuse complete valid hits, fill only gaps, and let query prune stale entries. Bypass entirely (no init/query/save) for projects at or below the 10-file threshold.
---

# Project Code Memory

For non-tiny projects, use `projectCodeMemory/` as an ignored, machine-oriented cache. Put every file created solely for code memory inside this folder. Current source remains authoritative, but a `VALID` record is a fingerprint-verified proxy for its supporting files; never reopen those files merely to reconfirm remembered facts.

## Start every code task

1. Pin `PRIMARY_PROJECT_ROOT` once. Use the nearest repository root containing the task's initial working directory, or that initial directory when it is not in a repository. Do not recompute it after changing directories or following code into another folder.
2. Before any `pcm.py` command, count project-owned source and test files without reading their contents. When Git exists, count tracked plus non-ignored untracked files. Exclude vendored, generated, dependency, build-output, and existing `projectCodeMemory/` files.
   - **10 files or fewer**: Treat the project as tiny and stop this skill's memory workflow for the whole task. Do not run `init`, `query`, `save`, `reindex`, or `audit`; do not create, modify, or delete anything under `projectCodeMemory/`; and do not add, change, or remove its `.gitignore` rule. Leave any existing memory and ignore entry untouched and inspect source normally. This bypass overrides every later memory, finish, pruning, and integrity instruction.
   - **More than 10 files**: Before any broad source scan, make `query` the first repository command after this count, even for read-only analysis:

     ```bash
     python3 <skill-dir>/scripts/pcm.py query --root <primary-project-root> "<task terms, paths, or symbols>"
     ```

     `query` automatically and idempotently creates `projectCodeMemory/index.tsv`, `records/`, and `drafts/` in the primary project when absent and ensures only its root `.gitignore` contains `/projectCodeMemory/`.

3. Choose exactly one path from the query result:
   - **Complete hit**: `VALID` records contain every fact needed for a read-only answer. Stop discovery and answer from memory. Do not run `rg`, `find`, source reads, searches, save, reindex, or audit.
   - **Partial hit**: `VALID` records answer only part of the task. Keep their facts and inspect only the explicitly missing symbols or details. Do not broadly rediscover remembered flows.
   - **Miss or invalid**: `STALE`, `ERROR`, `NO_MATCH`, or `EMPTY_INDEX`. `query` automatically prunes matched stale or invalid records and repairs their index entries. Inspect current source for the uncovered scope and save a replacement only after verification.
4. For a code change with a complete architectural hit, trust remembered structure and invariants. Read only the exact edit sites and tests needed to make the change; do not reconstruct the surrounding architecture.
5. Query again only when a newly discovered symbol or path may match another record needed for an actual gap.

`<skill-dir>` means the absolute directory containing this `SKILL.md`; resolve it from the loaded skill location.

For a non-tiny project, invoking this skill authorizes cache writes only to `projectCodeMemory/` plus the required `.gitignore` rule, including during read-only analysis. Do not change source, tests, build files, or other project configuration unless the user requested code changes.

The root-relative ignore rule is:

```gitignore
/projectCodeMemory/
```

The initializer preserves unrelated `.gitignore` content and user changes.

## Cross-folder analysis

- Treat every folder or repository outside `PRIMARY_PROJECT_ROOT` as a secondary, read-only reference for memory purposes.
- Never pass a secondary folder to `--root`, run memory commands for it, create `projectCodeMemory/` inside it, or modify its `.gitignore`.
- Do not store external-only code logic in the primary project's memory. If external code explains an integration, record only the primary project's behavior and only with supporting source paths inside `PRIMARY_PROJECT_ROOT`.
- Keep the primary root fixed for the whole task. Change it only when the user explicitly switches the target project.

## Record verified knowledge

Record only new or changed reusable logic actually established after a partial hit, miss, stale record, or code change. Prefer entry points, call/data flows, ownership boundaries, invariants, persistence effects, configuration gates, and high-value test commands. Never rewrite an unchanged complete-hit record. Do not store code dumps, guesses, secrets, generated output, or facts copied without checking them.

Create the JSON draft at `<primary-project-root>/projectCodeMemory/drafts/<id>.json` with this shape, then save it:

```json
{
  "id": "stable-topic-id",
  "keywords": ["search", "terms"],
  "paths": ["exact/supporting/File.java"],
  "symbols": ["Class#method"],
  "summary": "One compact routing summary",
  "facts": ["Dense, independently useful fact"],
  "flows": ["entry -> validation -> persistence -> event"],
  "invariants": ["Condition that must remain true"],
  "side_effects": ["Database or event effect"],
  "verification": ["test command/result or exact source inspection"]
}
```

```bash
python3 <skill-dir>/scripts/pcm.py save --root <primary-project-root> <primary-project-root>/projectCodeMemory/drafts/<id>.json
```

The tool rejects drafts outside `projectCodeMemory/drafts/`, recomputes SHA-256 fingerprints for every supporting path, writes compact JSON under `projectCodeMemory/records/`, rebuilds `index.tsv`, and deletes the consumed draft. Keep each record scoped to one coherent topic. Include every source file needed to support cross-file conclusions.

## Finish every code task

1. If the task was answered entirely by complete `VALID` hits and no code changed, stop with no memory writes or audit.
2. If source inspection produced reusable new facts, save only those facts. For analysis-only tasks, exact current-source inspection is valid verification; do not claim that tests ran.
3. For code changes, update records whose supporting files changed after relevant checks pass. If checks could not run, record the exact source-based verification and limitation.
4. For records pruned by `query`, re-read only their scope and save a replacement when the logic still exists and remains reusable.
5. Run `audit --root <primary-project-root>` only after code or memory writes that may affect records. It prunes all stale or invalid records and rebuilds the index; `query` deliberately leaves unmatched records untouched to stay fast.

## Integrity rules

- A fingerprint mismatch always overrides the remembered conclusion.
- Automatically delete the corresponding cache record and index entry after a fingerprint mismatch or invalid record is verified. Never derive a deletion path from an invalid index ID.
- Never edit stored fingerprints by hand; `save` owns them.
- Never claim verification stronger than what was performed.
- Keep index summaries and records terse: navigation and invariants, not prose documentation.
- One task has exactly one memory root: `<primary-project-root>/projectCodeMemory/`.
- Keep indexes, records, drafts, scratch notes, manifests, state, locks, and temporary output created for this memory workflow under `projectCodeMemory/`. Never place them in the repository root, source tree, `/tmp`, user home, or the skill directory.
- Never commit `projectCodeMemory/`.
