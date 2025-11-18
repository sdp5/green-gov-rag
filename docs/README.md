# GreenGovRAG Documentation Guide

## How Documentation Works

### Auto-Generated API Docs from Python Docstrings

The documentation system uses **mkdocstrings** to automatically extract and render Python docstrings.

#### How It Works

1. **Write Google-style docstrings** in your Python code:
   ```python
   def create_vector_store(store_type: str) -> VectorStore:
       """Create a vector store instance.

       Args:
           store_type: Type of vector store ('faiss' or 'qdrant')

       Returns:
           Initialized vector store instance

       Raises:
           ValueError: If store_type is not supported

       Example:
           ```python
           store = create_vector_store('qdrant')
           ```
       """
       pass
   ```

2. **Reference the module** in documentation:
   ```markdown
   # In docs/api-reference/python/rag.md

   ## Vector Store Factory

   ::: green_gov_rag.rag.vector_store_factory
       options:
         show_source: true
         heading_level: 3
   ```

3. **mkdocstrings extracts** the docstring and renders it beautifully with:
   - Function signatures
   - Parameter descriptions
   - Return types
   - Examples
   - Source code links

#### API Reference Structure

```
docs/api-reference/
├── rest-api.md              # REST API endpoints (manual)
└── python/
    ├── rag.md               # RAG module (auto-generated)
    ├── etl.md               # ETL module (auto-generated)
    ├── models.md            # Database models (auto-generated)
    └── cloud.md             # Cloud module (auto-generated)
```

## Professional White/Green Theme

The documentation uses a professional white and green color scheme:

### Color Palette

- **Primary Green**: `#2e7d32` (Forest green)
- **Accent Teal**: `#00897b`
- **Light Backgrounds**: `#ffffff`, `#f5f5f5`
- **Green highlights**: `#e8f5e9`

### Theme Features

- **Light mode**: Clean white background with green accents
- **Dark mode**: Dark background with teal/green accents
- **Professional fonts**: Inter (text), Roboto Mono (code)
- **Custom CSS**: `docs/stylesheets/extra.css`
- **Responsive design**: Mobile-friendly
- **Code highlighting**: Professional syntax highlighting

### Customization

Edit `docs/stylesheets/extra.css` to customize colors:

```css
:root {
  --md-primary-fg-color: #2e7d32;  /* Change primary green */
  --md-accent-fg-color: #00897b;   /* Change accent teal */
}
```

## Serving Documentation Locally

### Quick Start

```bash
# Option 1: Using the serve script
./docs/serve.sh

# Option 2: Manual
cd docs/
source .venv/bin/activate
mkdocs serve
```

Visit: http://127.0.0.1:8000

### Building Static Site

```bash
cd docs/
source .venv/bin/activate
mkdocs build

# Output in: site/ (parent directory)
```

## Adding New Documentation

### 1. Create New Page

```bash
# Example: Add a new guide
touch docs/docs_src/user-guide/new-feature.md
```

### 2. Add to Navigation

Edit `docs/mkdocs.yml`:
```yaml
nav:
  - User Guide:
      - Querying: user-guide/querying.md
      - New Feature: user-guide/new-feature.md  # Add here
```

### 3. Write Content

Use Markdown with Material extensions:

```markdown
# New Feature

> Quick description

## Overview

Explain the feature...

!!! note "Important"
    Callout boxes for notes

=== "Tab 1"
    Content for tab 1

=== "Tab 2"
    Content for tab 2

## Code Example

```python
# Your code here
```

## See Also

- [Related Guide](./related.md)
```

## Documentation Standards

### File Naming

- Lowercase with hyphens: `getting-started.md`
- Descriptive names: `vector-stores.md` not `vs.md`

### Headers

- Use ATX-style: `# Header` not `Header\n======`
- One H1 per page
- Logical hierarchy: H1 → H2 → H3

### Cross-References

```markdown
[Link text](../path/to/file.md)
[Link to section](../path/to/file.md#section-id)
```

### Code Blocks

Always specify language:
````markdown
```python
# Python code
```

```bash
# Bash commands
```
````

### Admonitions

```markdown
!!! note "Title"
    Note content

!!! warning
    Warning content

!!! tip "Pro Tip"
    Tip content
```

## Directory Structure

```
docs/
├── mkdocs.yml                    # MkDocs configuration
├── docs_src/                     # Documentation source files
│   ├── index.md                  # Home page
│   ├── getting-started/          # Installation, quickstart
│   ├── user-guide/               # How to use
│   ├── contributor-guide/        # How to contribute
│   ├── developer-guide/          # Architecture, deep dives
│   │   ├── architecture/         # System design
│   │   ├── metadata-standards.md
│   │   ├── citations.md
│   │   └── cloud-storage.md
│   ├── deployment/               # Deployment guides
│   ├── api-reference/            # API documentation
│   │   ├── rest-api.md
│   │   └── python/               # Auto-generated
│   │       ├── rag.md
│   │       ├── etl.md
│   │       ├── models.md
│   │       └── cloud.md
│   ├── reference/                # Quick references
│   ├── about/                    # Changelog, license
│   ├── stylesheets/
│   │   └── extra.css             # Custom CSS
│   ├── javascripts/
│   │   └── extra.js              # Custom JavaScript
│   └── assets/                   # Images, logos
├── .venv/                        # Python virtual environment
├── requirements.txt              # MkDocs dependencies
└── serve.sh                      # Local server script

site/                             # Built documentation (in parent directory)
```

## Best Practices

### 1. Keep Documentation Current

- Update docs when changing code
- Add docs before merging PRs
- Review docs quarterly

### 2. Test Documentation

```bash
# Build in strict mode (fails on warnings)
mkdocs build --strict

# Check all links
# (Install linkchecker: pip install linkchecker)
linkchecker site/
```

### 3. Use Examples

- Show real, working code
- Include expected output
- Test examples regularly

### 4. Cross-Reference

- Link related documentation
- Don't duplicate content
- Use "See Also" sections

## Deployment

### Automated GitHub Pages Deployment

Documentation is **automatically deployed** to GitHub Pages when changes are pushed to `main` or `docs` branches:

- **Workflow**: `.github/workflows/docs-deploy.yml`
- **URL**: https://sdp5.github.io/green-gov-rag/
- **Trigger**: Push to `main`/`docs` branches (docs changes only) or manual workflow dispatch

The workflow:
1. Builds the MkDocs site in strict mode
2. Uploads the artifact
3. Deploys to GitHub Pages

#### Manual Deployment

You can also deploy manually:

```bash
# Using GitHub Actions (recommended)
# Go to: Actions → Deploy Documentation → Run workflow

# Or using MkDocs CLI
cd docs/
mkdocs gh-deploy --force

# Available at: https://sdp5.github.io/green-gov-rag/
```

#### First-Time Setup

To enable GitHub Pages in your repository:

1. Go to **Settings** → **Pages**
2. Set **Source** to "GitHub Actions"
3. The next push to `main` will trigger automatic deployment

### Read the Docs

1. Connect repository to Read the Docs
2. Add `.readthedocs.yml`:
   ```yaml
   version: 2
   mkdocs:
     configuration: docs/mkdocs.yml
   python:
     version: 3.12
     install:
       - requirements: docs/requirements.txt
   ```

### Custom Domain

1. Deploy to GitHub Pages or Read the Docs
2. Add CNAME record: `docs.yourdomain.com`
3. Update `site_url` in `docs/mkdocs.yml`

## Troubleshooting

### Build Warnings

```bash
# View all warnings
mkdocs build --strict 2>&1 | grep WARNING

# Common issues:
# - Broken links: Fix paths in Markdown
# - Missing files: Add placeholder or remove from nav
# - Invalid YAML: Check mkdocs.yml syntax
```

### Slow Builds

```bash
# Disable git-revision-date plugin for faster builds
# Comment out in docs/mkdocs.yml:
# - git-revision-date-localized
```

### Port Already in Use

```bash
# Use different port
mkdocs serve --dev-addr=127.0.0.1:8001
```

## Resources

- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [mkdocstrings](https://mkdocstrings.github.io/)
- [Markdown Guide](https://www.markdownguide.org/)

---

**Need help?** Open an issue or contact: contact@sundeep.id.au
