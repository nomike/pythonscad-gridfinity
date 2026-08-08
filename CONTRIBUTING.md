# Contributing

Contributions are welcome through GitHub issues and pull requests.

## Development setup

Python 3.10 or newer, [uv](https://docs.astral.sh/uv/), and Git are required.

```console
uv sync --all-groups
uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
```

Run all checks before opening a pull request:

```console
uv run pre-commit run --all-files
uv run pytest
uv run pyright
uv build
uvx --from twine==7.0.0 twine check dist/*
```

## Changes

- Keep library geometry at the default origin unless an example demonstrates placement.
- Preserve explicit units and document every distance as millimetres.
- Add tests for validation logic, public API changes, and `GridfinitySpec` updates.
- Update user-facing documentation with behavior changes.
- Regenerate README gallery previews when geometry changes significantly (see
  `scripts/render_gallery_*.py`).

## Commit messages

Every commit and pull-request title must follow
[Conventional Commits](https://www.conventionalcommits.org/):

```text
feat: add half-grid vase bin preset
fix: correct stacking lip height for reduced lip mode
docs: document TestPyPI development builds
```

Use `!` or a `BREAKING CHANGE:` footer for incompatible API changes. The
release automation uses these messages to choose the semantic version and
generate the changelog. See [VERSIONING.md](VERSIONING.md).

## Pull requests

Keep pull requests focused, explain how the result was tested, and ensure all
required checks pass.
