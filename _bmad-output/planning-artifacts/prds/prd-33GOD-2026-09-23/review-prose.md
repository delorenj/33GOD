# Editorial Review — Prose

This document exists to help a solo product owner and downstream UX,
architecture, and story-planning workflows read the DeloHQ PRD as a precise
behavioral contract. The voice is intentionally direct and company-oriented;
the review preserves that voice, defined domain-term capitalization, and the
distinction between human consequence and infrastructure detail.

| Pass | Original Text | Revised Text | Changes |
| --- | --- | --- | --- |
| prose | “The user-visible command names the target and selected operation.” (§4.5, FR-12) | “The confirmation view names the target and selected operation.” | “Confirmation view” describes the user-facing requirement without implying a particular command or transport implementation. |
| prose | “Every consequential DeloHQ Action is linked to its originating Inbox item or Agent Office and to the Canonical System's outcome Evidence.” (§4.5, FR-14) | “Every consequential DeloHQ Action is linked to its originating Inbox item or Agent Office and to outcome Evidence from the Canonical System.” | Removes the awkward possessive construction while preserving the defined terms and meaning. |

Two minor clarity fixes are recommended. No tone, structure, or intentional
company-language phrasing requires revision.
