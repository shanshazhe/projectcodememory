# Project Code Memory

Project Code Memory is a Codex skill that preserves compact, verified knowledge about a codebase between tasks. It helps Codex reuse prior analysis without repeatedly scanning the same source files, while SHA-256 fingerprints prevent stale conclusions from being trusted.

The cache is local to the target repository, machine-oriented, and never a replacement for the source code itself.

## Highlights

- Reuses verified architecture, control-flow, invariant, and side-effect notes.
- Validates every record against fingerprints of its supporting source files.
- Uses the smallest sufficient evidence set to avoid invalidating unrelated knowledge.
- Prunes stale or malformed records safely and repairs the searchable index.
- Avoids duplicate records by merging highly similar, structurally anchored topics at save time.
- Keeps all generated state under an ignored `projectCodeMemory/` directory.
- Activates only for broad, cross-file, unfamiliar, or recurring code work; narrow tasks skip its fixed overhead.
- Avoids first-time memory setup for projects with 10 or fewer owned source and test files.
- Keeps low-frequency record-authoring details in an on-demand reference instead of every skill load.
- Uses only the Python standard library.

## Install as a Codex skill

Codex discovers user-level skills under `$HOME/.agents/skills`. Clone this repository there:

```bash
git clone https://github.com/shanshazhe/projectcodememory.git "$HOME/.agents/skills/project-code-memory"
```

Then invoke the skill explicitly in a Codex prompt:

```text
$project-code-memory analyze the authentication flow
```

Codex can also select the skill automatically when a task matches its description. If a newly installed skill does not appear, restart Codex.

## How the workflow behaves

1. Skip the workflow for narrow work already pinned to one or two exact files or symbols.
2. Pin one primary project root. On first use, count repository-owned source and test paths without reading contents and stop as soon as the count reaches 11; an existing cache skips this count.
3. With no existing cache, bypass first-time memory setup when the count is 10 or fewer.
4. For eligible projects, query memory before reading or broadly searching source content, using `--limit 1` for focused work and up to three only for genuinely cross-cutting work.
5. Reuse complete fingerprint-valid hits and inspect only missing, stale, or exact edit details.
6. Save only newly verified, stable, reusable knowledge that passes the save gate; load the record-authoring reference only when a save is warranted.
7. Let normal queries validate and prune matched records; reserve full-cache audits for deliberate maintenance.

Directories outside the primary project are treated as read-only references. The skill never creates a second memory cache for them.

## Cache layout

```text
projectCodeMemory/
├── index.tsv       # Compact searchable index
├── records/        # Normalized, fingerprinted records
└── drafts/         # Temporary JSON drafts waiting to be saved
```

The skill ensures the target repository's root `.gitignore` contains:

```gitignore
/projectCodeMemory/
```

Do not commit the cache.

## CLI reference

Run the CLI from this repository and pass the target project with `--root`:

```bash
python3 scripts/pcm.py init --root /path/to/project
python3 scripts/pcm.py query --root /path/to/project "symbol path or task terms"
python3 scripts/pcm.py query --root /path/to/project --limit 5 "task terms"
python3 scripts/pcm.py save --root /path/to/project /path/to/project/projectCodeMemory/drafts/topic.json
python3 scripts/pcm.py reindex --root /path/to/project
python3 scripts/pcm.py audit --root /path/to/project
```

| Command | Behavior |
| --- | --- |
| `init` | Creates the cache directories and index, then ensures the ignore rule exists. |
| `query` | Initializes if needed, ranks index matches, validates up to `--limit` records, and emits valid knowledge. Matching stale or invalid records are pruned and the index is repaired. The default limit is 3. |
| `save` | Validates and fingerprints a draft. The same ID replaces its record; a different, highly similar topic is left `UNCHANGED` or `MERGED` into the existing ID and summary. Otherwise a new record is saved. The index is rebuilt and the draft is removed after success. |
| `reindex` | Rebuilds the index from readable, structurally valid records. It does not check source fingerprints or perform a full cleanup. |
| `audit` | Validates every record, prunes all stale or invalid records, and rebuilds the index. |

`query` is intentionally not read-only: it can create `projectCodeMemory/`, update `.gitignore`, prune matched records, and repair the index. It only validates records selected by the query and `--limit`; use `audit` for a deliberate full-cache health check after broad changes or when corruption is suspected. Unmatched stale records may remain until a later query or audit, but they are never returned as `VALID` without fingerprint validation.

Common status lines include `SAVED`, `MERGED`, `UNCHANGED`, `VALID`, `STALE`, `ERROR`, `PRUNED`, `EMPTY_INDEX`, `NO_MATCH`, and `NO_MEMORY`.

## Draft format

Drafts must live inside `<root>/projectCodeMemory/drafts/` and use repository-relative source paths:

```json
{
  "id": "authentication-flow",
  "keywords": ["auth", "login", "session"],
  "paths": ["src/auth.py"],
  "symbols": ["authenticate", "SessionStore"],
  "summary": "Authentication routing and session ownership",
  "facts": ["authenticate validates credentials before creating a session"],
  "flows": ["request -> authenticate -> SessionStore"],
  "invariants": ["A session is created only after successful validation"],
  "side_effects": ["Successful login persists a session"],
  "verification": ["python3 -m unittest tests.test_auth"]
}
```

Required, non-empty fields are `id`, `keywords`, `paths`, `summary`, `facts`, and `verification`. The `id` must match `[a-z0-9][a-z0-9._-]{0,79}`. Every path must resolve to an existing file inside the target project and must not point into `projectCodeMemory/`.

`paths` is an invalidation dependency list, not a research log. Include a file only when its current contents directly support a stored fact, flow, invariant, or side effect. Browsed files, incidental callers, shared wrappers, build files, and tests used only for verification should stay out of `paths`; keep commands and results in `verification`. Do not omit genuinely necessary cross-file evidence. Split independent topics into separate records when that keeps their evidence and change cadence separate.

The CLI stores normalized records rather than generating analysis itself. Codex is responsible for inspecting the code, verifying conclusions, and preparing the draft.

## Development

Requires Python 3.9 or newer. Run the test suite with:

```bash
python3 -m unittest discover -s tests -v
```

See [`SKILL.md`](SKILL.md) for the core agent workflow and safety rules. Record-authoring details live in [`references/record-format.md`](references/record-format.md) and are loaded only when needed.
