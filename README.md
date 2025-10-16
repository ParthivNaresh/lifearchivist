# LifeArchivist

[![CI Pipeline](https://github.com/parthivnaresh/lifearchivist/actions/workflows/ci.yml/badge.svg)](https://github.com/parthivnaresh/lifearchivist/actions/workflows/ci.yml)
[![Unit Tests](https://github.com/parthivnaresh/lifearchivist/actions/workflows/test-unit.yml/badge.svg)](https://github.com/parthivnaresh/lifearchivist/actions/workflows/test-unit.yml)
[![Code Linting](https://github.com/parthivnaresh/lifearchivist/actions/workflows/lint.yml/badge.svg)](https://github.com/parthivnaresh/lifearchivist/actions/workflows/lint.yml)
[![codecov](https://codecov.io/gh/parthivnaresh/lifearchivist/branch/main/graph/badge.svg)](https://codecov.io/gh/parthivnaresh/lifearchivist)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=parthivnaresh_lifearchivist&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=parthivnaresh_lifearchivist)
[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/parthivnaresh/lifearchivist/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)

---

## 🚀 Quick Links

- **Documentation**: [docs.lifearchivist.dev](https://docs.lifearchivist.dev)
- **Repository**: [github.com/parthivnaresh/lifearchivist](https://github.com/parthivnaresh/lifearchivist)
- **Issues**: [Report a bug or request a feature](https://github.com/parthivnaresh/lifearchivist/issues)

---

## 🛠️ Tech Stack

- **Backend**: FastAPI, Python 3.12
- **Vector DB**: Qdrant
- **Embeddings**: Sentence Transformers
- **LLM**: Ollama (local)
- **Storage**: Redis, SQLAlchemy
- **Search**: BM25 + Semantic Search
- **Desktop**: Electron + React + TypeScript

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/parthivnaresh/lifearchivist.git
cd lifearchivist

# Install dependencies with Poetry
poetry install

# Set up environment
cp .env.example .env

# Start services (Redis, Qdrant)
docker-compose up -d

# Run the application
poetry run uvicorn lifearchivist.server.main:app --reload
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Parthiv Naresh**
- GitHub: [@parthivnaresh](https://github.com/parthivnaresh)
- Email: parthivnaresh@gmail.com

---

Built with modern Python tooling and best practices for local-first, privacy-preserving personal knowledge management.
