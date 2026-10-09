---
name: eleza-session
description: "Pulls recent wearable walking sessions from Bee, normalizes terms against OpenStax course curriculum, evaluates factual alignment using eleza-align, and writes the structured evidence report and on-wrist gap prompt."
---

# eleza-session Agent Skill (ELZ-503)

This skill packages the complete on-wrist coaching and oral defense loop for Bee:
1. Pulls the latest walking session from Bee (`bee stream` or `bee sync`).
2. Applies deterministic biochemical term normalization against the active course map.
3. Segments utterances into claims and runs hybrid candidate retrieval against OpenStax passages.
4. Validates character-exact substring verification (**INV-2**).
5. Computes unit coverage (**Covered**, **Skipped**, **Contradicted**) without scores.
6. Records to the longitudinal ledger and generates the next-morning wrist gap prompt.

## Execution

```bash
# Run session alignment across latest Bee data
python3 -m eleza.agent_skill --unit glycolysis

# Output structured JSON
python3 -m eleza.agent_skill --unit glycolysis --json
```

## Rubric Reference

Matches the Devpost Amazon Developer Hackathon rubric item:
> *"novel education use case leveraging Agent Skills for on-wrist coaching, advance use of the facts and insights capabilities of the product and developer tools, real time functionality, self improvement workflows"*
