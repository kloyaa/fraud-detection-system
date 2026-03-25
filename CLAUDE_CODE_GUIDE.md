# Claude Code Guide
## How to Use Claude Code with RAS Multi-Agent System

```yaml
document:       docs/guides/claude_code_guide.md
audience:       All RAS engineers
last_updated:   Pre-development
```

---

## 1. What Is Claude Code?

Claude Code is a CLI tool that runs Claude directly in your terminal, with full access to your codebase. It can read files, write code, run commands, and execute multi-step tasks autonomously.

```bash
# Install
npm install -g @anthropic-ai/claude-code

# Run from your project root
cd risk-assessment-system
claude
```

When you run `claude` from the project root, it **automatically reads `CLAUDE.md`** — which means it instantly knows:
- All 8 agents and their domains
- The full technology stack
- All ADRs and open issues
- The current sprint state
- How to route questions to the right agent

---

## 2. How CLAUDE.md Works

```
You open terminal
      │
      ▼
claude (CLI starts)
      │
      ▼
Reads CLAUDE.md automatically ← This is the brain
      │
      ▼
Knows: all agents, stack, ADRs,
       open issues, routing rules
      │
      ▼
You talk to it — it routes to
the right agent automatically
```

Think of `CLAUDE.md` as the **system prompt** for your entire project. Every Claude Code session starts with full project context.

---

## 3. Invoking Agents

### 3.1 Automatic Routing

Just ask naturally — Claude Code reads the keyword routing table in `CLAUDE.md` and responds as the right agent:

```bash
# These automatically invoke @marcus
"Why did we choose Cassandra over PostgreSQL for the event log?"
"What's the Kafka partition strategy for risk.decisions?"

# These automatically invoke @priya
"How does envelope encryption work in our system?"
"Is our JWT configuration PCI DSS compliant?"

# These automatically invoke @yuki
"What features does the fraud scorer use?"
"How do we handle class imbalance in training?"

# These automatically invoke @sofia
"How should I implement the idempotency key middleware?"
"There's an N+1 query in the cases endpoint — fix it"

# These automatically invoke @elena
"Scaffold the Next.js dashboard page for case management"
"What's the correct rendering strategy for the queue page?"
```

### 3.2 Explicit Agent Invocation

Use the `@handle` syntax to force a specific agent:

```bash
"@priya review this JWT validation code"
"@darius what's the blast radius if Redis goes down?"
"@james does this data retention period satisfy BSA requirements?"
"@aisha what tests are missing from this PR?"
"@elena build the SHAP chart component"
```

### 3.3 Multi-Agent Invocation

Ask multiple agents to weigh in on the same problem:

```bash
"@marcus @priya @darius — design the mTLS configuration
 for the scoring API pods"

"@sofia @aisha — review this FastAPI endpoint for
 correctness and test coverage"

"@yuki @james — does this new feature require a
 compliance review before Feast registration?"
```

Claude Code will respond with each agent's perspective in sequence, clearly labelled.

---

## 4. Using Slash Commands

The `.claude/commands/` files define custom slash commands. Use them directly:

```bash
/score debug
# → Full pipeline trace of a scoring request
# → @sofia, @yuki, @marcus each annotate their layer

/score simulate velocity_attack
# → @yuki generates a realistic fraud scenario payload
# → Runs through full scoring pipeline in debug mode

/review queue
# → @sofia queries case management API
# → @james annotates compliance flags

/review case case_00318
# → Full case investigation view
# → All agents contribute their domain perspective

/ppr run
# → @aisha orchestrates full PRR checklist
# → All agents run their owned sections

/ppr status
# → Current go/no-go status across all 6 sections
```

---

## 5. Using Agent Prompts

The `.claude/prompts/` directory contains ready-to-use task prompts. Load them like this:

```bash
# Run Elena's frontend kickoff
claude < .claude/prompts/elena_frontend_kickoff.md

# Reset all document statuses to pre-development
claude < .claude/prompts/reset_to_pre_development.md
```

Or paste the prompt content directly into the Claude Code session.

---

## 6. How Agents Interact With Each Other

Agents don't run in separate processes — they are **personas that Claude Code adopts** based on context. Here's how cross-agent collaboration works in practice:

### 6.1 Sequential Handoff

```
You: "@sofia implement the idempotency middleware.
      @priya review it for security after."

Claude Code:

### 🖥️ Sofia Martínez — Senior Backend Engineer
[writes the implementation]

### 🔐 Priya Nair — Principal Security Engineer
[reviews Sofia's code, flags timing attack risk in
 comparison, recommends hmac.compare_digest]
```

### 6.2 Blocking Handoff (One Agent Depends on Another)

```
You: "Design the ML feature pipeline"

@marcus: "Here is the Kafka → Flink → Feast topology..."
  └─► @yuki picks up: "Given Marcus's topology, here are
      the Feast feature view definitions..."
        └─► @darius picks up: "Given Yuki's Flink job,
            here is the Kubernetes deployment config..."
```

### 6.3 Disagreement Protocol

Agents can and will push back on each other:

```
You: "Should we add Redis caching in front of the rule DB?"

@sofia: "Here's how I'd implement it..."

@marcus: "I disagree with Sofia's approach here.
          Redis TTL creates a stale rule window.
          The correct pattern per ADR-008 is Kafka-based
          distribution. Here's why..."

@priya: "Both of you — this cache also introduces
         a new attack surface. If we do implement it,
         here are the security requirements..."
```

### 6.4 PRR Cross-Agent Gate

```
You: "/ppr run"

@aisha runs each section and invokes section owners:
  Section 1 → @sofia provides coverage report
  Section 2 → @darius provides load test results
  Section 3 → @darius provides chaos experiment evidence
  Section 4 → @priya provides security scan results
  Section 5 → @darius provides observability evidence
  Section 6 → @james provides compliance sign-off

@aisha collects all results → issues GO / NO-GO
```

---

## 7. Practical Workflows

### 7.1 Starting a New Feature

```bash
# 1. Get architecture guidance
"@marcus — I need to add a new real-time feature:
 merchant_chargeback_rate_1h. Where does it fit in the pipeline?"

# 2. Get compliance approval
"@james @priya — does merchant_chargeback_rate_1h
 require a compliance review before Feast registration?"

# 3. Implement feature definition
"@yuki — write the Feast feature view definition
 for merchant_chargeback_rate_1h"

# 4. Implement Flink job
"@yuki @sofia — write the Flink operator for
 computing merchant_chargeback_rate_1h"

# 5. Add tests
"@aisha — write pytest unit tests for the new
 velocity feature computation"

# 6. Update catalog
"@yuki — update docs/ml/feature_catalog.md
 with the new feature definition"
```

### 7.2 Investigating a Production Issue

```bash
# Simulate an incident
"@darius — P1 alert: scoring API P95 is 187ms.
 Walk me through the diagnosis"

# Darius runs through scoring_api_latency.md
# Identifies BentoML as the breaching stage
# @yuki is invoked for ML-specific diagnosis
# @sofia is invoked if DB pool is the issue
```

### 7.3 Code Review

```bash
# Paste your PR diff or file path
"Review this PR: app/engines/rule_engine.py

 @sofia — correctness, N+1, async patterns
 @priya — security, injection vectors
 @aisha — test coverage gaps"
```

### 7.4 Document Generation

```bash
# Generate a new ADR
"@marcus — write ADR-009 for our decision to use
 Karpenter over Cluster Autoscaler"

# Update existing doc
"@james — update docs/compliance/pci_dss_controls.md
 Requirement 10.2.1(c) — Elasticsearch audit is now enabled"

# Generate a runbook
"@darius — write a runbook for Neo4j connection
 timeout in the Flink graph pipeline"
```

---

## 8. File Operations

Claude Code can read and write files directly:

```bash
# Read a specific document
"Read docs/architecture/adr/ADR-005-neo4j-graph-store.md
 and explain the decision to @yuki"

# Write a new file
"@sofia — create app/core/idempotency.py
 implementing the idempotency key middleware
 per the spec in docs/security/encryption_spec.md"

# Edit an existing file
"@priya — update k8s/istio/peer-authentication-strict.yaml
 to add the new ml namespace"

# Run tests
"@aisha — run pytest tests/unit/test_rule_engine.py
 and fix any failures"
```

---

## 9. Settings & Permissions

Claude Code respects the permissions defined in `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(pytest:*)",
      "Bash(ruff:*)",
      "Bash(mypy:*)",
      "Bash(alembic:*)",
      "Read(.claude/agents/*)",
      "Read(docs/**)",
      "Write(app/**)",
      "Write(frontend/**)",
      "Write(tests/**)"
    ],
    "deny": [
      "Bash(terraform apply:*)",
      "Bash(kubectl delete:*)",
      "Bash(DROP TABLE:*)",
      "Write(k8s/production/**)"
    ]
  }
}
```

**Allowed by default:** reading docs, writing application code, running tests, linting
**Blocked by default:** applying infrastructure changes, deleting Kubernetes resources, production DB mutations

---

## 10. Tips & Best Practices

| Tip | Why |
|---|---|
| Always run `claude` from the project root | So CLAUDE.md is auto-loaded |
| Use `@handle` for precision | Avoids ambiguous routing on complex topics |
| Reference doc paths explicitly | `"per docs/security/rbac_matrix.md §3"` gives Claude exact context |
| One task per message | Clearer output, easier to review |
| Ask for ADRs on big decisions | `"@marcus — write an ADR for this decision"` |
| Use `/ppr status` before any merge | Catch PRR gaps early |
| Commit CLAUDE.md to Git | Every engineer gets the same agent context |
| Update open issues in CLAUDE.md | Keeps the team's context current |

---

## 11. Quick Reference Card

```
INVOKE AGENT        @marcus / @priya / @yuki / @darius
                    @sofia / @james / @aisha / @elena

SLASH COMMANDS      /score debug
                    /score simulate <scenario>
                    /review queue
                    /review case <id>
                    /ppr run
                    /ppr status

RUN PROMPTS         claude < .claude/prompts/<prompt>.md

KEY FILES           CLAUDE.md              ← Project brain (auto-loaded)
                    .claude/agents/        ← Agent personas
                    .claude/commands/      ← Slash commands
                    .claude/prompts/       ← Reusable task prompts
                    .claude/settings.json  ← Permissions

MULTI-AGENT         "@sofia @priya review this endpoint"
HANDOFF             "@marcus design it, @sofia implement it"
DISAGREEMENT        Agents will push back — let them
```

---

*Document Version: 1.0.0*
*Maintained by: All agents (update when workflows change)*
*Classification: Internal — Engineering Confidential*