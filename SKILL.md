---
name: project-code-memory
description: Automatically initialize and maintain a compact, repository-local projectCodeMemory index of verified code structure and logic, reuse complete valid hits without rereading source, and inspect only missing or stale details. Use at the start and end of every repository code analysis, debugging, implementation, fix, refactor, or test task, including read-only analysis, to reduce codebase discovery time and token use without trusting stale conclusions.
---

# Project Code Memory

Use `projectCodeMemory/` as an ignored, machine-oriented cache. Put every file created solely for code memory inside this folder. Current source remains authoritative, but a `VALID` record is a fingerprint-verified proxy for its supporting files; never reopen those files merely to reconfirm remembered facts.

## Start every code task

1. Resolve the repository root. Before any broad source scan, make this the first repository command, even for read-only analysis:

   ```bash
   python3 <skill-dir>/scripts/pcm.py query --root <repo-root> "<task terms, paths, or symbols>"
   ```

   `query` automatically and idempotently creates `projectCodeMemory/index.tsv`, `records/`, and `drafts/` when absent and ensures the root `.gitignore` contains `/projectCodeMemory/`.

2. Choose exactly one path from the query result:
   - **Complete hit**: `VALID` records contain every fact needed for a read-only answer. Stop discovery and answer from memory. Do not run `rg`, `find`, source reads, searches, save, reindex, or audit.
   - **Partial hit**: `VALID` records answer only part of the task. Keep their facts and inspect only the explicitly missing symbols or details. Do not broadly rediscover remembered flows.
   - **Miss or invalid**: `STALE`, `ERROR`, `NO_MATCH`, or `EMPTY_INDEX`. Inspect current source for the uncovered scope and replace stale relevant records after verification.
3. For a code change with a complete architectural hit, trust remembered structure and invariants. Read only the exact edit sites and tests needed to make the change; do not reconstruct the surrounding architecture.
4. Query again only when a newly discovered symbol or path may match another record needed for an actual gap.

`<skill-dir>` means the absolute directory containing this `SKILL.md`; resolve it from the loaded skill location.

Invoking this skill authorizes cache writes only to `projectCodeMemory/` plus the required `.gitignore` rule, including during read-only analysis. Do not change source, tests, build files, or other project configuration unless the user requested code changes.

The root-relative ignore rule is:

```gitignore
/projectCodeMemory/
```

The initializer preserves unrelated `.gitignore` content and user changes.

## Record verified knowledge

Record only new or changed reusable logic actually established after a partial hit, miss, stale record, or code change. Prefer entry points, call/data flows, ownership boundaries, invariants, persistence effects, configuration gates, and high-value test commands. Never rewrite an unchanged complete-hit record. Do not store code dumps, guesses, secrets, generated output, or facts copied without checking them.

Create the JSON draft at `projectCodeMemory/drafts/<id>.json` with this shape, then save it:

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
python3 <skill-dir>/scripts/pcm.py save --root <repo-root> <repo-root>/projectCodeMemory/drafts/<id>.json
```

The tool rejects drafts outside `projectCodeMemory/drafts/`, recomputes SHA-256 fingerprints for every supporting path, writes compact JSON under `projectCodeMemory/records/`, rebuilds `index.tsv`, and deletes the consumed draft. Keep each record scoped to one coherent topic. Include every source file needed to support cross-file conclusions.

## Finish every code task

1. If the task was answered entirely by complete `VALID` hits and no code changed, stop with no memory writes or audit.
2. If source inspection produced reusable new facts, save only those facts. For analysis-only tasks, exact current-source inspection is valid verification; do not claim that tests ran.
3. For code changes, update records whose supporting files changed after relevant checks pass. If checks could not run, record the exact source-based verification and limitation.
4. For stale records related to the task, re-read only their scope and overwrite them with `save`. If the logic no longer exists, remove that record and run `reindex`.
5. Run `audit` only after code or memory writes that may affect records. Leave unrelated stale records untrusted for later repair.

## Integrity rules

- A fingerprint mismatch always overrides the remembered conclusion.
- Never edit stored fingerprints by hand; `save` owns them.
- Never claim verification stronger than what was performed.
- Keep index summaries and records terse: navigation and invariants, not prose documentation.
- Keep indexes, records, drafts, scratch notes, manifests, state, locks, and temporary output created for this memory workflow under `projectCodeMemory/`. Never place them in the repository root, source tree, `/tmp`, user home, or the skill directory.
- Never commit `projectCodeMemory/`.
