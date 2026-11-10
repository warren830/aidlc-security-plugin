# Security threat model

Fill in each section, in this order. Step 6 of the Security Threat Model stage
says what each one holds. A threat's entry goes under the first of its STRIDE
categories, in the order of the six STRIDE sections below.

## Scope

The specs the review read, by their record paths, and the review's `scan_id`.

## Assumptions

One line for each premise the threats depend on that the specs do not state,
led by its ID, `A-001` onwards. The person confirms them at the gate.

## Trust boundaries

One line for each place where data crosses between parties of different
trust: the boundary, and what sits on each side.

## Asset flows

One line for each asset the design handles: the path it takes between
components, and the trust boundaries it crosses.

## Spoofing

The spoofing threats, highest severity first, or one line that says the
review found none.

## Tampering

The tampering threats, highest severity first, or one line that says the
review found none.

## Repudiation

The repudiation threats, highest severity first, or one line that says the
review found none.

## Information disclosure

The information disclosure threats, highest severity first, or one line that
says the review found none.

## Denial of service

The denial of service threats, highest severity first, or one line that says
the review found none.

## Elevation of privilege

The elevation of privilege threats, highest severity first, or one line that
says the review found none.

## Mitigations for Construction

For each CRITICAL or HIGH threat, one or more controls the code must have, one
line each, led by the mitigation ID and the threat's ID, such as
`M-001 (T-001)`.

## Record

Exactly one fenced `json` block, the machine-readable record. Keep it the only
`json` block in the file.
