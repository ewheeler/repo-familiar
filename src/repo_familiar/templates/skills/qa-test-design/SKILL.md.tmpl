---
name: qa-test-design
description: Design meaningful tests before writing them. Use for test plans, boundary analysis, assertion quality, flaky-test prevention, and test architecture.
---

# QA Test Design

Use this skill before writing tests or when deciding whether existing tests actually cover meaningful behavior.

## Principle

Eight deep tests beat twenty shallow tests. Every test should justify its existence by covering a distinct behavior, boundary, failure mode, or state transition.

## Workflow

1. Decompose the feature into positive, negative, boundary, error, and state-transition cases.
2. Identify input boundaries and special values.
3. Choose assertion types that verify observable behavior rather than implementation details.
4. Design fixtures and factories that make each test's varying data explicit.
5. Check for flaky-test risks: time, randomness, ordering, concurrency, ports, filesystem state, network calls, and shared mutable state.
6. Summarize the proposed test set before implementation.

## Test Case Template

```text
Feature: <name>

Positive cases:
- <valid input> -> <expected output>

Negative cases:
- <invalid input> -> <specific rejection>

Boundary cases:
- <minimum valid value>
- <just below minimum>
- <maximum valid value>
- <just above maximum>

Error cases:
- <dependency unavailable> -> <graceful behavior>

State transitions:
- <initial state> -> <action> -> <final state>
```

## Strong Assertions

Prefer:

- Exact expected values over `is not None`.
- Specific exceptions and messages over broad `Exception` catches.
- Observable outputs and side effects over internal method-call assertions.
- One logical outcome per test.

Avoid:

- Tests that only prove framework behavior.
- Snapshot tests for business logic.
- Shared mutable fixtures.
- Network calls in unit tests.
- Test ordering dependencies.

## Report Shape

```text
Test Design: <feature>
Total cases: <n>
Positive: <n>
Negative: <n>
Boundary: <n>
Error: <n>
State transition: <n>
Flaky risk: LOW/MEDIUM/HIGH
Ready to implement: yes/no
```
