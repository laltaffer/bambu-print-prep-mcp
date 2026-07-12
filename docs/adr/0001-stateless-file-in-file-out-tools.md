# 0001 — Stateless file-in/file-out tool surface

Date: 2026-07-09
Status: accepted

## Context

Model modifications are multi-step chains (cut → orient → open in Studio). The
MCP server could hold loaded meshes in memory between calls (stateful workspace)
or treat every operation as an independent file-to-file transformation.

## Decision

Every operation is a separate MCP tool that reads a model file from disk and
writes new derived file(s) to disk. No server-side session state. Chaining
happens by passing paths between tool calls.

## Consequences

- Every intermediate step is a real file the user can open, inspect, or return
  to; a crashed server loses nothing.
- Each step re-parses the mesh. Accepted cost: hobby-scale models parse in
  well under a second; correctness and inspectability outrank throughput here.
- Tool schemas stay per-operation and precise (the 2026-07-09 review showed
  schema-vs-core drift is the failure mode to guard against).
