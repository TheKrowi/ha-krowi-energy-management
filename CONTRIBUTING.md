# Contributing to Krowi Energy Management

## Development status

This project is in **beta** (`0.0.x`). No stable release has been cut yet.

---

## Architecture conventions

See `openspec/config.yaml` for the full context block. Key rules:

- **No coordinator** — entities react to state changes via `async_track_state_change_event`, never poll.
- **Options override data** — every `async_setup_entry` must use `effective = {**entry.data, **entry.options}` and read all mutable fields from `effective`. Only `domain_type` may be read directly from `entry.data`.
- **EntitySelector for entity fields** — use `selector.EntitySelector()` (no domain filter) for any config/options field that accepts an entity ID.
- **RestoreNumber** — number entities subclass `RestoreNumber` to persist values across HA restarts.

---

## Commit style

Use [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | When to use |
|--------|-------------|
| `feat:` | New user-visible feature |
| `fix:` | Bug fix |
| `chore:` | Maintenance, version bumps, non-functional changes |
| `refactor:` | Code restructure with no behaviour change |
| `docs:` | Documentation only |

---

## Release checklist

> Only relevant when cutting an official release. Skip during beta.

1. Update `"version"` in `custom_components/krowi_energy_management/manifest.json` to the new version (e.g. `1.0.0`)
2. Commit: `chore: release v1.0.0`
3. Push to `main`
4. Create a **GitHub Release** with:
   - Tag: `v1.0.0` (must match `manifest.json` version, prefixed with `v`)
   - Target: the release commit on `main`
   - Release notes describing what changed
5. HACS will pick up the new version and display release notes in the update UI
