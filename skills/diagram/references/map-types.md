# Map Types — Reference Guide

Map-type-specific guidance. Load this when building a specific kind of map and you need to know what to capture, what to probe for, and what to flag as risk.

Use the table of contents to jump to the relevant section. Don't read end-to-end.

## Table of Contents

- [Lead Routing](#lead-routing)
- [Data Flow Diagrams (DFD)](#data-flow-diagrams-dfd)
- [Incident Management](#incident-management)
- [Change Management](#change-management)
- [User Workflows](#user-workflows)
- [A/B Test / Experiment Maps](#ab-test--experiment-maps)
- [System Architecture Handoffs](#system-architecture-handoffs)

---

## Lead Routing

### Capture

- Trigger / source (form, import, partner API)
- Enrichment steps (data appended before routing)
- Dedupe / merge logic (which fields match; merge priority)
- Assignment rules hierarchy (top-down ladder of decisions)
- Exceptions and fallback routing
- Re-assignment conditions
- SLA expectations (response time, escalation triggers)
- Audit trail (which system stores what)

### Always probe for

- Unique identifiers used for matching
- Match logic (email exact vs. fuzzy, company_id, domain match)
- Ownership fields (Owner, AE_Owner_Id, Round_Robin_Pool)
- Routing priority order (what wins when multiple rules match)
- Missing-data handling (does a null field fail the rule, or proceed?)
- Out-of-hours behavior
- Compliance / consent constraints (GDPR opt-out, CASL, etc.)

### Always flag

- Duplicate risk (no unique key gate)
- Conflicting assignment criteria (two rules both fire)
- No fallback queue (a record could be unassigned forever)
- Undefined SLA
- Asymmetry between create-triggered and update-triggered branches (a common bug pattern: the create flow excludes a population but the update flow doesn't)

### Suggested lane pattern

Function lanes (Entry, Match, Enrich, Decide, Route/Assign, Cadence/Notify, Write) for routing-heavy maps inside a single CRM. Use the `horizontal_7_lane_functional_routing` preset.

---

## Data Flow Diagrams (DFD)

### Confirm level first

If the user hasn't specified, ask: "Should this be a level 0 (context), level 1 (system decomposition), or level 2 (detailed events) DFD?"

**Level 0:** External entities, core systems, and major data flows only. Aim for fewer than 10 nodes.

**Level 1:** Decompose major processes into sub-processes. Include data stores and key transformations. 15–30 nodes.

**Level 2:** Include key API calls and event names. Include queues, staging layers, retry logic, and failure handling. 30–50 nodes; consider splitting.

### Always label flows

Each connector should carry the type of data crossing it (e.g., "Lead Create Event", "Webhook Payload", "Bulk Sync File"). Use the `connect(label=...)` parameter.

### Always probe for

- Source of truth for each data type
- Sync direction (one-way push, two-way, periodic batch)
- Frequency (real-time, near-real-time, hourly, daily batch)
- Authentication method (internal audience only — OAuth, API key, IP allowlist)
- Observability (logs, alerts, traces — and who owns them)

### Suggested lane pattern

System lanes when crossing platforms; vertical orientation if time flows top-to-bottom feels more natural (e.g., a sync pipeline). Use the `vertical_3_lane_dfd` preset for source-transform-destination flows.

---

## Incident Management

### Capture

- Detection (how is the incident first known?)
- Severity classification (Sev1/2/3 thresholds)
- Triage (who picks it up first; how it's prioritized)
- Escalation (when and to whom)
- Communication (internal Slack channels, status page, customer comms)
- Mitigation (immediate steps to reduce impact)
- Resolution (root cause fixed; verified by whom)
- Postmortem (template, deadline, attendees)
- Follow-up actions (Jira tickets, runbook updates)

### Define roles

- Incident Commander (one person, decisions and coordination)
- SMEs (subject matter experts pulled in based on system)
- Communications lead (handles status updates, customer comms)
- Scribe (records timeline)

### Always probe for

- SLAs (acknowledgment time, mitigation time, resolution time by severity)
- After-hours coverage (who's on-call, rotation schedule, paging tool)
- Customer-impact thresholds (when do external comms start)
- Postmortem cadence and visibility

### Suggested lane pattern

Function lanes (Detect, Triage, Mitigate, Communicate, Resolve, Postmortem) work well. System lanes if the incident response crosses tools (PagerDuty → Slack → Statuspage → Jira).

---

## Change Management

### Capture

- Intake (where change requests originate, format)
- Impact assessment (who reviews, what gets evaluated)
- Risk classification (low/medium/high; what each means)
- Approvals (who must approve at each risk level)
- Testing (what gets tested, by whom, in what environment)
- Rollout plan (phased? all-at-once? canary?)
- Backout plan (how to revert; tested?)
- Communications (when stakeholders are told)
- Documentation updates (runbooks, wikis, training materials)
- Change window (timing constraints; freeze periods)

### Always probe for

- Approval matrix (who can approve what)
- Emergency change process (bypassing normal approvals)
- Standard vs. major change distinction
- Post-implementation review trigger

### Suggested lane pattern

Function lanes (Intake, Assess, Approve, Test, Deploy, Verify, Communicate) for the full lifecycle. Use the `horizontal_7_lane_functional_routing` preset, retitling lanes.

---

## User Workflows

### Separate two layers

- **User-visible steps:** what the user does and sees on screen
- **Behind-the-scenes system steps:** what the system does in response

The lanes should reflect this separation. Use two lanes minimum (User, System) or expand to more if multiple backend systems are involved.

### Capture

- Entry point (URL, button click, deep link)
- Required inputs at each step (what the user must provide)
- Success outcome (what defines a complete journey)
- Failure paths (what happens when the user enters bad data, abandons, times out)
- Re-entry behavior (can the user resume mid-flow?)

### Suggested lane pattern

System lanes with at least 2 lanes (User-facing, Backend). Use the `horizontal_2_lane_system_handoff` preset or expand to 3–4 lanes for multi-backend flows.

---

## A/B Test / Experiment Maps

This is a specialized variant that gets common patterns wrong if not handled deliberately.

### Always include

- **The assignment mechanism** as its own node, ideally in its own lane (e.g., a LaunchDarkly lane between the user-facing system and the backend). Don't bury the assignment inside another node.
- **Both arms explicitly.** Don't show just the variation arm and imply the control. Each arm gets its own path through the map, even when much of the path is shared.
- **The excluded population.** Who is NOT in the experiment? Show them as an out-of-scope branch with a red `out_of_scope` node. This makes it clear who is and isn't subject to the test.
- **The experiment field names** in the relevant data-write nodes. Common names: `experiment_name`, `experiment_variant` or `experiment_arm`, plus any experiment-specific data fields.
- **Which downstream systems receive the experiment fields.** The fields need to land in analytics, CRM, and data warehouse for the readout to work.

### Always flag

- **Observability gaps in the assignment mechanism.** Feature flags often assign without emitting an assignment event. If no event is logged, downstream analytics can't reconcile who got which variant. This is the #1 silent failure mode.
- **Multi-experiment interactions.** When two experiments run on overlapping audiences at the same time, explicitly map the interaction logic: mutual exclusion, priority order, or both-fire-independently behavior. If the user hasn't decided, surface it as an open question.
- **Naming inconsistencies** between PRDs, code, and data warehouse (e.g., PRD says `experiment_arm` but the code writes `experiment_variant`).
- **Dedupe gaps in experiment-tracking arrays.** If your CRM stores experiments as an array attribute, check whether the workflow that appends to it deduplicates.

### Suggested lane pattern

System lanes when the experiment crosses platforms (Prospect/Browser, LaunchDarkly, Customer.io, CRM, Salesforce). Use the `horizontal_5_lane_system_end_to_end` preset.

---

## System Architecture Handoffs

For maps showing how data or control flows between systems (the user submits something, system A receives, processes, hands to B, etc.).

### Capture

- Each system's role (transport, validation, transformation, persistence)
- Handoff trigger (sync API call, async event, scheduled job)
- Handoff payload (what data crosses; mention only the key fields, not the whole schema)
- Error handling at each handoff (retry, dead-letter queue, alerting)
- Idempotency (can this handoff fire twice safely?)

### Always probe for

- Authentication on each handoff (audience-dependent)
- Latency budget per hop
- Total end-to-end SLA
- Observability (which hops emit traces / logs / metrics)

### Suggested lane pattern

System lanes, one per platform. Use the `horizontal_2_lane_system_handoff` preset for two systems, or `horizontal_5_lane_system_end_to_end` for up to five.

---

## Cross-cutting: when to use system vs. function lanes

| Map characteristic | Use system lanes | Use function lanes |
|--------------------|------------------|--------------------|
| Crosses multiple platforms (CRM, marketing automation, analytics) | ✓ | |
| Most steps live in one system | | ✓ |
| Question is "which system owns which step" | ✓ | |
| Question is "what phase of work is each step" | | ✓ |
| Routing/decision-heavy | | ✓ |
| Lifecycle / handoff focused | ✓ | |

Never mix the two patterns in one map. Pick one before placing nodes.
