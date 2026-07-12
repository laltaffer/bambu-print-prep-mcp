# 0002 — Accept STL and 3MF input; always output STL

Date: 2026-07-09
Status: accepted

## Context

MakerWorld downloads arrive as either plain STL or Bambu-native 3MF (which can
embed print profiles and plate layout). Users will hand the server whichever
they have. trimesh can read both but cannot faithfully preserve Bambu's
profile/plate payload when re-writing 3MF.

## Decision

Operations accept .stl and .3mf model files. Derived files are always .stl.

## Consequences

- The tool never refuses the files the user actually has.
- A modified mesh loses any embedded print profile — honestly, by design: after
  geometry changes the baked profile's validity is unknowable, and Bambu Studio
  re-slices on import anyway. Writing 3MF output would imply profile fidelity
  we cannot provide.
- If profile-preserving edits are ever wanted, that is a new decision (likely
  driving Bambu Studio itself, not trimesh).
