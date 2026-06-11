# Agent Core Instructions

This folder is the documentation index for the project. Treat the docs as reference material and keep them stable unless the user explicitly asks to revise the documentation itself.

## How to Use This Folder
- Read this file first when you need platform rules, architecture references, or roadmap context.
- Treat the rest of `/home/ravi/workspace/form-builder/docs` as read-only specification unless asked to edit docs.
- Use codebase-memory MCP for backend/frontend symbol lookups when a docs question points to implementation detail.

## Do This First
- Identify whether the question is about docs, backend, or frontend behavior.
- Check the most relevant spec file before guessing from memory.
- If the question touches implementation, verify the code path in the owning repo.
- Reuse the existing graph index unless you know the source changed materially.

## Canonical Paths
- Docs: `/home/ravi/workspace/form-builder/docs`
- Backend: `/home/ravi/workspace/docker/apps/form-backend`
- Frontend: `/home/ravi/workspace/frontend`

## Cross-Repo Coordination
- If a docs item maps to code, verify the current backend/frontend implementation before assuming the doc is still current.
- Reindex only when source content changes materially or the user explicitly requests a refresh.

## Common Failure Modes
- Docs drift from implementation. Verify the owning repo before treating a spec as current.
- Older notes may conflict with newer repo instructions. Prefer the repository AGENTS file when there is a mismatch.
- Pure docs questions do not need code edits. Do not over-escalate them into implementation work.

## Skill Router
- Use repo-specific backend/frontend skills when the question is implementation-oriented.
- Use planning/review skills when the task is architectural, risky, or cross-repo.
- Use codebase-memory tools first when you need structure, callers, or dependency paths.

## Relevant References
- Backend tool and MCP routing notes now live in [`backend-mcp.json`](/home/ravi/workspace/form-builder/docs/backend-mcp.json) and [`backend-check-agent-tools.sh`](/home/ravi/workspace/form-builder/docs/backend-check-agent-tools.sh).
- Frontend tool and MCP routing notes now live in [`frontend-mcp.json`](/home/ravi/workspace/form-builder/docs/frontend-mcp.json), [`frontend-check-agent-tools.sh`](/home/ravi/workspace/form-builder/docs/frontend-check-agent-tools.sh), and [`frontend-watch-ridp-changes.sh`](/home/ravi/workspace/form-builder/docs/frontend-watch-ridp-changes.sh).
- Frontend skill files now live under [`frontend-skills/`](/home/ravi/workspace/form-builder/docs/frontend-skills).
- Use this file mainly as the entry point for product/architecture context, not as a place for implementation rules.
