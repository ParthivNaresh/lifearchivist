# LifeArchivist

<div align="center">

**Local-first, privacy-preserving personal knowledge system with MCP architecture**

### Build & Quality

[![Unit Tests](https://github.com/ParthivNaresh/lifearchivist/actions/workflows/test-unit.yml/badge.svg)](https://github.com/ParthivNaresh/lifearchivist/actions/workflows/test-unit.yml)
[![Code Linting](https://github.com/ParthivNaresh/lifearchivist/actions/workflows/lint.yml/badge.svg)](https://github.com/ParthivNaresh/lifearchivist/actions/workflows/lint.yml)
[![Documentation](https://github.com/ParthivNaresh/lifearchivist/actions/workflows/docs.yml/badge.svg)](https://github.com/ParthivNaresh/lifearchivist/actions/workflows/docs.yml)
[![SonarCloud Analysis](https://github.com/ParthivNaresh/lifearchivist/actions/workflows/sonarqube.yml/badge.svg)](https://github.com/ParthivNaresh/lifearchivist/actions/workflows/sonarqube.yml)
[![codecov](https://codecov.io/gh/ParthivNaresh/lifearchivist/branch/main/graph/badge.svg)](https://codecov.io/gh/ParthivNaresh/lifearchivist)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=ParthivNaresh_lifearchivist&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=ParthivNaresh_lifearchivist)

### Code Standards

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)

### Project Info

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/ParthivNaresh/lifearchivist/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

## 🚀 Quick Links

- **Documentation**: [docs.lifearchivist.dev](https://docs.lifearchivist.dev)
- **Repository**: [github.com/ParthivNaresh/lifearchivist](https://github.com/ParthivNaresh/lifearchivist)
- **Issues**: [Report a bug or request a feature](https://github.com/ParthivNaresh/lifearchivist/issues)

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
git clone https://github.com/ParthivNaresh/lifearchivist.git
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
- GitHub: [@ParthivNaresh](https://github.com/ParthivNaresh)
- Email: parthivnaresh@gmail.com

---

<div align="center">

Built with modern Python tooling and best practices for local-first, privacy-preserving personal knowledge management.

</div>
