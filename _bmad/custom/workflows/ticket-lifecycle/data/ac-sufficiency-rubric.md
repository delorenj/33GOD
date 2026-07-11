# AC Sufficiency Rubric

Evaluate acceptance criteria against these 4 binary criteria. ALL must pass for AC to be sufficient.

## Criteria

### 1. Non-Empty
- AC field exists and contains content
- Empty string, null, or whitespace-only fails

### 2. Testable Assertions
- Each AC item must be a verifiable statement
- Pass: "User can log in with valid credentials and sees dashboard"
- Fail: "Login works well" / "Good user experience" / "Fast performance"

### 3. Enumerated Items
- AC must be a numbered or bulleted list of discrete items
- Pass: "1. X happens 2. Y displays 3. Z is stored"
- Fail: Prose paragraph describing expected behavior

### 4. Functional Requirement Coverage
- At least one AC item must exist per functional requirement referenced in the ticket
- If ticket references FR-1 and FR-2, there must be AC items covering both
- If ticket has no explicit FR references, this criterion passes by default

## Evaluation

```
SUFFICIENT = non_empty AND testable AND enumerated AND fr_coverage
```

If ANY criterion fails, route to Plane Captain for AC refinement.
Include which specific criteria failed in the refinement request.
