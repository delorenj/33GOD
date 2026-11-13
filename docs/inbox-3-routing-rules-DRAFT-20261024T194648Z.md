# INBOX-3 Routing Rules Draft

**Ticket:** INBOX-3 (uuid: f84ea341-26a7-46c6-8539-940b5ae3c362)
**Board:** INBOX Inbox and Triage
**Workspace:** damians-desk
**State:** Todo
**Owner:** Damian
**Draft Date:** {timestamp}
**Status:** Owner-only review draft — not yet active

---

## Purpose

Define routing rules for incoming items across four categories:
- **HelloSubconscious**
- **LAMP**
- **personal**
- **parking**

This document proposes routing criteria and structure. It does NOT activate any routing or move tickets. It is a bounded draft for Damian's review and approval.

---

## Existing Category Definitions (Authoritative)

The following category names are taken from the existing Plane board definitions and are authoritative for naming only. No UUID mapping or destination binding is assumed or verified here.

- **HelloSubconscious**: Items related to the HelloSubconscious project ecosystem
- **LAMP**: Items related to the LAMP stack or infrastructure
- **personal**: Items for personal projects or work
- **parking**: Items awaiting classification or with ambiguous routing

---

## Routing Rules Structure

Each rule consists of:
- **Criteria**: Conditions that determine if an item belongs to this category
- **Examples**: Synthetic/generic examples only (no private source content)
- **Decision Type**: Established rule vs. proposal
- **Cross-Project Handling**: How to handle items that could fit multiple categories

---

## Routing Categories

### 1. HelloSubconscious

**Decision Type:** Established rule (source: existing board taxonomy)

**Criteria:**
- Item title, description, or metadata contains "HelloSubconscious" or clear project references
- Workspace or project field indicates HelloSubconscious
- Tags include "hello-subconscious", "subconscious", or similar

**Examples:**
- "Update HelloSubconscious landing page copy"
- "Fix bug in HelloSubconscious audio processing pipeline"
- "Add new feature to HelloSubconscious CLI tool"

**Cross-Project Handling:**
- If an item could plausibly belong to both HelloSubconscious and LAMP, default to HelloSubconscious unless the LAMP aspect is clearly dominant
- Tie-break: prefer the category that aligns with the primary maintainer's focus

---

### 2. LAMP

**Decision Type:** Established rule (source: existing board taxonomy)

**Criteria:**
- Item title, description, or metadata contains "LAMP" or clear LAMP stack references
- Workspace or project field indicates LAMP infrastructure
- Tags include "lamp", "infrastructure", "server", or similar

**Examples:**
- "Upgrade LAMP stack to PHP 8.3"
- "Debug MySQL replication issues in LAMP environment"
- "Add monitoring for LAMP server resource usage"

**Cross-Project Handling:**
- If an item could plausibly belong to both LAMP and HelloSubconscious, default to LAMP only if the infrastructure aspect is clearly dominant
- Tie-break: prefer the category that aligns with the primary maintainer's focus

---

### 3. personal

**Decision Type:** Established rule (source: existing board taxonomy)

**Criteria:**
- Item title, description, or metadata contains "personal" or clear personal project references
- Workspace or project field indicates personal work
- Tags include "personal", "hobby", or similar

**Examples:**
- "Build personal website with new CSS framework"
- "Experiment with personal AI assistant setup"
- "Document personal workflow improvements"

**Cross-Project Handling:**
- If an item could plausibly belong to both personal and another category, default to personal unless the other category is clearly dominant
- Tie-break: prefer the category that aligns with the primary maintainer's focus

---

### 4. parking

**Decision Type:** Proposal (requires Damian's explicit decision)

**Criteria:**
- Item does not clearly fit any of the above categories
- Item title or description is ambiguous or lacks sufficient detail
- Item is a meta-issue about routing itself
- Item is a draft or placeholder with no clear destination

**Examples:**
- "Update documentation" (no project specified)
- "Investigate performance issue" (no clear scope)
- "Miscellaneous task" (no category indicated)
- "How should we route this?" (meta-issue)

**Handling:**
- Items in parking require manual classification by Damian
- No automatic dispatch or activation
- Review gate: Damian must approve classification before moving out of parking

---

## Decision Rules Summary

| Category | Decision Type | Automatic? | Approval Required | Cross-Project Tie-Break |
|----------|---------------|------------|-------------------|------------------------|
| HelloSubconscious | Established | Yes | No | Prefer HelloSubconscious unless LAMP is clearly dominant |
| LAMP | Established | Yes | No | Prefer LAMP unless HelloSubconscious is clearly dominant |
| personal | Established | Yes | No | Prefer personal unless another category is clearly dominant |
| parking | Proposal | No | Yes (Damian) | N/A |

---

## Sensitive Input Exclusion

This routing guide does NOT process or route:
- Raw private clinical/client content
- Transcripts or original sources
- Attachments or history
- Any content marked as private or sensitive

Routing is based solely on non-sensitive metadata and generic category names.

---

## No Auto-Dispatch

- No automatic ticket assignment or movement
- No workflow activation
- No service restart or configuration change
- No Git stage/commit/push
- No board/repo identity changes
- No memory write or global config

Routing rules are advisory only until Damian approves and activates them.

---

## Review Gate

Before any routing is activated:
1. Damian reviews this draft
2. Damian approves the categories and criteria
3. Damian classifies any parking items
4. Damian explicitly authorizes activation

---

## Acceptance Coverage

This draft covers:
- Four routing categories with clear criteria
- Cross-project tie-breaking logic
- Parking fallback with review gate
- Sensitivity exclusions
- No auto-dispatch commitment

---

## Questions for Damian

1. Are the category names and criteria acceptable as written?
2. Should the cross-project tie-breaking logic be adjusted?
3. Should parking items have a time-based escalation policy?
4. Are there additional categories that should be defined?

---

## Next Steps

1. Damian reviews and approves this draft
2. Damian classifies any parking items
3. Damian authorizes activation (separate step)
4. Routing rules are implemented only after explicit approval

---

## Receipt

**Draft File:** {filename}
**Owner:** root:root
**Permissions:** 0600 (owner-only)
**Source:** Non-sensitive existing taxonomy
**Validation Hash:** (to be computed)

---

*This is a bounded draft for Damian's review. No routing is activated by this document.*
