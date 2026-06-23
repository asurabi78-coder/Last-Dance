# Contributing

Thanks for your interest in contributing! This guide covers adding skills, improving existing ones, and submitting changes.

## Requesting a Skill

[Open a Skill Request issue](https://github.com/aaron-he-zhu/seo-geo-claude-skills/issues/new?template=skill-request.yml) if you have an idea but don't want to build it yourself.

## Adding a New Skill

### 1. Choose the correct category

| Category | Directory | Use when the skill... |
|----------|-----------|----------------------|
| Research | `research/` | Gathers market data before content creation |
| Build | `build/` | Creates new content or markup |
| Optimize | `optimize/` | Improves existing content or site health |
| Monitor | `monitor/` | Tracks performance over time |
| Cross-cutting | `cross-cutting/` | Spans multiple phases (quality frameworks, entity, memory) |

### 2. Create the skill directory

```bash
mkdir -p <category>/<skill-name>
```

Directory name: 1-64 chars, lowercase `a-z`, numbers, hyphens only. No leading/trailing/consecutive hyphens.

### 3. Create `SKILL.md` with required frontmatter

```yaml
---
name: your-skill-name
version: "1.0.0"
description: 'Use when the user asks to "[trigger]". [What it does]. For [related task], see [other-skill].'
license: Apache-2.0
compatibility: "Claude Code and compatible agent-skill hosts"
metadata:
  author: your-github-username
  version: "1.0.0"
  geo-relevance: "high|medium|low"
  tags: [seo, your-tags]
  triggers: ["trigger phrase 1", "trigger phrase 2"]
---
```

The `name` field must match the directory name exactly.

### 4. Write effective instructions

Use the compact shared skeleton from `references/skill-contract.md`: `Quick Start`, `Skill Contract`, `Handoff Summary`, `Data Sources`, `Instructions`, `Reference Materials`, and `Next Best Skill`. Optional sections such as `What This Skill Does`, `Example`, `Tips for Success`, `Save Results`, and `Validation Checkpoints` are welcome when they improve execution quality. Put detailed references in the skill's `references/` subdirectory.

Auditor-class skills are the exception: they inline the authoritative auditor runbook directly in their `SKILL.md` body.

### 5. Validate

```bash
./scripts/validate-skill.sh <category>/<skill-name>
```

### 6. Update tracking files

After adding or updating a skill, keep these 5 files in sync:
- `VERSIONS.md` — version and date
- `.claude-plugin/plugin.json` — skills array
- `marketplace.json` (repo root) — must match plugin.json; copy to `.claude-plugin/marketplace.json` afterward
- `README.md` — skills table
- `CLAUDE.md` — category table

For release bumps, also sync README badges, localized README badges, and both marketplace files.

## Improving Existing Skills

Keep changes focused. Bump both top-level `version` and `metadata.version` together. Update `VERSIONS.md`. Put new reference docs in the skill's `references/` subdirectory.

## Craft Checklist

Beyond the mechanical checks, every skill should pass the senior self-test from [skill-contract.md §Skill Authoring Discipline](https://github.com/aaron-he-zhu/seo-geo-claude-skills/blob/main/references/skill-contract.md):

- [ ] **Simplicity** — would a senior engineer call this skill overcomplicated? Every section traces to the user's task.
- [ ] **Boundary** — the `description` ends with a `Not for X — use Y` clause so it doesn't compete with a sibling skill.
- [ ] **Verifiable** — the Skill Contract states a `Done when:` with checkable conditions.
- [ ] **Honest data** — Instructions tell the model to label Measured / User-provided / Estimated and never invent numbers.
- [ ] **Surgical handoff** — Next Best Skill points to exactly one primary move.

## Quality Checklist (mechanical)

Before submitting a PR:

- [ ] `name` matches directory name (lowercase slug `^[a-z0-9][a-z0-9-]*$`)
- [ ] Top-level `version` is present and matches `metadata.version` plus `VERSIONS.md`
- [ ] `description` includes trigger phrases AND scope boundaries (≤1024 chars)
- [ ] Shared compact section contract present (`validate-skill.sh` checks this)
- [ ] Validator passes: `./scripts/validate-skill.sh <category>/<skill-name>`
- [ ] Uses `~~placeholder` pattern for tool references
- [ ] `allowed-tools: WebFetch` added if skill fetches live URLs
- [ ] Includes validation checkpoints and at least one example
- [ ] All tracking and release files updated; plugin.json and marketplace.json arrays identical
- [ ] `.claude-plugin/marketplace.json` byte-identical to repo-root copy

## Submitting

- Fork, create a `feature/your-skill-name` branch, and submit a PR.

## Code of Conduct

Be respectful, constructive, and focused on making the library better for everyone.
