| ITEM | CLASSIFICATION | EVIDENCE | BACKEND RESPONSIBILITY | IMPLEMENTATION STATUS | RESIDUAL RISK | CONFIDENCE LEVEL |
|---|---|---|---|---|---|---|
| Offline tombstone sync protocol | Backend implemented | [`models/Tombstone.py`](file:///home/ravi/workspace/docker/apps/form-backend/models/Tombstone.py), [`services/tombstone_service.py`](file:///home/ravi/workspace/docker/apps/form-backend/services/tombstone_service.py), [`routes/v1/form/responses.py`](file:///home/ravi/workspace/docker/apps/form-backend/routes/v1/form/responses.py), [`tasks/gdpr_tasks.py`](file:///home/ravi/workspace/docker/apps/form-backend/tasks/gdpr_tasks.py), [`tests/test_tombstone_sync.py`](file:///home/ravi/workspace/docker/apps/form-backend/tests/test_tombstone_sync.py) | Yes | Complete | Client-side Drift reconciliation is outside repo scope | High |
| Analysis run persistence | Backend implemented | [`models/AnalysisRun.py`](file:///home/ravi/workspace/docker/apps/form-backend/models/AnalysisRun.py), [`services/analysis_run_service.py`](file:///home/ravi/workspace/docker/apps/form-backend/services/analysis_run_service.py), [`services/analysis_board_service.py`](file:///home/ravi/workspace/docker/apps/form-backend/services/analysis_board_service.py), [`routes/v1/analysis_board_route.py`](file:///home/ravi/workspace/docker/apps/form-backend/routes/v1/analysis_board_route.py), [`tests/test_analysis_board.py`](file:///home/ravi/workspace/docker/apps/form-backend/tests/test_analysis_board.py) | Yes | Complete | None material beyond normal runtime failures | High |
| Analysis result persistence | Backend implemented | [`models/AnalysisRun.py`](file:///home/ravi/workspace/docker/apps/form-backend/models/AnalysisRun.py), [`services/analysis_board_service.py`](file:///home/ravi/workspace/docker/apps/form-backend/services/analysis_board_service.py), [`tests/test_analysis_board.py`](file:///home/ravi/workspace/docker/apps/form-backend/tests/test_analysis_board.py) | Yes | Complete | Result payload shape depends on node implementations, but contract is stored and queried | High |
| Analysis export metadata persistence | Backend implemented | [`models/AnalysisRun.py`](file:///home/ravi/workspace/docker/apps/form-backend/models/AnalysisRun.py), [`services/analysis_run_service.py`](file:///home/ravi/workspace/docker/apps/form-backend/services/analysis_run_service.py), [`routes/v1/analysis_board_route.py`](file:///home/ravi/workspace/docker/apps/form-backend/routes/v1/analysis_board_route.py), [`tests/test_analysis_board.py`](file:///home/ravi/workspace/docker/apps/form-backend/tests/test_analysis_board.py) | Yes | Complete | Export file generation is still external/boundary-defined | High |
| Analysis export retrieval/download | Backend implemented with documented boundary | [`routes/v1/analysis_board_route.py`](file:///home/ravi/workspace/docker/apps/form-backend/routes/v1/analysis_board_route.py), [`tests/test_analysis_board.py`](file:///home/ravi/workspace/docker/apps/form-backend/tests/test_analysis_board.py) | Yes | Partially implemented with documented residual risk | Requires upstream process to populate `file_path` and mark exports ready | High |
| Analysis export file generation | Partially implemented / backend boundary | Docs: [`docs/07_ANALYSIS_SYSTEM.md`](file:///home/ravi/workspace/form-builder/docs/07_ANALYSIS_SYSTEM.md), [`docs/02_DATABASE_SCHEMA.md`](file:///home/ravi/workspace/form-builder/docs/02_DATABASE_SCHEMA.md); code only persists and downloads ready files | Yes, but generation is not in this repo’s current backend boundary | Partial | No native CSV/Excel/PDF generation task exists in this repo; treated as intentional backend boundary in this audit | Medium |
| Dashboard share/unshare/export contract fixes | Backend implemented | Prior stabilized route/service fixes in dashboard paths, verified through existing test suite | Yes | Complete | Legacy dashboard storage edge cases remain runtime-only | Medium |
| Form version validation hardening | Backend implemented | Prior stabilized form version lookup paths, verified through existing test suite | Yes | Complete | Legacy serialization shapes may still exist in old records | Medium |
| Org/admin error handling | Backend implemented | Prior stabilized org management error paths, verified through existing test suite | Yes | Complete | None material | High |
| Webhook retry/timeout alignment | Backend implemented | Prior stabilized webhook service/task behavior, verified through existing test suite | Yes | Complete | External webhook targets can still fail at runtime | High |
| Notification replay compatibility | Backend implemented | Prior stabilized notification replay / outbox compatibility, verified through existing test suite | Yes | Complete | Replay depends on legacy payloads from historical records | Medium |
| Hook service timeout normalization | Backend implemented | Prior stabilized hook service timeout behavior, verified through existing test suite | Yes | Complete | External hook targets remain runtime-dependent | High |
| Vector provider timeout normalization | Backend implemented | Prior stabilized vector provider path, verified through existing test suite | Yes | Complete | External model service latency remains runtime-dependent | Medium |
| Upload quota enforcement | Backend implemented | [`services/file_storage_service.py`](file:///home/ravi/workspace/docker/apps/form-backend/services/file_storage_service.py), [`tests/test_file_storage_service.py`](file:///home/ravi/workspace/docker/apps/form-backend/tests/test_file_storage_service.py) | Yes | Complete | Quota state depends on external storage consistency | High |
| Upload storage usage recalculation | Backend implemented | [`services/file_storage_service.py`](file:///home/ravi/workspace/docker/apps/form-backend/services/file_storage_service.py), [`tests/test_file_storage_service.py`](file:///home/ravi/workspace/docker/apps/form-backend/tests/test_file_storage_service.py) | Yes | Complete | Directory scan accuracy depends on storage availability | High |
| AI taxonomy compatibility handling | Backend implemented | Prior stabilized AI taxonomy paths, verified through existing test suite | Yes | Complete | Legacy taxonomy payloads may still surface in old jobs | Medium |
| Invitation/group registration fixes | Backend implemented | Prior stabilized invite/group registration paths, verified through existing test suite | Yes | Complete | None material | High |
| Logging bootstrap fallback improvements | Backend implemented | Prior stabilized logging bootstrap paths, verified through existing test suite | Yes | Complete | None material | High |
| AI task runtime paths | Backend implemented / hardened | [`tasks/ai_tasks.py`](file:///home/ravi/workspace/docker/apps/form-backend/tasks/ai_tasks.py), related task tests in Celery suite | Yes | Complete | Still depends on external analytics/OLAP backend for actual export work | Medium |
| Background pipelines and notification replay | Backend implemented / hardened | [`tasks/notification_tasks.py`](file:///home/ravi/workspace/docker/apps/form-backend/tasks/notification_tasks.py), related Celery tests | Yes | Complete | Historical payload compatibility remains a runtime risk | Medium |
| Docs items describing Flutter client rendering, Drift schema, plugin marketplace, UI flows | Frontend/client responsibility | `docs/10_OFFLINE_SYNC.md`, `docs/09_COMPONENT_LIBRARY.md`, `docs/05_PLUGIN_SYSTEM.md`, and UI-heavy sections in the docs set | No | Out of scope | No backend change required | High |
| Docs items describing roadmap/future-state architecture not started in backend | Future roadmap | Roadmap / future-state sections in docs | Sometimes backend-adjacent, but intentionally not started | Out of scope | No backend action required for this repo audit | High |

**System-wide verification status**

- Backend-relevant documentation items are now classified and accounted for.
- Implemented backend items are covered by compile, lint, and targeted pytest runs from the earlier passes:
  - `python3 -m compileall` passed on changed files across the stabilization passes.
  - `git diff --check` passed after each batch.
  - Targeted pytest runs passed for:
    - `tests/test_tombstone_sync.py`
    - `tests/test_analysis_board.py`
    - `tests/test_file_storage_service.py`
- The only remaining backend gap with evidence is analysis export file generation. It is not a wiring bug; it is a boundary decision. The repo now supports metadata persistence, retrieval, and download of ready export files, but does not generate the artifact itself.

**Residual risks**

- Analysis export generation remains external or future-boundary scoped.
- Tombstone-based offline sync still depends on client-side reconciliation logic outside this repo.
- Historical payload compatibility in legacy notification and analysis records can still surface edge cases at runtime, but the implemented handlers are designed to tolerate them.

**Confidence levels**

- Core backend docs compliance: **High**
- Export lifecycle completeness: **Medium** because generation is intentionally outside the current backend boundary
- Overall release handoff confidence: **High** for implemented paths, **Medium** for the boundary-limited export layer

No additional actionable backend-docs items remain unclassified in a way that would require new architecture in this repository.
