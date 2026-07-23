# ChatBI Qualification and Source-Aware Routing Implementation Plan

> **For agentic workers:** Execute this plan inline with test-first checkpoints. Preserve existing `data_query` configuration as a compatibility value.

**Goal:** Prevent action words such as “统计” and “可视化” from opening ChatBI unless the request domain and evidence identify ChatBI business data.

**Architecture:** Keep `DATA_QUERY/data_query` backward-compatible, but add operation/domain/evidence semantics and a `DIRECT/CLARIFY/DENY` ChatBI qualification. Use authorized dataset metadata/vector candidates and previous-result provenance as evidence; pass one canonical decision through Router, Dispatcher, AssistantAgentRunner, and Tool Nudge.

**Tech Stack:** Python, Pydantic, dataclasses, existing AgentScope routing, existing metadata/vector search, pytest.

---

### Task 1: Define source-aware intent output

**Files:**
- Modify: `app/services/ai/intent_service.py`
- Modify: `app/services/ai/request_decision.py`
- Test: `tests/ai/test_request_decision.py`

- [ ] Add optional `operation`, `domain`, and `target_kind` fields to `IntentResponse`, preserving existing four-value `IntentType` parsing.
- [ ] Update the intent prompt so `DATA_QUERY` explicitly means ChatBI business data and examples distinguish machine files/runtime state from business records.
- [ ] Add a ChatBI qualification model with `DIRECT`, `CLARIFY`, and `DENY` modes to the request-decision layer.
- [ ] Add tests proving `统计一下我机器的文件数` is not ChatBI even when semantic evidence is `DATA_QUERY`, while `统计客户订单数量` remains eligible.

### Task 2: Build authorized dataset evidence

**Files:**
- Create: `app/services/ai/chatbi_qualification.py`
- Modify: `app/services/ai/metadata_index_service.py` only if a small adapter is required
- Test: `tests/ai/test_chatbi_qualification.py`

- [ ] Build a query-facing dataset candidate adapter over the existing permission-filtered metadata/vector index; do not inject the entire `dataset_menu` into the router prompt.
- [ ] Return top-k authorized dataset candidates with score, dataset id, display name, and matched metadata text.
- [ ] Classify evidence as direct when a prior ChatBI result, explicit dataset selection, portal command, or high-scoring authorized dataset candidate exists; classify ambiguous business-data requests as clarify; classify runtime/file/web/docs or no-evidence requests as deny.
- [ ] Test authorized dataset matches, empty menu/index, runtime/file mismatch, and permission filtering.

### Task 3: Apply one ChatBI gate to routing and execution

**Files:**
- Modify: `app/services/ai/turn_classifier.py`
- Modify: `app/services/ai/router_service.py`
- Modify: `app/services/ai/dispatcher.py` only if decision propagation requires it
- Modify: `app/services/ai/tool_nudge_policy.py`
- Modify: `app/services/ai/runners/assistant_agent_runner.py`
- Test: `tests/ai/test_turn_classifier.py`, `tests/ai/test_router_context.py`, `tests/ai/test_tool_nudge_policy.py`

- [ ] Compute qualification once in the async session-classification path and pass it downward instead of re-inferring from action keywords.
- [ ] Narrow Router candidates to ChatBI agents only for `DIRECT`; allow `CLARIFY` without forced delegation; exclude ChatBI for `DENY`.
- [ ] Make Tool Nudge force `sub_agent_call` only for `DIRECT`; route `CLARIFY` to clarification and `DENY` to runtime/file/web/general tools.
- [ ] Preserve ChatBI follow-up behavior only when previous-result provenance is ChatBI; preserve runtime/file provenance for their visualization follow-ups.
- [ ] Add end-to-end boundary tests for business aggregation, machine file counts, runtime load, public-web visualization, and previous ChatBI visualization.

### Task 4: Verify compatibility and diagnostics

**Files:**
- Modify: `tests/CHECKLIST.md` if the repository checklist requires a new routing contract row
- Test: focused routing, decision, nudge, dispatcher, and sub-agent suites

- [ ] Run the new qualification tests first and observe red before implementation.
- [ ] Run focused routing and execution tests after each gate change.
- [ ] Run `git diff --check` and report unrelated user files such as `temp.md` without editing them.

