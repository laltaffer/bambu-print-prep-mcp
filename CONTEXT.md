# CONTEXT — Ubiquitous Language

Glossary only. Implementation decisions live in docs/adr/; product scope in _brain.md.

## Terms

**Model file** — a 3D model on local disk that the user supplies. Accepted forms:
STL or 3MF. The original is never modified.

**Derived file** — a new STL written by an operation. Always STL regardless of the
model file's format; always a new file, never an overwrite.

**Operation** — a named, deterministic modification of a model file that produces
a derived file (e.g. scale, plane cut, split, mirror). One operation = one
tool call = one derived file (or one file per resulting part).

**Handoff** — opening a file in Bambu Studio on this Mac so the user can slice
and print. The pipeline's last mile; slicing itself is out of scope.

**Part** — one connected component of a model, produced by a split or a cut.
An operation that yields multiple parts writes one derived file per part.

**Validation** — the checks a derived file must pass before it is reported as a
result, in two tiers: *blocking* (unusable geometry — no file is produced and
nothing is left on disk) and *advisory* (delivered with a warning:
non-watertight, exceeds build volume, suspiciously small part).
