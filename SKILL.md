---
name: project-code-memory
description: Maintain a compact, repository-local projectCodeMemory index of verified code structure and logic, keep every generated memory artifact inside that folder, and reuse only entries whose source fingerprints are still current. Use at the start and end of every repository code analysis, debugging, implementation, fix, refactor, or test task to avoid repeated codebase discovery without trusting stale conclusions.
---

# Project Code Memory

Use `projectCodeMemory/` as an ignored, machine-oriented cache. Put every file created solely for code memory inside this folder. Treat current source and tests as authoritative; memory only accelerates navigation and recall.

## Start every code task

1. Resolve the repository root. If `projectCodeMemory/index.tsv` exists, query it **before broad source scans**:

   ```bash
   python3 <skill-dir>/scripts/pcm.py query --root <repo-root> "<task terms, paths, or symbols>"
   ```

2. Use only `VALID` records. Never use facts from `STALE` or malformed records; inspect current source instead and replace the record after verification.
3. Query again with discovered class, symbol, table, endpoint, or path names when the initial natural-language query has no useful match.
4. Read the current files being changed. A valid memory can replace repeated architectural discovery, not inspection of the edit site.

For a read-only analysis request, do not create or update memory unless the user also authorized repository changes.

## Initialize for an authorized code change

If memory does not exist, run:

```bash
python3 <skill-dir>/scripts/pcm.py init --root <repo-root>
```

Ensure the repository root `.gitignore` contains exactly this root-relative rule:

```gitignore
/projectCodeMemory/
```

Preserve unrelated `.gitignore` content and user changes.

## Record verified knowledge

Record only reusable logic actually established while reading, changing, or testing code. Prefer entry points, call/data flows, ownership boundaries, invariants, persistence effects, configuration gates, and high-value test commands. Do not store code dumps, guesses, secrets, generated output, or facts copied without checking them.

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

## Finish every code change

1. Run `python3 <skill-dir>/scripts/pcm.py audit --root <repo-root>` after edits and tests.
2. For stale records related to the changed logic, re-read current code and overwrite them with `save`. If the logic no longer exists, remove that record and run `reindex`.
3. Save newly learned logic only after its supporting code structure is confirmed and relevant checks pass. If checks could not run, state the exact source-based verification and any limitation; never promote uncertainty to fact.
4. Leave unrelated stale records untrusted. They may be repaired when their area is next analyzed.

## Integrity rules

- A fingerprint mismatch always overrides the remembered conclusion.
- Never edit stored fingerprints by hand; `save` owns them.
- Never claim verification stronger than what was performed.
- Keep index summaries and records terse: navigation and invariants, not prose documentation.
- Keep indexes, records, drafts, scratch notes, manifests, state, locks, and temporary output created for this memory workflow under `projectCodeMemory/`. Never place them in the repository root, source tree, `/tmp`, user home, or the skill directory.
- Never commit `projectCodeMemory/`.
