# RAOS Analysis Job Continuity — Result

Status: **DOGFOOD READY**  
Date: 2026-09-18

A real Reader workflow exposed that async cognition status was held only in React memory. Refreshing an unanalyzed Source during a running job therefore made the Analyze button appear idle again even though backend cognition was still active.

The fix establishes one source-level authoritative cognition lease:

```text
one current Source
→ at most one QUEUED/RUNNING authoritative cognition job
→ Analyze and Reprocess share the same lease
```

Backend now exposes the active job by Source and deduplicates Analyze/Reprocess against the same source-level lease. Frontend reloads both the latest completed AnalysisRun and any active job on page initialization, automatically resumes polling after refresh, and keeps Analyze/Reprocess disabled until the active job completes or fails.

The existing AnalysisRun identity uniqueness remains defense-in-depth; token conservation no longer depends on reaching that lower DB guard.

Validation:

```text
analysis-job focused tests: 5 passed
Phase13 + acquisition/Reader focused tests: 33 passed
frontend typecheck: PASS
frontend production build: PASS
full backend: 838 passed / 63 skipped / 1 known Case-K residual
runtime: CANONICAL / ATTESTED / READY
```

Current limitation: the job registry is process-local. Browser refresh and multi-tab continuity are fixed; production/private-beta process-restart durability should move analysis jobs to durable storage rather than treating in-process memory as the long-term job ledger.

Frozen principle:

> **Cognition is background OS work. Its truth must not depend on one browser tab remaining alive, and one Source must not spend the same cognition budget twice concurrently.**
