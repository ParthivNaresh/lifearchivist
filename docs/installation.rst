Installation
============

This guide will help you install Life Archivist on your system.

Prerequisites
-------------

Before installing Life Archivist, ensure you have the following:

* Python 3.11 or higher
* Poetry (for Python dependency management)
* Docker and Docker Compose
* Node.js 18+ and npm (for the desktop app)
* Git

System Dependencies
-------------------

macOS
~~~~~

.. code-block:: bash

   # Install Homebrew if not already installed
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

   # Install system dependencies
   brew install python@3.11 poetry docker node git

Linux
~~~~~

.. code-block:: bash

   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3.11 python3-pip docker.io docker-compose nodejs npm git
   
   # Install Poetry
   curl -sSL https://install.python-poetry.org | python3 -

Installation Steps
------------------

1. Clone the Repository
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   git clone https://github.com/yourusername/lifearchivist.git
   cd lifearchivist

2. Install Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Install all dependencies (Python + Node.js)
   just install

   # Or manually:
   poetry install
   cd desktop && npm install

3. Start Services
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Start Docker services (Ollama, Redis, Qdrant)
   just services

   # Initialize Ollama models
   just init-models

4. Verify Installation
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Check all systems
   just verify

   # Check individual components
   just check-docker
   just health
   just test-cli

Quick Start
-----------

After installation, you can start Life Archivist with:

.. code-block:: bash

   # Start everything (services + server + UI)
   just fullstack

   # Or start components individually:
   just server     # Backend only
   just ui         # Frontend only
   just desktop    # Electron app

The application will be available at:

* Backend API: http://localhost:8000
* Web UI: http://localhost:3000
* API Documentation: http://localhost:8000/docs

Configuration
-------------

Create a `.env` file from the example:

.. code-block:: bash

   cp .env.example .env

Edit the `.env` file to configure:

* Storage paths
* Model settings
* API keys (if needed)
* Service URLs

See the :doc:`configuration` guide for detailed configuration options.

Troubleshooting
---------------

If you encounter issues:

1. Check Docker services are running:

   .. code-block:: bash

      just check-docker

2. Reset the environment:

   .. code-block:: bash

      just reset
      just setup

3. Check logs:

   .. code-block:: bash

      docker-compose logs -f

For more help, see the `GitHub Issues <https://github.com/yourusername/lifearchivist/issues>`_.