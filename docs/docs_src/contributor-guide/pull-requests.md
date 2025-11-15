# Pull Request Guide

> Complete guide to submitting and reviewing pull requests in GreenGovRAG

## Table of Contents

- [Overview](#overview)
- [Before You Start](#before-you-start)
- [Fork and Branch Workflow](#fork-and-branch-workflow)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Creating Pull Requests](#creating-pull-requests)
- [Pull Request Checklist](#pull-request-checklist)
- [Code Review Process](#code-review-process)
- [Addressing Feedback](#addressing-feedback)
- [Merge Process](#merge-process)
- [After Merge](#after-merge)
- [Common Scenarios](#common-scenarios)

## Overview

Pull requests (PRs) are the primary way to contribute code to GreenGovRAG. This guide covers the complete workflow from creating a branch to getting your changes merged.

### Pull Request Goals

- **Quality**: Ensure code meets project standards
- **Documentation**: Changes are well-documented
- **Testing**: All tests pass and new code is tested
- **Review**: Changes are reviewed by maintainers
- **Integration**: Changes merge cleanly without conflicts

### Timeline Expectations

- **Initial Review**: 3-5 business days
- **Follow-up Reviews**: 1-2 business days
- **Merge**: Once approved and checks pass

*Note: These are estimates. Complex PRs may take longer.*

## Before You Start

### 1. Check for Existing Work

```bash
# Search existing pull requests
# Visit: https://github.com/sdp5/green-gov-rag/pulls

# Search closed PRs too
# Visit: https://github.com/sdp5/green-gov-rag/pulls?q=is%3Apr+is%3Aclosed
```

**Why:** Avoid duplicate work and learn from similar changes.

### 2. Create or Find an Issue

```bash
# Search existing issues
# Visit: https://github.com/sdp5/green-gov-rag/issues

# Create new issue if needed
# Click "New Issue" and describe the problem/feature
```

**Why:** PRs should reference an issue for context and discussion.

### 3. Discuss Approach

For significant changes:
- Comment on the issue with your proposed approach
- Wait for maintainer feedback
- Adjust approach based on discussion

**Why:** Ensures alignment before investing time in implementation.

## Fork and Branch Workflow

### 1. Fork the Repository

```bash
# Via GitHub web interface:
# 1. Visit https://github.com/sdp5/green-gov-rag
# 2. Click "Fork" button in top-right
# 3. Select your account as the destination
```

### 2. Clone Your Fork

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/green-gov-rag.git
cd green-gov-rag

# Add upstream remote
git remote add upstream https://github.com/sdp5/green-gov-rag.git

# Verify remotes
git remote -v
# origin    https://github.com/YOUR_USERNAME/green-gov-rag.git (fetch)
# origin    https://github.com/YOUR_USERNAME/green-gov-rag.git (push)
# upstream  https://github.com/sdp5/green-gov-rag.git (fetch)
# upstream  https://github.com/sdp5/green-gov-rag.git (push)
```

### 3. Create a Feature Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create and switch to feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

**Branch naming conventions:**

```bash
# Feature branches
feature/add-victorian-planning-schemes
feature/improve-vector-search
feature/export-to-pdf

# Bug fix branches
fix/vector-store-connection-timeout
fix/metadata-extraction-error
fix/query-endpoint-500-error

# Documentation branches
docs/update-installation-guide
docs/add-architecture-diagram
docs/improve-api-examples

# Refactoring branches
refactor/simplify-llm-factory
refactor/extract-common-utilities
refactor/improve-error-handling

# Test branches
test/add-integration-tests
test/improve-coverage
test/add-performance-benchmarks
```

### 4. Sync with Upstream

Keep your branch up-to-date:

```bash
# Fetch upstream changes
git fetch upstream

# Update your main branch
git checkout main
git merge upstream/main
git push origin main

# Update your feature branch
git checkout feature/your-feature-name
git merge main

# Or rebase for cleaner history
git rebase main
```

## Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, no logic change)
- **refactor**: Code refactoring (no feature change or bug fix)
- **perf**: Performance improvements
- **test**: Adding or updating tests
- **build**: Build system or dependency changes
- **ci**: CI/CD configuration changes
- **chore**: Other changes (tooling, config, etc.)

### Scopes (Optional)

- **api**: API endpoints and services
- **rag**: RAG pipeline components
- **etl**: ETL pipeline
- **db**: Database models and migrations
- **tests**: Testing infrastructure
- **docs**: Documentation
- **deploy**: Deployment configuration

### Examples

```bash
# Feature addition
feat(rag): add support for hybrid BM25 + vector search

Implements hybrid search combining BM25 and vector similarity.
This improves retrieval accuracy for keyword-heavy queries.

Closes #42

# Bug fix
fix(api): handle empty LGA name in query endpoint

Previously, empty LGA names caused 500 errors due to SQL escaping.
Now validates input and returns 400 with helpful error message.

Fixes #123

# Documentation
docs: update installation guide with PostgreSQL setup

Add detailed steps for installing and configuring PostgreSQL
with pgvector extension for local development.

# Refactoring
refactor(etl): extract common parsing logic to base class

Reduces code duplication across PDF, HTML, and Word parsers.
No functional changes.

# Breaking change
feat(api)!: change query response format

BREAKING CHANGE: Query response now returns sources as array
instead of object. Update clients to use new format.

Before:
{
  "answer": "...",
  "sources": {"doc1": {...}, "doc2": {...}}
}

After:
{
  "answer": "...",
  "sources": [{"id": "doc1", ...}, {"id": "doc2", ...}]
}

Closes #67
```

### Commit Best Practices

**Good commits:**
```bash
# Atomic: Single logical change
git commit -m "feat(rag): add location NER for Australian places"

# Descriptive: Clear what and why
git commit -m "fix(db): prevent SQL injection in LGA filter

Use parameterized queries instead of string interpolation
to prevent SQL injection vulnerabilities."

# Scoped: Changes related to one area
git commit -m "test(etl): add integration tests for document ingestion"
```

**Bad commits:**
```bash
# Too vague
git commit -m "fix bug"
git commit -m "update code"
git commit -m "wip"

# Too broad (multiple unrelated changes)
git commit -m "Add feature X, fix bug Y, update docs Z"

# Missing context
git commit -m "fix query"  # Which query? What was wrong?
```

### Making Commits

```bash
# Stage specific files
git add backend/green_gov_rag/rag/hybrid_search.py
git add backend/tests/test_rag/test_hybrid_search.py

# Commit with message
git commit -m "feat(rag): add hybrid search combining BM25 and vector similarity"

# Or use editor for multi-line message
git commit
# Opens editor where you can write detailed message

# Amend last commit (if not pushed)
git commit --amend

# Add changes to last commit (if not pushed)
git add forgotten_file.py
git commit --amend --no-edit
```

## Creating Pull Requests

### 1. Push Your Branch

```bash
# Push to your fork
git push origin feature/your-feature-name

# If you rebased, force push (careful!)
git push origin feature/your-feature-name --force-with-lease
```

### 2. Create PR on GitHub

1. Visit your fork: `https://github.com/YOUR_USERNAME/green-gov-rag`
2. Click "Compare & pull request" button
3. Select base repository: `sdp5/green-gov-rag`
4. Select base branch: `main`
5. Fill out PR template (see below)

### 3. Pull Request Template

```markdown
## Description

Brief description of what this PR does.

Closes #<issue_number>

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)
- [ ] Performance improvement
- [ ] Test addition/improvement

## Changes Made

- Detailed description of change 1
- Detailed description of change 2
- Detailed description of change 3

## Testing

Describe how you tested these changes:

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed
- [ ] All tests passing locally

Test commands run:
```bash
pytest tests/test_module.py
```

## Documentation

- [ ] Code comments updated
- [ ] Docstrings updated
- [ ] User documentation updated (if needed)
- [ ] Architecture documentation updated (if needed)

## Checklist

- [ ] Code follows project style guidelines (Ruff)
- [ ] Type hints added for all functions (MyPy)
- [ ] Tests added and passing
- [ ] Documentation updated
- [ ] No breaking changes (or documented with migration guide)
- [ ] Commit messages follow conventional commits format
- [ ] Branch is up to date with main

## Screenshots (if applicable)

For UI changes or visual improvements.

## Additional Notes

Any additional context, concerns, or discussion points.
```

### 4. Example Pull Request

**Title:**
```
feat(etl): add Victorian Planning Schemes document source
```

**Description:**
```markdown
## Description

Adds a new document source plugin for scraping Victorian planning schemes
from the Victoria Planning website. This expands coverage to Victoria and
enables location-filtered queries for Victorian LGAs.

Closes #78

## Type of Change

- [x] New feature (non-breaking change which adds functionality)

## Changes Made

- Created `VicPlanningSchemesScraper` class in `etl/sources/`
- Implemented document fetching from planning.vic.gov.au
- Added metadata extraction for planning zone information
- Configured rate limiting to respect website robots.txt
- Added comprehensive unit and integration tests
- Updated document source configuration schema
- Added documentation for configuration

## Testing

- [x] Unit tests added/updated
- [x] Integration tests added/updated
- [x] Manual testing performed
- [x] All tests passing locally

Test commands run:
```bash
pytest tests/test_etl/test_sources/test_vic_planning.py -v
pytest -m integration
ruff check .
mypy green_gov_rag
```

Manual testing:
- Scraped 50 Victorian planning documents successfully
- Verified metadata extraction accuracy
- Tested rate limiting (5 req/sec)
- Confirmed integration with existing pipeline

## Documentation

- [x] Code comments updated
- [x] Docstrings updated
- [x] User documentation updated
- [x] Architecture documentation updated

Updated files:
- `docs/user-guide/document-sources.md` - Added Victorian Planning Schemes section
- `docs/reference/plugin-api.md` - Updated with example usage

## Checklist

- [x] Code follows project style guidelines (Ruff)
- [x] Type hints added for all functions (MyPy)
- [x] Tests added and passing
- [x] Documentation updated
- [x] No breaking changes
- [x] Commit messages follow conventional commits format
- [x] Branch is up to date with main

## Additional Notes

The scraper respects robots.txt and implements exponential backoff for
rate limiting. Future enhancement could add incremental updates to avoid
re-scraping unchanged documents.
```

## Pull Request Checklist

Before submitting your PR, verify:

### Code Quality

- [ ] Code follows [style guidelines](code-style.md)
- [ ] All functions have type hints
- [ ] Docstrings use Google style
- [ ] No linting errors (`ruff check .`)
- [ ] Code is formatted (`ruff format .`)
- [ ] No type errors (`mypy green_gov_rag tests`)
- [ ] Complexity is manageable (McCabe < 10)

### Testing

- [ ] Unit tests added for new code
- [ ] Integration tests added if needed
- [ ] All tests pass (`pytest`)
- [ ] Coverage meets requirements (`pytest --cov`)
- [ ] Edge cases tested
- [ ] Error cases tested

### Documentation

- [ ] Code comments explain "why", not "what"
- [ ] Docstrings complete and accurate
- [ ] User docs updated if user-facing changes
- [ ] Architecture docs updated if structural changes
- [ ] API docs updated if endpoint changes
- [ ] CHANGELOG.md updated (if applicable)

### Git Hygiene

- [ ] Commit messages follow conventional commits
- [ ] Commits are atomic and logical
- [ ] No merge commits (use rebase)
- [ ] No debug code or commented code
- [ ] No sensitive data (API keys, passwords)
- [ ] Branch is up to date with main

### Functionality

- [ ] Feature works as intended
- [ ] No breaking changes (or documented)
- [ ] Performance acceptable
- [ ] Security considerations addressed
- [ ] Error handling robust
- [ ] Edge cases handled

## Code Review Process

### Review Timeline

1. **Automatic Checks** (immediate)
   - CI/CD runs tests
   - Linting and formatting checks
   - Type checking
   - Coverage report generated

2. **Initial Review** (3-5 business days)
   - Maintainer reviews code
   - Provides feedback or approval
   - May request changes

3. **Follow-up Reviews** (1-2 business days)
   - Review updated code
   - Iterate until approved

4. **Merge** (once approved + checks pass)
   - Maintainer merges PR
   - Branch deleted
   - Release planning (if applicable)

### What Reviewers Look For

**Code Quality:**
- Follows style guidelines
- Well-structured and readable
- Appropriate complexity
- Proper error handling
- Security considerations

**Testing:**
- Adequate test coverage
- Tests are meaningful
- Edge cases covered
- Integration tests where needed

**Documentation:**
- Clear docstrings
- Updated user/dev docs
- Architecture docs if needed
- Code comments where helpful

**Design:**
- Aligns with project architecture
- Follows existing patterns
- No unnecessary complexity
- Performance implications understood

**Completeness:**
- Fully implements feature/fix
- No TODOs or unfinished code
- Migration path for breaking changes

### Review Feedback Types

**Must Fix (Required):**
```markdown
**Required:** This will cause a SQL injection vulnerability.
Use parameterized queries instead.
```

**Suggestion (Optional):**
```markdown
**Suggestion:** Consider extracting this logic into a separate function
for better testability. Not blocking if you prefer current approach.
```

**Question:**
```markdown
**Question:** What happens if the LGA name contains special characters?
Should we add validation here?
```

**Praise:**
```markdown
**Nice work!** This is a really clean implementation of the hybrid search.
The tests are especially thorough.
```

## Addressing Feedback

### Reading Review Comments

1. Read all feedback before making changes
2. Ask questions if anything is unclear
3. Distinguish between required and suggested changes
4. Plan your response and implementation

### Responding to Feedback

```markdown
# For required changes
> Use parameterized queries to prevent SQL injection.

Good catch! I've updated to use SQLModel's parameter binding. See
commit abc1234.

# For suggestions you implement
> Consider extracting this to a helper function.

Good idea! I've extracted it to `_validate_lga_name()`. See commit def5678.

# For suggestions you don't implement
> Consider using a different algorithm here.

I considered this approach, but it would significantly increase complexity
without measurable performance benefit. Given that this code path is only
hit during initialization, I think the current approach is acceptable.

Happy to discuss further if you feel strongly about it!

# For questions
> What happens if the LGA name is empty?

Good question! I've added validation to raise ValueError if LGA name is
empty or whitespace-only. Also added tests for this case.
```

### Making Changes

```bash
# Make requested changes
git add modified_files.py
git commit -m "fix(api): add input validation for LGA names"

# Push to same branch
git push origin feature/your-feature-name

# PR automatically updates
```

### Iterating

- Make changes in response to feedback
- Push to same branch (PR updates automatically)
- Mark resolved conversations as resolved
- Request re-review when ready

### Handling Conflicts

If main branch advances:

```bash
# Update your main branch
git checkout main
git pull upstream main

# Update your feature branch
git checkout feature/your-feature-name
git rebase main

# Resolve conflicts if any
# Edit conflicting files
git add resolved_files.py
git rebase --continue

# Force push (updates PR)
git push origin feature/your-feature-name --force-with-lease
```

## Merge Process

### Approval Requirements

Before merge:
- [ ] At least one maintainer approval
- [ ] All CI checks passing
- [ ] No unresolved conversations
- [ ] Branch up to date with main
- [ ] No merge conflicts

### Merge Methods

**Squash and Merge (Default):**
- Combines all commits into one
- Cleaner history
- Used for most PRs

```bash
# Maintainer will squash and merge via GitHub UI
# Or via command line:
git checkout main
git merge --squash feature/your-feature-name
git commit -m "feat(etl): add Victorian planning schemes (#123)"
git push origin main
```

**Rebase and Merge:**
- Preserves individual commits
- Used for PRs with well-organized commits
- Must have clean commit history

**Merge Commit:**
- Creates merge commit
- Rarely used
- Only for special cases

### After Approval

Once your PR is approved:

1. **Ensure CI passes** - Fix any failing checks
2. **Resolve conflicts** - Rebase if needed
3. **Wait for merge** - Maintainer will merge
4. **Celebrate!** - Your contribution is merged 🎉

## After Merge

### Cleanup

```bash
# Update your main branch
git checkout main
git pull upstream main

# Delete your feature branch
git branch -d feature/your-feature-name

# Delete remote branch (if not auto-deleted)
git push origin --delete feature/your-feature-name
```

### Follow-up

- Monitor for issues related to your changes
- Be available to answer questions
- Consider related improvements
- Update your fork regularly

### Recognition

Your contribution will be:
- Listed in git history
- Mentioned in release notes
- Added to CONTRIBUTORS.md
- Appreciated by the community!

## Common Scenarios

### Scenario 1: PR Too Large

**Problem:** PR has too many changes, hard to review.

**Solution:**
```bash
# Break into smaller PRs
git checkout main
git checkout -b feature/part-1
# Cherry-pick related commits
git cherry-pick abc1234 def5678
git push origin feature/part-1
# Create separate PR

# Repeat for other parts
```

### Scenario 2: Tests Failing in CI

**Problem:** Tests pass locally but fail in CI.

**Solution:**
```bash
# Check CI environment differences
# - Python version
# - Dependencies
# - Environment variables

# Run tests exactly as CI does
docker-compose up -d
docker-compose exec backend pytest

# Fix issues and push
```

### Scenario 3: Merge Conflicts

**Problem:** Main branch has conflicting changes.

**Solution:**
```bash
# Update main
git checkout main
git pull upstream main

# Rebase feature branch
git checkout feature/your-feature-name
git rebase main

# Resolve conflicts
# Edit conflicting files, then:
git add resolved_files.py
git rebase --continue

# Force push
git push origin feature/your-feature-name --force-with-lease
```

### Scenario 4: Reviewer Requests Major Changes

**Problem:** Reviewer suggests significant refactoring.

**Solution:**
1. Discuss the feedback - understand reasoning
2. If you agree: Make changes, push, request re-review
3. If you disagree: Explain your reasoning respectfully
4. If uncertain: Ask for clarification or alternative approaches

```markdown
Thanks for the feedback! I see your point about the architecture.

I have a few questions before implementing:
1. Would this approach work with the existing vector store interface?
2. Are there performance implications I should consider?
3. Should I create a separate PR for this refactoring?

Happy to discuss in more detail!
```

### Scenario 5: Abandoning a PR

If you need to abandon a PR:

```markdown
I don't have time to continue this right now. Feel free to close this PR.

If anyone wants to pick this up, here's what's left to do:
- [ ] Add integration tests
- [ ] Update documentation
- [ ] Fix review feedback in #comment-123

Thanks for the review feedback!
```

---

**Congratulations!** You now know the complete pull request workflow. Start contributing by finding a [good first issue](https://github.com/sdp5/green-gov-rag/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)!

## Quick Reference

### Common Commands

```bash
# Setup
git clone https://github.com/YOUR_USERNAME/green-gov-rag.git
git remote add upstream https://github.com/sdp5/green-gov-rag.git

# Branch management
git checkout -b feature/your-feature
git checkout main
git pull upstream main
git merge main

# Committing
git add file.py
git commit -m "feat(scope): description"
git push origin feature/your-feature

# Resolving conflicts
git rebase main
# resolve conflicts
git add file.py
git rebase --continue
git push origin feature/your-feature --force-with-lease

# Cleanup
git branch -d feature/your-feature
git push origin --delete feature/your-feature
```

### PR Checklist (Quick Version)

- [ ] Tests pass
- [ ] Code formatted (ruff)
- [ ] Type checked (mypy)
- [ ] Documentation updated
- [ ] Commits follow conventions
- [ ] Branch up to date with main
- [ ] PR description complete
