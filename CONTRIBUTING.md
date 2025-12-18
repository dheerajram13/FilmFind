# Contributing to FilmFind

Thank you for your interest in contributing to FilmFind! This document provides guidelines and instructions for contributing to this AI-powered movie discovery engine.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Areas for Contribution](#areas-for-contribution)
- [Project Structure](#project-structure)
- [Getting Help](#getting-help)

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards other community members

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Trolling or insulting/derogatory comments
- Publishing others' private information
- Any conduct inappropriate in a professional setting

## Getting Started

### Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** installed
- **Node.js 18+** and npm/yarn
- **PostgreSQL 14+** (or Supabase account)
- **Redis** (local or Upstash account)
- **Git** for version control
- A **GitHub account**

### First-Time Contributors

1. **Star the repository** to show your support
2. **Fork the repository** to your GitHub account
3. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/FilmFind.git
   cd FilmFind
   ```
4. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/dheerajram13/FilmFind.git
   ```

## Development Setup

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

5. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys and configuration
   ```

6. Run database migrations:
   ```bash
   alembic upgrade head
   ```

7. Start the development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend Setup (if applicable)

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create environment file:
   ```bash
   cp .env.local.example .env.local
   # Edit .env.local with your configuration
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```

## Development Workflow

### 1. Create a Feature Branch

Always create a new branch for your work:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b bugfix/issue-number-description
# or
git checkout -b docs/documentation-improvement
```

Branch naming conventions:
- `feature/` - New features
- `bugfix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions or modifications
- `chore/` - Maintenance tasks

### 2. Keep Your Branch Updated

Regularly sync with the upstream repository:

```bash
git fetch upstream
git rebase upstream/main
```

### 3. Make Your Changes

- Write clean, readable code
- Follow the project's coding standards
- Add tests for new functionality
- Update documentation as needed

### 4. Run Tests Locally

Before committing, ensure all tests pass:

```bash
# Backend tests
cd backend
python -m pytest

# With coverage
python -m pytest --cov=app --cov-report=html

# Run specific test file
python -m pytest tests/test_query_parser.py -v
```

### 5. Lint and Format

Pre-commit hooks will run automatically, but you can also run manually:

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Run ruff linter
python -m ruff check . --fix

# Run ruff formatter
python -m ruff format .

# Run type checking
mypy app/
```

## Coding Standards

### Python Code Style

We use **Ruff** for linting and formatting, which enforces:

- **Line length**: Maximum 100 characters
- **Indentation**: 4 spaces (no tabs)
- **Import sorting**: Automatic with Ruff
- **Type hints**: Required for all function signatures
- **Docstrings**: Required for all public functions and classes

#### Example:

```python
from typing import List, Optional

from app.schemas.query import QueryIntent
from app.utils.logger import get_logger

logger = get_logger(__name__)


def parse_query(
    query: str,
    max_results: int = 10,
    filters: Optional[dict] = None
) -> QueryIntent:
    """
    Parse a natural language query into structured intent.

    Args:
        query: The user's natural language query
        max_results: Maximum number of results to return
        filters: Optional filters to apply

    Returns:
        QueryIntent object with extracted information

    Raises:
        ValueError: If query is empty or invalid
    """
    if not query.strip():
        raise ValueError("Query cannot be empty")

    logger.info(f"Parsing query: {query}")
    # Implementation here
    return QueryIntent(raw_query=query)
```

### Type Hints

Always use type hints for function parameters and return values:

```python
# Good
def calculate_score(
    semantic_score: float,
    popularity_score: float,
    weights: ScoringWeights
) -> float:
    return semantic_score * weights.semantic + popularity_score * weights.popularity

# Avoid
def calculate_score(semantic_score, popularity_score, weights):
    return semantic_score * weights.semantic + popularity_score * weights.popularity
```

### Imports Organization

Ruff automatically organizes imports into three groups:

```python
# Standard library imports
import os
from typing import List, Optional

# Third-party imports
from fastapi import APIRouter, Depends
from pydantic import BaseModel

# Local application imports
from app.core.config import settings
from app.services.embedding_service import EmbeddingService
```

### Error Handling

Use specific exceptions and provide meaningful error messages:

```python
# Good
try:
    result = fetch_movie_data(movie_id)
except HTTPError as e:
    logger.error(f"Failed to fetch movie {movie_id}: {e}")
    raise MovieNotFoundError(f"Movie {movie_id} not found") from e

# Avoid
try:
    result = fetch_movie_data(movie_id)
except:
    raise Exception("Error")
```

### Logging

Use structured logging with appropriate levels:

```python
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Use appropriate log levels
logger.debug("Detailed debugging information")
logger.info("General informational messages")
logger.warning("Warning messages for potentially harmful situations")
logger.error("Error messages for serious problems")
logger.critical("Critical messages for very serious errors")
```

## Testing Guidelines

### Writing Tests

We use **pytest** for testing. All new features should include tests.

#### Test File Structure

```python
import pytest
from app.services.query_parser import QueryParser


class TestQueryParser:
    """Test suite for QueryParser."""

    @pytest.fixture
    def parser(self):
        """Fixture to create a QueryParser instance."""
        return QueryParser()

    def test_parse_simple_query(self, parser):
        """Test parsing a simple movie query."""
        result = parser.parse("action movies")
        assert result.genres == ["Action"]
        assert result.raw_query == "action movies"

    def test_parse_with_reference(self, parser):
        """Test parsing query with reference movie."""
        result = parser.parse("movies like Interstellar")
        assert "Interstellar" in result.reference_titles
        assert result.genres is not None

    @pytest.mark.parametrize("query,expected_genre", [
        ("horror films", ["Horror"]),
        ("romantic comedies", ["Romance", "Comedy"]),
        ("sci-fi thrillers", ["Science Fiction", "Thriller"]),
    ])
    def test_genre_extraction(self, parser, query, expected_genre):
        """Test genre extraction from various queries."""
        result = parser.parse(query)
        assert all(genre in result.genres for genre in expected_genre)
```

### Test Coverage

- Aim for **80%+ code coverage**
- Critical paths should have **100% coverage**
- Test both success and failure cases
- Test edge cases and boundary conditions

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_query_parser.py

# Run specific test
pytest tests/test_query_parser.py::TestQueryParser::test_parse_simple_query

# Run with verbose output
pytest -v

# Run tests matching a pattern
pytest -k "test_parse"
```

### Test Categories

1. **Unit Tests**: Test individual functions/methods
2. **Integration Tests**: Test component interactions
3. **End-to-End Tests**: Test complete workflows
4. **Performance Tests**: Test performance requirements

## Commit Guidelines

### Commit Message Format

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks, dependency updates
- `ci`: CI/CD changes

#### Examples

```bash
feat(search): add semantic similarity scoring

Implemented multi-signal scoring engine that combines semantic similarity,
popularity, and rating scores with configurable weights.

Closes #42

---

fix(query-parser): handle empty query strings

Added validation to prevent errors when parsing empty or whitespace-only queries.

Fixes #38

---

docs(readme): update installation instructions

Added detailed steps for setting up the development environment on Windows.

---

test(scoring): add tests for scoring engine

Added comprehensive test suite for ScoringEngine covering all signal extractors
and weight presets.
```

### Commit Best Practices

- Write clear, descriptive commit messages
- Keep commits focused on a single change
- Commit early and often
- Don't commit commented-out code
- Don't commit debugging statements
- Never commit secrets or API keys

## Pull Request Process

### Before Creating a PR

1. **Ensure all tests pass**:
   ```bash
   pytest
   ```

2. **Run linters and formatters**:
   ```bash
   pre-commit run --all-files
   ```

3. **Update documentation** if needed

4. **Rebase on latest main**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

### Creating a Pull Request

1. **Push your branch** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Open a Pull Request** on GitHub with:
   - **Clear title** following commit conventions
   - **Description** of changes made
   - **Related issue** number (if applicable)
   - **Screenshots** (for UI changes)
   - **Testing steps** for reviewers

### PR Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Related Issue
Closes #(issue number)

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
- [ ] All existing tests pass
- [ ] Added new tests for new functionality
- [ ] Manually tested the changes
- [ ] Updated documentation

## Screenshots (if applicable)
Add screenshots here

## Checklist
- [ ] My code follows the project's coding standards
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
```

### Review Process

- Be patient and respectful during reviews
- Address all review comments
- Push additional commits to your branch (don't force push during review)
- Mark conversations as resolved once addressed
- Request re-review when ready

### After Approval

Once approved, a maintainer will merge your PR. After merging:

1. Delete your feature branch:
   ```bash
   git branch -d feature/your-feature-name
   git push origin --delete feature/your-feature-name
   ```

2. Update your local main:
   ```bash
   git checkout main
   git pull upstream main
   ```

## Areas for Contribution

### Good First Issues

Look for issues labeled `good first issue` or `beginner-friendly`:

- Documentation improvements
- Adding tests for existing code
- Fixing typos or broken links
- Small bug fixes
- Code cleanup and refactoring

### Feature Development

- New query understanding patterns
- Additional signal extractors
- UI/UX improvements
- Performance optimizations
- New filtering capabilities

### Infrastructure

- CI/CD improvements
- Docker optimization
- Monitoring and logging enhancements
- Database migration improvements

### Documentation

- API documentation
- Code examples
- Architecture diagrams
- Tutorial content
- Translation to other languages

### Testing

- Increase test coverage
- Add integration tests
- Performance benchmarks
- Load testing

## Project Structure

Understanding the project structure helps you navigate the codebase:

```
FilmFind/
├── backend/
│   ├── app/
│   │   ├── api/              # API routes and endpoints
│   │   ├── core/             # Core configuration and constants
│   │   ├── models/           # Database models (SQLAlchemy)
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic and services
│   │   └── utils/            # Utility functions
│   ├── tests/                # Test files
│   ├── scripts/              # Utility scripts
│   ├── alembic/              # Database migrations
│   └── requirements.txt      # Python dependencies
├── frontend/                 # Next.js frontend (if applicable)
├── docs/                     # Documentation
└── images/                   # Architecture diagrams
```

### Key Files

- `backend/app/main.py` - FastAPI application entry point
- `backend/app/core/config.py` - Configuration management
- `backend/app/core/constants.py` - Application constants
- `backend/pyproject.toml` - Python project configuration
- `backend/.ruff.toml` - Ruff linter configuration
- `backend/.pre-commit-config.yaml` - Pre-commit hooks

## Getting Help

### Resources

- **Documentation**: Check the [README](README.md) and [docs/](docs/) folder
- **Issues**: Browse existing [GitHub Issues](https://github.com/dheerajram13/FilmFind/issues)
- **Discussions**: Join [GitHub Discussions](https://github.com/dheerajram13/FilmFind/discussions)

### Asking Questions

Before asking a question:

1. Search existing issues and discussions
2. Check the documentation
3. Try debugging with logs

When asking:

- Provide context and background
- Include error messages and logs
- Share what you've already tried
- Use code blocks for code snippets

### Reporting Bugs

Use the bug report template and include:

- **Description**: Clear description of the bug
- **Steps to Reproduce**: Detailed steps to reproduce the issue
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: OS, Python version, etc.
- **Logs**: Relevant log output
- **Screenshots**: If applicable

### Suggesting Features

Use the feature request template and include:

- **Problem**: What problem does this solve?
- **Proposed Solution**: How should it work?
- **Alternatives**: Other solutions you considered
- **Additional Context**: Any other relevant information

## Recognition

Contributors will be recognized in:

- The project's README
- Release notes for significant contributions
- The contributors page on GitHub

## License

By contributing, you agree that your contributions will be licensed under the same [MIT License](LICENSE) that covers this project.

---

**Thank you for contributing to FilmFind!**

If you have questions about contributing, feel free to reach out to the maintainers or open a discussion on GitHub.

**Maintainer Contact:**
- GitHub: [@dheerajram13](https://github.com/dheerajram13)
- Email: sriramadheeraj@gmail.com
