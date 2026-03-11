# CRANK_ENGINE Pickup: OWRLD-34 (Stripe Integration + Anonymous Limits)

**Date:** 2026-03-11 00:30 EDT  
**Assignee:** Grolf (eng) - IC fallback due to session locks  
**Ticket:** OWRLD-34

## Pickup Reason
CRANK_ENGINE dispatch at 00:23 ET: SVGME-36 merged (PR #81), assign next highest-leverage revenue ticket.

- OWRLD-39: Already assigned to mobile
- OWRLD-38: Already merged (PR #19, 2026-03-09)
- OWRLD-37/36: Not revenue features
- OWRLD-35: Self-assigned earlier (GOD-13)
- **OWRLD-34: Stripe Integration + Anonymous Limits** ← Highest revenue leverage (direct monetization)

All ICs have session locks (pid=206865). Per directive: assign to self if no IC free.

## Ticket Details
- **ID:** OWRLD-34
- **Name:** Stripe Integration + Anonymous Limits
- **Project:** Overworld (revenue)
- **Revenue Impact:** Direct monetization - payment processing + conversion funnel

## First Concrete Action
Install Stripe SDK (@stripe/stripe-js), scaffold checkout session API endpoint at `/api/stripe/checkout`.

## ETA
30 minutes (by 01:00 ET)

## Technical Plan
1. Install Stripe SDK
2. Create API route: `/api/stripe/checkout`
3. Implement anonymous user limits (map count/export restrictions)
4. Add checkout redirect flow
