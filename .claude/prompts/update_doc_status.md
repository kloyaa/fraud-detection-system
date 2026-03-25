# Prompt: Update Documentation Status
## Risk Assessment System (RAS)

---

## Purpose

Run this prompt after any implementation is completed to update
the status of all affected documentation. This ensures docs
reflect reality — not design intent.

---

## Usage

```bash
# After completing a task, run:
claude < .claude/prompts/update_doc_status.md

# Or inline:
"@<agent> — mark <component> as implemented and
 update all affected docs"
```

---

## Your Task

You have just completed an implementation. Update every affected
document in the project to reflect the new status.

---

## Status Values

Use exactly these values — no others:

| Status | Meaning |
|---|---|
| `⏳ Planned` | Designed but not yet implemented |
| `🔨 In Progress` | Implementation started, not complete |
| `✅ Implemented` | Code written, tests passing, merged to main |
| `✅ Verified` | Implemented AND verified in staging environment |
| `✅ Live` | Running in production |
| `❌ Blocked` | Cannot proceed — blocker documented |
| `🔴 Open` | Issue/gap that needs resolution |
| `✅ Resolved` | Issue closed with evidence |
| `✅ Accepted` | ADR decision accepted (ADRs only — never changes) |
| `🔵 N/A` | Not applicable to this system |

---

## Step-by-Step Instructions

### Step 1 — Identify What Was Implemented

State clearly:
- What component / feature / control was implemented
- Which files were changed (code + tests)
- What evidence exists (test run, PR number, commit hash)

### Step 2 — Find All Affected Documents

Search every document in the CLAUDE.md File Index for references
to the implemented component. Look for:

```
- Any row in a status table containing the component name
- Any ⏳ Planned or 🔨 In Progress status for this component
- Any open issue (ISS-*) related to this component
- Any PRR blocker (B-*) that this resolves
- Any CLAUDE.md sprint task for this component
```

### Step 3 — Update Each Document

For each affected document:

1. Change the status field from `⏳ Planned` → `✅ Implemented`
2. Add an evidence line beneath the status:
   ```
   Evidence: PR #<number> · commit <sha> · tests passing
   ```
3. If it resolves an open issue, update in CLAUDE.md:
   ```
   ISS-XXX: <description> | ✅ Resolved | PR #<number>
   ```
4. If it clears a PRR blocker, update in CLAUDE.md:
   ```
   B-XXX: <description> | ✅ Cleared | PR #<number>
   ```
5. Update the CLAUDE.md sprint task:
   ```
   - [x] <task description> ← @<agent> PR #<number>
   ```

### Step 4 — Update CLAUDE.md File Index

Mark the document as updated:
```
docs/security/encryption_spec.md   ✅ (updated Sprint X)
```

### Step 5 — Output a Change Summary

After all updates, output:

```
## Status Update Summary

Component:    <what was implemented>
Evidence:     PR #<n> · <commit-sha> · <test run link>

Documents updated:
  ✅ CLAUDE.md — ISS-XXX resolved, sprint task checked
  ✅ docs/security/encryption_spec.md — §2.2 status updated
  ✅ docs/compliance/pci_dss_controls.md — Req X.Y status updated
  ✅ docs/quality/prr_checklist.md — Gate X.X passed

PRR blockers cleared:    B-XXX (if applicable)
Issues resolved:         ISS-XXX (if applicable)
Next PRR gate:           <what needs to happen next>
```

---

## Rules

- **Never mark something `✅ Implemented` without evidence**
  (PR number, commit hash, or test run output)
- **Never mark `✅ Verified` without a staging test result**
- **Never mark `✅ Live` without a production deployment confirmation**
- **Always update CLAUDE.md** — it is the source of truth for project state
- **ADR statuses never change** — `✅ Accepted` is permanent
- **Do not update docs you did not search** — only update what you can confirm