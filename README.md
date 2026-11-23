# Runtime contract

Bohrium Playground Period 4 submission — challenge `challenge-32c0210d` (track: `academic-writing`).

This repository holds the complete skill package for the challenge: the skill
definition, its executable entry point and all supporting scripts. No precomputed
answers, private data or credentials are included.

## Skill

- Name: `thesis-longdoc-consistency`
- Summary: Use when a case supplies a thesis or other long document and asks for chapter planning, cross-chapter consistency checks, or localized revision tracking; indexes chapters and word allocation, builds an acronym and terminology glossary, verifies figure/table/equation numbering against references, and produces a scoped change log in /app/output/result.json while preserving case_id and every output_contract field. Deterministic standard library only; no network.

## Contents

| File |
|------|
| `SKILL.md` |
| `scripts/run_skill.py` |
| `README.md` |

## How to run

```bash
python scripts/run_skill.py --case /input/case.json --output /app/output/result.json
```

The entry point is `SKILL.md`; input/output contracts, error handling and a minimal
usage example are documented there.

## Notes

- Pure Python standard library; no network access required.
- The result JSON keeps the input case id, the main results, per-item evidence,
  a run status and an uncertainty section.
