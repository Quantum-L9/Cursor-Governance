---
name: Complete Self-Reflection Action Layer
overview: "Complete the 5 remaining tasks for self-reflection governance tracking: severity escalation, user correction detection, Slack notifications, API endpoints, and ApprovalManager integration."
todos:
  - id: severity-escalation
    content: Implement severity escalation in GovernanceBlockPattern - add _calculate_severity() method and replace hardcoded LOW severity
    status: pending
  - id: slack-notifications
    content: Add Slack notification when evolution plans require approval - wire Slack client into create_evolution_plan()
    status: pending
  - id: api-endpoints
    content: Create API endpoints for evolution plan management - new file api/routes/evolution.py with list, get, approve, reject endpoints
    status: pending
  - id: approval-manager
    content: Extend ApprovalManager with evolution approval methods - request_evolution_approval() and check_evolution_approved()
    status: pending
  - id: user-correction-detection
    content: Wire user correction detection in conversation handlers - commands.py, webhook_slack.py, task_router.py, slack_ingest.py
    status: pending
---

# Complete Self-Reflection Governance Tracking Action Layer

## Overview

Complete the action layer for self-reflection governance tracking system. The data flow is complete (governance blocks and user corrections are tracked), but the action handlers are missing.

## Current State

**Completed:**

- Schema updates (`ExecutionResult` has `governance_blocks` and `user_corrections`)
- AgentInstance tracking methods (`add_governance_block()`, `add_user_correction()`)
- Executor integration (blocks tracked during execution)
- Self-reflection patterns (detect gaps, but severity always LOW)
- Integration tests (20 tests passing)

**Missing:**

1. Severity escalation in `GovernanceBlockPattern` (hardcoded to "LOW")
2. User correction detection from conversation handlers
3. Slack notifications for evolution plans
4. API endpoints for evolution plan management
5. ApprovalManager integration for evolution approvals

---

## Task 1: Severity Escalation in GovernanceBlockPattern

**File:** [`core/agents/selfreflection.py`](core/agents/selfreflection.py)

**Current Issue:** Line 192 hardcodes `severity="LOW"`, so evolution plans rarely trigger (requires HIGH/CRITICAL).

**Changes:**

1. Add `_calculate_severity()` method to `GovernanceBlockPattern` class
2. Replace hardcoded `severity="LOW"` with dynamic calculation
3. Escalation logic:

   - `HIGH`: ≥5 blocks OR any safety_block OR ≥3 blocks with "denied" in reason
   - `MEDIUM`: 3-4 blocks OR any authority_block
   - `LOW`: 1-2 blocks (non-safety, non-authority)

**Code Location:**

- Lines 168-202: `GovernanceBlockPattern` class
- Replace line 192: `severity="LOW"` → `severity=self._calculate_severity(legitimate_blocks)`

**Impact:** Enables evolution plans to trigger when governance blocks accumulate.

---

## Task 2: User Correction Detection from Conversation Layer

**Files to Modify:**

- [`api/routes/commands.py`](api/routes/commands.py) - Command execution handler
- [`api/webhook_slack.py`](api/webhook_slack.py) - Slack webhook handler
- [`orchestration/task_router.py`](orchestration/task_router.py) - Task routing
- [`memory/slack_ingest.py`](memory/slack_ingest.py) - Slack message ingestion

**Challenge:** Need to access `AgentInstance` from conversation handlers.

**Solution:**

1. Store `AgentInstance` reference in task context/metadata
2. Add correction detection helper function
3. Wire detection in each handler

**Detection Patterns:**

- Keywords: "no", "stop", "instead", "actually", "don't", "wrong", "should be", "correction"
- User edits that override agent output
- User interrupts mid-execution

**Implementation:**

1. Create `detect_user_correction()` helper in `core/agents/agent_instance.py` or new utility module
2. In each handler, after user message processing:

   - Check if correction patterns detected
   - If `AgentInstance` available in context, call `instance.add_user_correction()`
   - If not available, store correction in task metadata for later retrieval

**Code Locations:**

- `api/routes/commands.py`: After command execution (around line 290)
- `api/webhook_slack.py`: After Slack message processing (around line 700)
- `orchestration/task_router.py`: In task routing logic
- `memory/slack_ingest.py`: In `_index_slack_conversation()` (already extracts corrections, needs wiring)

**Note:** May need to pass `AgentInstance` through task context or retrieve from executor service.

---

## Task 3: Slack Notification for Evolution Plans

**Files to Modify:**

- [`core/agents/kernelevolution.py`](core/agents/kernelevolution.py) - Evolution plan creation
- [`core/agents/executor.py`](core/agents/executor.py) - Self-reflection execution

**Current State:** Evolution plans are created and persisted, but no Slack notification sent.

**Implementation:**

1. Add Slack client parameter to `create_evolution_plan()` function
2. After plan creation (line 384), if `requires_igor_approval=True`, send notification
3. Notification format:
   ```
   🧬 *Kernel Evolution Plan Requires Approval*
   • Plan ID: {plan_id}
   • Agent: {agent_id}
   • Impact: {estimated_impact}
   • Proposals: {proposal_count}
   • Gaps Addressed: {total_gaps_addressed}

   Review: `/api/evolution/plans/{plan_id}`
   Approve: `/api/evolution/plans/{plan_id}/approve`
   ```


**Code Locations:**

- `core/agents/kernelevolution.py`: Line 292-384 (`create_evolution_plan()`)
- `core/agents/executor.py`: Line 1798-1823 (where `create_evolution_plan()` is called)

**Dependencies:**

- Need Slack client available in executor context
- Check if `services/slack_client.py` has async notification method
- May need to inject Slack client into `AgentExecutorService.__init__()`

---

## Task 4: API Endpoints for Evolution Plan Management

**New File:** [`api/routes/evolution.py`](api/routes/evolution.py)

**Endpoints to Create:**

1. `GET /api/evolution/plans` - List evolution plans (with status filter)
2. `GET /api/evolution/plans/{plan_id}` - Get plan details
3. `POST /api/evolution/plans/{plan_id}/approve` - Approve plan
4. `POST /api/evolution/plans/{plan_id}/reject` - Reject plan
5. `GET /api/evolution/plans/{plan_id}/gmp-spec` - Get GMP spec for plan

**Implementation:**

1. Create new route file `api/routes/evolution.py`
2. Add Pydantic models for request/response:

   - `EvolutionPlanResponse`
   - `EvolutionPlanListResponse`
   - `ApprovePlanRequest`
   - `RejectPlanRequest`

3. Query evolution plans from memory substrate (packet type: `kernel.evolution.plan`)
4. Store approval/rejection decisions in substrate (packet type: `kernel.evolution.approval`)
5. Register routes in main API router

**Code Structure:**

```python
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from core.agents.kernelevolution import EvolutionPlan
from memory.substrate_service import MemorySubstrateService

router = APIRouter(prefix="/api/evolution", tags=["evolution"])

@router.get("/plans")
async def list_evolution_plans(
    status: Optional[str] = "pending",
    substrate_service: MemorySubstrateService = Depends(get_substrate_service),
) -> EvolutionPlanListResponse:
    """List evolution plans filtered by status."""
    ...

@router.get("/plans/{plan_id}")
async def get_evolution_plan(
    plan_id: str,
    substrate_service: MemorySubstrateService = Depends(get_substrate_service),
) -> EvolutionPlanResponse:
    """Get evolution plan details."""
    ...

@router.post("/plans/{plan_id}/approve")
async def approve_evolution_plan(
    plan_id: str,
    request: ApprovePlanRequest,
    substrate_service: MemorySubstrateService = Depends(get_substrate_service),
) -> dict:
    """Approve an evolution plan."""
    ...

@router.post("/plans/{plan_id}/reject")
async def reject_evolution_plan(
    plan_id: str,
    request: RejectPlanRequest,
    substrate_service: MemorySubstrateService = Depends(get_substrate_service),
) -> dict:
    """Reject an evolution plan."""
    ...
```

**Integration:**

- Register router in main API app (likely `api/server.py` or `api/router.py`)
- Add dependency injection for `MemorySubstrateService`

---

## Task 5: ApprovalManager Integration for Evolution

**Files to Modify:**

- [`core/governance/approval_manager.py`](core/governance/approval_manager.py) - Extend ApprovalManager
- [`core/agents/kernelevolution.py`](core/agents/kernelevolution.py) - Use ApprovalManager

**Current State:** `ApprovalManager` handles tool execution approval, but not kernel evolution.

**Implementation Options:**

1. **Option A:** Extend existing `ApprovalManager` with evolution methods
2. **Option B:** Create `EvolutionApprovalManager` subclass
3. **Option C:** Add evolution approval to existing `request_approval()` method

**Recommended:** Option A (extend existing class)

**Changes:**

1. Add `request_evolution_approval()` method to `ApprovalManager`
2. Add `check_evolution_approved()` method
3. Store evolution approvals in substrate (packet type: `kernel.evolution.approval`)
4. Update `create_evolution_plan()` to use ApprovalManager if available
5. Wire ApprovalManager into executor service

**Code Locations:**

- `core/governance/approval_manager.py`: Add methods after line 367
- `core/agents/kernelevolution.py`: Update `create_evolution_plan()` to check/request approval
- `core/agents/executor.py`: Pass ApprovalManager to evolution plan creation

**Approval Flow:**

1. Evolution plan created → `requires_igor_approval=True`
2. `ApprovalManager.request_evolution_approval()` called
3. Approval request stored in substrate
4. Slack notification sent (via Task 3)
5. Igor approves via API (Task 4) or Slack command
6. Approval stored, plan marked as approved
7. Future kernel hot-reload can check approval status

---

## Implementation Order

1. **Task 1** (Severity Escalation) - Simplest, unblocks evolution plan triggering
2. **Task 3** (Slack Notifications) - Requires Task 1 to see notifications
3. **Task 4** (API Endpoints) - Enables manual plan review
4. **Task 5** (ApprovalManager) - Integrates with API endpoints
5. **Task 2** (User Corrections) - Most complex, requires context passing

---

## Testing Strategy

**Unit Tests:**

- `GovernanceBlockPattern._calculate_severity()` with various block counts/types
- User correction detection patterns
- Evolution plan API endpoints

**Integration Tests:**

- End-to-end: governance block → severity escalation → evolution plan → Slack notification
- User correction → tracked → self-reflection → evolution plan
- API approval flow: create plan → approve → verify approval status

**Test Files:**

- `tests/unit/test_governance_block_severity.py` (new)
- `tests/integration/test_evolution_plan_api.py` (new)
- `tests/integration/test_user_correction_detection.py` (new)
- Update: `tests/integration/test_governance_tracking_e2e.py`

---

## Dependencies & Prerequisites

**Required:**

- Slack client available in executor context
- Memory substrate service for querying evolution plans
- FastAPI router registration mechanism

**Optional:**

- Slack command handler for `/approve-evolution {plan_id}` (future enhancement)

---

## Success Criteria

1. Governance blocks escalate to HIGH severity when thresholds met
2. User corrections detected and tracked from all conversation handlers
3. Slack notifications sent when evolution plans require approval
4. API endpoints allow listing, viewing, approving, and rejecting plans
5. ApprovalManager handles evolution plan approvals
6. All integration tests pass
7. Evolution plans trigger kernel update proposals when appropriate

---

## Files Summary

**Modify:**

- `core/agents/selfreflection.py` - Severity escalation
- `core/agents/kernelevolution.py` - Slack notifications, ApprovalManager integration
- `core/agents/executor.py` - Pass Slack client, ApprovalManager
- `core/governance/approval_manager.py` - Evolution approval methods
- `api/routes/commands.py` - User correction detection
- `api/webhook_slack.py` - User correction detection
- `orchestration/task_router.py` - User correction detection
- `memory/slack_ingest.py` - Wire existing correction extraction

**Create:**

- `api/routes/evolution.py` - Evolution plan API endpoints
- `tests/unit/test_governance_block_severity.py` - Severity tests
- `tests/integration/test_evolution_plan_api.py` - API tests
- `tests/integration/test_user_correction_detection.py` - Detection tests

**Update:**

- `tests/integration/test_governance_tracking_e2e.py` - Add new test cases
