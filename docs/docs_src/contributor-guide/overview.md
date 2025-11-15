# Contributor Guide Overview

> Welcome to the GreenGovRAG contributor community

## Welcome

Thank you for your interest in contributing to GreenGovRAG! This project aims to make Australian environmental and planning regulations more accessible through AI-powered retrieval and analysis. Whether you're fixing a bug, adding a feature, improving documentation, or suggesting enhancements, your contributions are valued and appreciated.

This guide will help you understand how to contribute effectively to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Ways to Contribute](#ways-to-contribute)
- [Getting Started](#getting-started)
- [Contribution Workflow](#contribution-workflow)
- [Contributor License Agreement](#contributor-license-agreement)
- [Recognition and Attribution](#recognition-and-attribution)
- [Getting Help](#getting-help)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming, inclusive, and harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

**Examples of behavior that contributes to a positive environment:**

- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members
- Providing thoughtful and constructive feedback
- Being patient with new contributors

**Examples of unacceptable behavior:**

- The use of sexualized language or imagery
- Trolling, insulting/derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information without explicit permission
- Other conduct which could reasonably be considered inappropriate in a professional setting

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting the project maintainer at contact@sundeep.id.au. All complaints will be reviewed and investigated promptly and fairly.

Project maintainers have the right and responsibility to remove, edit, or reject comments, commits, code, wiki edits, issues, and other contributions that are not aligned with this Code of Conduct.

### Scope

This Code of Conduct applies within all project spaces, including the GitHub repository, issue tracker, pull requests, and any community spaces associated with the project.

## Ways to Contribute

### Reporting Bugs

Found a bug? Help us fix it!

**Before submitting a bug report:**
1. Check the [existing issues](https://github.com/sdp5/green-gov-rag/issues) to avoid duplicates
2. Verify the bug exists in the latest version
3. Gather relevant information (error messages, logs, environment details)

**When submitting a bug report, include:**
- A clear and descriptive title
- Steps to reproduce the issue
- Expected behavior vs. actual behavior
- Environment details (OS, Python version, deployment method)
- Error messages and stack traces
- Screenshots if applicable
- Possible fix or workaround (if known)

**Example bug report:**
```markdown
**Bug Description:**
Query endpoint returns 500 error when filtering by LGA with special characters

**Steps to Reproduce:**
1. Send POST request to /api/query
2. Include lga_name: "O'Connor"
3. Observe 500 Internal Server Error

**Expected Behavior:**
Query should process successfully and return results

**Environment:**
- OS: Ubuntu 22.04
- Python: 3.12.3
- Deployment: Docker Compose
- Vector Store: FAISS

**Error Message:**
```
psycopg2.errors.SyntaxError: unterminated quoted string
```

**Possible Fix:**
SQL query needs proper escaping for apostrophes
```

### Suggesting Enhancements

Have an idea to improve GreenGovRAG? We'd love to hear it!

**Before submitting an enhancement:**
1. Check if it already exists in [issues](https://github.com/sdp5/green-gov-rag/issues)
2. Consider if it aligns with the project's scope and goals
3. Think about implementation complexity and maintenance burden

**When suggesting an enhancement, include:**
- A clear and descriptive title
- Detailed description of the proposed feature
- Use cases and benefits
- Potential implementation approach
- Possible alternatives considered
- Any breaking changes or migration needs

**Enhancement categories:**
- **New Features**: Document sources, query capabilities, API endpoints
- **Performance**: Optimization, caching, indexing improvements
- **User Experience**: API design, error messages, documentation
- **Developer Experience**: Tooling, testing, development workflow
- **Infrastructure**: Deployment, monitoring, scaling

### Contributing Code

Ready to write code? Excellent!

**Code contribution areas:**
1. **RAG Pipeline**: Improve retrieval, ranking, response generation
2. **ETL Pipeline**: Add document sources, enhance parsing, improve chunking
3. **API**: New endpoints, enhanced filtering, better error handling
4. **Database**: Schema improvements, query optimization, migrations
5. **Testing**: Unit tests, integration tests, test coverage
6. **Documentation**: Code comments, API docs, user guides
7. **Infrastructure**: Docker, deployment, CI/CD improvements

**Before starting development:**
1. Read the [Development Setup Guide](dev-setup.md)
2. Review the [Code Style Guide](code-style.md)
3. Understand the [Testing Requirements](testing.md)
4. Check the [Pull Request Guidelines](pull-requests.md)

### Improving Documentation

Documentation improvements are always welcome!

**Documentation types:**
- **User Guides**: Help users understand features and workflows
- **Developer Guides**: Explain architecture and implementation details
- **API Documentation**: Document endpoints, parameters, responses
- **Code Comments**: Improve inline documentation and docstrings
- **Examples**: Add code examples and usage patterns
- **Troubleshooting**: Document common issues and solutions

**Documentation locations:**
- User guides: `/docs/user-guide/`
- Developer guides: `/docs/developer-guide/`
- Getting started: `/docs/getting-started/`
- Reference: `/docs/reference/`
- Code docstrings: Throughout the codebase

### Adding Document Sources

One of the most valuable contributions is adding new regulatory document sources!

**Process:**
1. Identify a relevant Australian environmental/planning regulation source
2. Review the [Document Sources Guide](../user-guide/document-sources.md)
3. Implement a scraper using the plugin system
4. Add comprehensive tests
5. Document the source configuration
6. Submit a pull request

**See also:**
- [Plugin System Architecture](../developer-guide/architecture/plugin-system.md)
- [Plugin API Reference](../reference/plugin-api.md)

### Reviewing Pull Requests

Help maintain code quality by reviewing pull requests!

**What to look for:**
- Code follows style guidelines
- Tests are comprehensive and passing
- Documentation is updated
- Changes align with project goals
- No breaking changes without migration path
- Security considerations addressed

**Review guidelines:**
- Be constructive and respectful
- Explain reasoning behind suggestions
- Distinguish between required changes and suggestions
- Approve when ready, request changes when needed
- Test the changes locally when possible

## Getting Started

### Quick Start Checklist

- [ ] Read this contributor overview
- [ ] Review the [Code of Conduct](#code-of-conduct)
- [ ] Set up development environment ([Dev Setup Guide](dev-setup.md))
- [ ] Read the code style guide ([Code Style](code-style.md))
- [ ] Understand testing requirements ([Testing Guide](testing.md))
- [ ] Review pull request workflow ([PR Guide](pull-requests.md))
- [ ] Find an issue to work on or create one
- [ ] Join community discussions (GitHub Discussions/Issues)

### Finding Issues to Work On

**Good first issues:**
Look for issues labeled `good first issue` - these are beginner-friendly and well-documented.

**Help wanted:**
Issues labeled `help wanted` indicate where maintainers need community assistance.

**Areas needing help:**
- Adding new document sources
- Improving test coverage
- Enhancing documentation
- Performance optimization
- Bug fixes

**Claiming an issue:**
1. Comment on the issue expressing interest
2. Wait for maintainer acknowledgment
3. Ask clarifying questions if needed
4. Start working once acknowledged

## Contribution Workflow

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/green-gov-rag.git
cd green-gov-rag

# Add upstream remote
git remote add upstream https://github.com/sdp5/green-gov-rag.git
```

### 2. Create a Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create a feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

**Branch naming conventions:**
- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation changes
- `refactor/description` - Code refactoring
- `test/description` - Test additions/improvements

### 3. Make Changes

Follow the development workflow:
1. Write code following [code style guidelines](code-style.md)
2. Add/update tests ([testing guide](testing.md))
3. Update documentation as needed
4. Run linters and formatters
5. Ensure all tests pass

### 4. Commit Changes

Follow commit message guidelines:

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: Add support for Victorian planning schemes"
```

See [Pull Request Guide](pull-requests.md#commit-message-guidelines) for detailed commit message conventions.

### 5. Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create pull request on GitHub
# Fill out the PR template completely
```

### 6. Code Review

- Respond to review feedback promptly
- Make requested changes in new commits
- Push updates to the same branch
- Engage in constructive discussion
- Mark conversations as resolved when addressed

### 7. Merge

Once approved:
- Maintainers will merge your PR
- Your changes will be included in the next release
- Delete your feature branch

## Contributor License Agreement

### Agreement

By contributing to GreenGovRAG, you agree that:

1. **You grant the project a license** to use your contribution under the project's open source license
2. **You have the right to grant this license** - your contribution is your original work or you have permission to contribute it
3. **You understand your contribution is public** and will be maintained as part of the project
4. **You agree to the Code of Conduct** and will follow it in all project interactions

### Intellectual Property

- All contributions remain open source under the project license
- You retain copyright to your contributions
- You grant a perpetual, irrevocable license for the project to use your contribution
- The project may relicense in the future (with community input)

### Third-Party Code

When contributing code from third-party sources:
1. Ensure it's compatible with our license
2. Maintain original copyright notices
3. Document the source and license
4. Get approval from maintainers before including

## Recognition and Attribution

We value all contributions and ensure contributors are recognized!

### Contributors List

All contributors are listed in:
- `CONTRIBUTORS.md` file
- GitHub contributors page
- Release notes for their contributions

### How We Recognize Contributors

**Code Contributors:**
- Listed in git commit history
- Mentioned in release notes
- Added to CONTRIBUTORS.md

**Documentation Contributors:**
- Credited in documentation
- Listed in CONTRIBUTORS.md
- Mentioned in release notes

**Issue Reporters:**
- Mentioned in issue resolution commits
- Credited in release notes for significant bugs

**Reviewers:**
- Acknowledged for thorough reviews
- Mentioned in PR discussions

### Adding Yourself as a Contributor

When making your first contribution:
1. Add your name to `CONTRIBUTORS.md` (if it doesn't exist, create it)
2. Include your GitHub username
3. Briefly describe your contribution
4. Optionally include your website or social media

**Format:**
```markdown
## Contributors

- **Your Name** (@github-username) - Description of contribution
  - Website: https://yoursite.com (optional)
```

### Release Credits

Contributors to each release are credited in:
- GitHub release notes
- CHANGELOG.md
- Project announcements

## Getting Help

### Questions About Contributing

**For general questions:**
- Check existing [documentation](../index.md)
- Search [closed issues](https://github.com/sdp5/green-gov-rag/issues?q=is%3Aissue+is%3Aclosed)
- Ask in GitHub Discussions (if enabled)
- Create a new issue with the `question` label

**For development help:**
- Review the [Developer Guide](../developer-guide/)
- Check the [Troubleshooting Guide](../user-guide/troubleshooting.md)
- Ask in your pull request
- Tag maintainers in issues/PRs (sparingly)

**For urgent issues:**
- Security vulnerabilities: Email contact@sundeep.id.au
- Critical bugs: Create issue with `critical` label
- Infrastructure issues: Contact maintainers

### Community Resources

- **GitHub Issues**: Bug reports, feature requests, discussions
- **GitHub Pull Requests**: Code review and collaboration
- **Documentation**: Comprehensive guides and references
- **Email**: contact@sundeep.id.au (for sensitive matters)

### Response Time Expectations

- **Issues**: Typically within 2-3 business days
- **Pull Requests**: Initial review within 3-5 business days
- **Security Issues**: Within 24 hours
- **Questions**: Within 1 week

*Note: GreenGovRAG is maintained by volunteers. Response times may vary.*

## Next Steps

Now that you understand the contribution process:

1. **Set up your environment**: Follow the [Development Setup Guide](dev-setup.md)
2. **Learn the code style**: Review the [Code Style Guide](code-style.md)
3. **Understand testing**: Read the [Testing Guide](testing.md)
4. **Make your first contribution**: Check out [good first issues](https://github.com/sdp5/green-gov-rag/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)

## Project Maintainers

- **Sundeep Anand** (@sdp5) - Project Creator and Lead Maintainer
  - Email: contact@sundeep.id.au
  - Responsible for: Overall direction, code review, releases

## Acknowledgments

Thank you to all contributors who help make GreenGovRAG better! Your time, expertise, and dedication to improving access to environmental regulations is truly appreciated.

Special thanks to:
- The LangChain community for excellent RAG tooling
- The FastAPI team for the robust API framework
- All open source projects that make GreenGovRAG possible

---

**Questions or concerns about this guide?**

Open an issue or contact the maintainers at contact@sundeep.id.au

**Happy contributing!**
