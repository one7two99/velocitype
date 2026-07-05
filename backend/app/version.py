"""Single source of the backend's version.

Must match ``frontend/package.json`` (enforced by a CI check). Bump both together
on every release, alongside CHANGELOG.md and frontend/src/releaseNotes.ts.
"""

__version__ = "0.25.0"
