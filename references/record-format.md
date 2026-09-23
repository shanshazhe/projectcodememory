# Record authoring reference

Read this file only after the `SKILL.md` save gate passes.

## Draft location and shape

Create a JSON draft inside `<primary-project-root>/projectCodeMemory/drafts/`:

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
  "verification": ["Inspected src/auth.py and ran python3 -m unittest tests.test_auth"]
}
```

Required, non-empty fields are `id`, `keywords`, `paths`, `summary`, `facts`, and `verification`. Optional list fields may be empty. The ID must match `[a-z0-9][a-z0-9._-]{0,79}`.

## Field quality

- **id:** Stable topic name, not a task or ticket number unless the ticket itself is the lasting concept.
- **keywords:** User vocabulary plus exact domain terms that a future query is likely to contain.
- **paths:** The smallest sufficient invalidation dependency set.
- **symbols:** Exact source literals for classes, methods, endpoints, event types, properties, or database objects that improve retrieval. Prefer identifiers that `query --locate` can find verbatim inside an evidence path; line numbers are resolved on demand and must not be stored.
- **summary:** One compact routing or ownership sentence.
- **facts:** Dense, independently useful statements; each must be supported by `paths`.
- **flows:** Important entry-to-effect chains using concise arrows.
- **invariants:** Conditions that must remain true, including important negative behavior.
- **side_effects:** Persistence, event, network, authorization, or lifecycle effects.
- **verification:** Exact source inspection and checks actually performed. Never imply that tests ran when they did not.

## Evidence-path rules

`paths` is an invalidation dependency list, not a browsing log.

Include a file only when its current contents are necessary to support a stored claim. Do not include incidental callers, navigation-only files, shared wrappers, build files, or tests used solely to run verification. A test belongs in `paths` only when the record stores behavior established by that test rather than by production source.

Do not omit a genuine cross-file dependency merely to reduce invalidation. Split independent topics when that yields smaller evidence sets or separates files with different change cadences.

Every evidence path must be repository-relative, exist inside the primary root, and stay outside `projectCodeMemory/`. Never store knowledge supported only by external repositories.

## Save

```bash
python3 <skill-dir>/scripts/pcm.py save \
  --root <primary-project-root> \
  <primary-project-root>/projectCodeMemory/drafts/<id>.json
```

`save` validates the draft, computes SHA-256 fingerprints, writes a compact record, rebuilds the index, and removes the consumed draft. Saving the same ID replaces it. A strongly overlapping different ID may return `UNCHANGED` or `MERGED`; accept that canonicalization rather than creating a duplicate.

After saving, do not run `reindex` or `audit`: `save` already rebuilds the index and fingerprints its evidence.

## Final check

Before finishing, confirm that:

- every claim is reusable rather than task narration;
- every claim has direct evidence in `paths`;
- no secret, guess, code dump, or stale conclusion is present;
- verification wording matches what actually ran;
- the cache remains ignored and uncommitted.
