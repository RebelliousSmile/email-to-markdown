---
name: changelog
description: Generate or update CHANGELOG.md from git history, then commit and tag the release
argument-hint: <version> (e.g. v1.2.0) or empty to auto-detect next version
---

# Changelog Prompt

## Goal

Generate or update CHANGELOG.md by extracting and grouping commits since the last git tag, then commit the changelog and create a signed git tag for the release.

## Context

### Commit convention

```markdown
@aidd_docs/templates/vcs/commit.md
```

## Rules

- Follow https://keepachangelog.com format
- Group commits by type: Added, Fixed, Changed, Removed, Security, Deprecated
- Skip chore/style/ci commits unless significant
- Most recent version at the top
- Dates in YYYY-MM-DD format
- If CHANGELOG.md exists, prepend new section — never overwrite previous entries
- Never push without explicit user confirmation

## Steps

1. Run `` `git tag --sort=-version:refname | head -1` `` to find the last tag
2. Run `` `git log <last-tag>..HEAD --pretty="%h %s" --no-merges` `` to list commits since last tag
3. If $ARGUMENTS provided, use it as the new version; otherwise infer next semver from commit types:
   - `feat` → minor bump, `fix` → patch bump, `BREAKING CHANGE` → major bump
4. Group commits by Keep a Changelog category (Added/Fixed/Changed/Removed)
5. If CHANGELOG.md exists, read current content
6. Prepend new `## [version] - YYYY-MM-DD` section
7. Show diff to user and **wait for confirmation** before writing
8. Write updated CHANGELOG.md
9. Commit: `` `git add CHANGELOG.md && git commit -m "chore(release): <version>"` ``
10. Create annotated tag: `` `git tag -a <version> -m "Release <version>"` ``
11. Show summary (version, tag, commits included) and ask user: push tag + branch? (`git push && git push origin <version>`)
