## What does this PR do?

<!-- Brief description of changes -->

## Type of change

- [ ] New skill
- [ ] Skill update
- [ ] Documentation
- [ ] Bug fix
- [ ] Other

## Checklist

### For new skills:
- [ ] `name` field matches directory name exactly
- [ ] `description` includes trigger phrases AND scope boundaries
- [ ] Placed in the correct category directory (research/build/optimize/monitor/cross-cutting)
- [ ] Uses `~~placeholder` pattern for tool references
- [ ] Includes validation checkpoints
- [ ] Includes at least one concrete example
- [ ] Related skills are linked correctly

### For all changes:
- [ ] Follows the [Agent Skills specification](https://agentskills.io/specification.md)
- [ ] `VERSIONS.md` updated with new version and date
- [ ] `marketplace.json` (repo root) skills array updated (if adding a new skill)
- [ ] `.claude-plugin/marketplace.json` byte-identical to root (`cp marketplace.json .claude-plugin/marketplace.json` — or let CI do it on main)
- [ ] `.claude-plugin/plugin.json` skills array updated (if adding a new skill)
- [ ] `README.md` skills table updated (if adding a new skill)
- [ ] No CORE-EEAT, CITE, veto, cap, BLOCKED, or artifact-gate standard was weakened
- [ ] Human maintainer review completed before merge
