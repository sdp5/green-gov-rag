# Support

> Getting help with GreenGovRAG

## Community Support

### GitHub Issues

The primary support channel is GitHub Issues:

**[GitHub Issues](https://github.com/sdp5/green-gov-rag/issues)**

#### Before Creating an Issue

1. **Search existing issues** to avoid duplicates
2. **Check documentation** (you're reading it!)
3. **Review troubleshooting guide**: [User Guide > Troubleshooting](../user-guide/troubleshooting.md)
4. **Check discussions** for Q&A: [GitHub Discussions](https://github.com/sdp5/green-gov-rag/discussions)

#### Creating a Good Issue

Include:

**For Bug Reports**:

- GreenGovRAG version (`greengovrag-cli --version`)
- Python version (`python --version`)
- Operating system (Linux, macOS, Windows)
- Deployment type (Docker, AWS, Azure, local)
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error messages and logs
- Relevant configuration (redact secrets!)

**Example Bug Report**:
```markdown
**GreenGovRAG Version**: 0.1.0
**Python**: 3.12.0
**OS**: Ubuntu 22.04
**Deployment**: Docker Compose

**Steps to Reproduce**:
1. Run `docker-compose up`
2. Query API: `curl -X POST http://localhost:8000/api/query -d '{"query": "test"}'`
3. Observe error

**Expected**: 200 OK with answer
**Actual**: 500 Internal Server Error

**Error Log**:
```
ERROR: Qdrant connection timeout
```

**Configuration**:
```env
VECTOR_STORE_TYPE=qdrant
QDRANT_URL=http://qdrant:6333
```
```

**For Feature Requests**:
- Clear use case description
- Why existing features don't meet the need
- Proposed solution (optional)
- Alternatives considered (optional)

**Example Feature Request**:
```markdown
**Feature**: Support for Victoria's Planning & Environment Act

**Use Case**: Users in Victoria need to query state-specific planning legislation, but currently only NSW and SA are supported.

**Proposed Solution**: Add VIC legislation parser in `backend/green_gov_rag/etl/sources/vic_legislation.py`

**Alternatives**: Manual document upload (not ideal for updates)
```

### GitHub Discussions

For questions, ideas, and general discussion:

**[GitHub Discussions](https://github.com/sdp5/green-gov-rag/discussions)**

**Categories**:

- **Q&A**: Ask questions
- **Ideas**: Propose new features
- **Show and Tell**: Share your use cases
- **General**: Everything else

## Professional Support

For commercial deployments, custom integrations, or dedicated support:

**Email**: contact@sundeep.id.au

**Services offered**:

- Custom document source development
- Deployment assistance (AWS, Azure, on-premises)
- Performance tuning and optimization
- Integration with existing systems
- Training and workshops
- SLA-based support contracts

## Documentation

### Official Documentation

- **Getting Started**: [Installation](../getting-started/installation.md) | [Quick Start](../getting-started/quickstart.md)
- **User Guide**: [Querying](../user-guide/querying.md) | [Troubleshooting](../user-guide/troubleshooting.md)
- **Deployment**: [AWS](../deployment/aws.md) | [Azure](../deployment/azure.md) | [Local Docker](../deployment/local-docker.md)
- **Developer Guide**: [Architecture](../developer-guide/architecture/overview.md) | [LLM Config](../developer-guide/llm-config.md)
- **API Reference**: [REST API](../api-reference/rest-api.md) | [Python API](../api-reference/python/rag.md)
- **Reference**: [CLI](../reference/cli-reference.md) | [Config](../reference/config-reference.md) | [Glossary](../reference/glossary.md)

### Video Tutorials

Coming soon! Subscribe to updates:

- **YouTube**: TBD
- **Newsletter**: TBD

### Blog Posts

Coming soon! Follow for updates:

- **Blog**: [Sundeep's Blog](https://sundeep.id.au/blog)

## Common Issues

### Installation Problems

**Issue**: `pip install` fails with dependency conflicts

**Solution**:
```bash
# Use Python 3.12+ in virtual environment
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]
```

**Issue**: Docker Compose fails with port conflicts

**Solution**:
```bash
# Change ports in docker-compose.yml
services:
  backend:
    ports:
      - "8001:8000"  # Use 8001 instead of 8000
```

### Database Issues

**Issue**: `pgvector extension not found`

**Solution**:
```bash
# Rebuild database container
docker-compose down -v
docker-compose up postgres
# Wait for initialization, then:
docker-compose up backend
```

**Issue**: Connection pool exhausted

**Solution**:
```bash
# Increase pool size in .env
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=20
```

### Vector Store Issues

**Issue**: Qdrant connection timeout

**Solution**:
```bash
# Check Qdrant is running
docker ps | grep qdrant

# Check connection URL
curl http://localhost:6333/health
```

**Issue**: FAISS index not found

**Solution**:
```bash
# Re-run ETL pipeline
greengovrag-cli etl run-pipeline
```

### LLM Provider Issues

**Issue**: OpenAI API rate limit exceeded

**Solution**:
```bash
# Use gpt-5-mini instead of gpt-5
LLM_MODEL=gpt-5-mini

# Or reduce concurrent requests
API_RATE_LIMIT=10/minute
```

**Issue**: Azure OpenAI deployment not found

**Solution**:
```bash
# Verify deployment name matches model
az cognitiveservices account deployment list \
  --name your-openai-resource \
  --resource-group your-rg

# Update .env
AZURE_OPENAI_DEPLOYMENT=<correct-deployment-name>
```

## Response Times

**GitHub Issues**:

- **Bug reports**: 1-3 business days
- **Feature requests**: 1-7 business days
- **Questions**: 1-5 business days

**Professional Support** (paid):

- **Critical issues**: 4 hours (business hours)
- **High priority**: 1 business day
- **Normal priority**: 3 business days

**Note**: These are targets, not guarantees. Response times may vary.

## Contributing

Help improve GreenGovRAG!

### Ways to Contribute

1. **Report bugs** via GitHub Issues
2. **Suggest features** via GitHub Discussions
3. **Fix bugs** via Pull Requests
4. **Add documentation** via Pull Requests
5. **Answer questions** in Discussions
6. **Share use cases** in Show and Tell

See [Contributor Guide](../contributor-guide/overview.md) for details.

### Recognition

Contributors are listed in:

- [Changelog](changelog.md) (for significant contributions)
- [GitHub Contributors](https://github.com/sdp5/green-gov-rag/graphs/contributors)
- Release notes

## Communication Channels

### Official Channels

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: Questions, ideas, general discussion
- **Email**: contact@sundeep.id.au (professional support)

### Unofficial Channels

None at this time. We recommend using official channels to ensure:

- Searchable history
- Proper tracking
- Transparency

## Code of Conduct

GreenGovRAG follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

**Summary**:

- Be respectful and inclusive
- Welcome diverse perspectives
- Focus on constructive feedback
- No harassment or discrimination

**Reporting**: contact@sundeep.id.au

## Security Issues

**DO NOT** report security vulnerabilities via public GitHub Issues.

**Email**: contact@sundeep.id.au with subject "SECURITY"

**Response time**: 24-48 hours (expedited for critical issues)

See [Security Policy](https://github.com/sdp5/green-gov-rag/security/policy) for details.

## Roadmap

See [GitHub Projects](https://github.com/sdp5/green-gov-rag/projects) for:

- Planned features
- Current priorities
- Release schedule

Upvote features you'd like to see in GitHub Discussions!

## Stay Updated

- **GitHub Releases**: [Latest Releases](https://github.com/sdp5/green-gov-rag/releases)
- **GitHub Watch**: Click "Watch" → "Custom" → "Releases"
- **Changelog**: [Changelog](changelog.md)

## Resources

### External Resources

- **LangChain Documentation**: [python.langchain.com/docs](https://python.langchain.com/docs)
- **FastAPI Documentation**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **Qdrant Documentation**: [qdrant.tech/documentation](https://qdrant.tech/documentation)
- **PostgreSQL Documentation**: [postgresql.org/docs](https://www.postgresql.org/docs)
- **AWS Documentation**: [docs.aws.amazon.com](https://docs.aws.amazon.com)
- **Azure Documentation**: [docs.microsoft.com/azure](https://docs.microsoft.com/azure)

### Related Projects

- **LangChain**: RAG framework
- **LlamaIndex**: Alternative RAG framework
- **Haystack**: NLP framework with RAG support
- **Weaviate**: Vector database
- **Chroma**: Vector database

## Acknowledgments

Thank you to:

- All contributors
- Open-source community
- Australian government for open data
- Users providing feedback

---

**Last Updated**: 2025-11-22

**Need Help?**

- **Issues**: [GitHub Issues](https://github.com/sdp5/green-gov-rag/issues)
- **Discussions**: [GitHub Discussions](https://github.com/sdp5/green-gov-rag/discussions)
- **Email**: contact@sundeep.id.au
