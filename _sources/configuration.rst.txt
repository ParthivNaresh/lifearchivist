Configuration
=============

Life Archivist can be configured through environment variables and configuration files.

Environment Variables
---------------------

Create a `.env` file in the project root:

.. code-block:: bash

   cp .env.example .env

Key Configuration Options
-------------------------

Storage Settings
~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Storage paths
   LIFEARCH_HOME=/path/to/storage
   LIFEARCH_VAULT_PATH=/path/to/vault
   
   # Database
   LIFEARCH_DATABASE_URL=sqlite:///lifearchivist.db

Model Settings
~~~~~~~~~~~~~~

.. code-block:: bash

   # LLM Configuration
   LIFEARCH_LLM_MODEL=llama3.2:3b
   LIFEARCH_EMBEDDING_MODEL=all-MiniLM-L6-v2
   
   # Ollama settings
   LIFEARCH_OLLAMA_URL=http://localhost:11434

Service URLs
~~~~~~~~~~~~

.. code-block:: bash

   # External services
   LIFEARCH_REDIS_URL=redis://localhost:6379
   LIFEARCH_QDRANT_URL=http://localhost:6333

API Settings
~~~~~~~~~~~~

.. code-block:: bash

   # Server configuration
   LIFEARCH_HOST=localhost
   LIFEARCH_PORT=8000
   LIFEARCH_CORS_ORIGINS=["http://localhost:3000"]

Feature Flags
~~~~~~~~~~~~~

.. code-block:: bash

   # Enable/disable features
   LIFEARCH_ENABLE_UI=true
   LIFEARCH_ENABLE_AGENTS=true
   LIFEARCH_ENABLE_WEBSOCKETS=true

Advanced Configuration
----------------------

Logging
~~~~~~~

Configure logging levels and output:

.. code-block:: bash

   LIFEARCH_LOG_LEVEL=INFO
   LIFEARCH_LOG_FORMAT=json
   LIFEARCH_LOG_FILE=/var/log/lifearchivist.log

Performance Tuning
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Worker settings
   LIFEARCH_WORKER_COUNT=4
   LIFEARCH_MAX_UPLOAD_SIZE=100MB
   
   # Cache settings
   LIFEARCH_CACHE_TTL=3600
   LIFEARCH_CACHE_SIZE=1000

Security
~~~~~~~~

.. code-block:: bash

   # Security settings
   LIFEARCH_SECRET_KEY=your-secret-key
   LIFEARCH_ENABLE_AUTH=false
   LIFEARCH_JWT_EXPIRY=86400

Configuration File
------------------

You can also use a YAML configuration file:

.. code-block:: yaml

   # config.yaml
   storage:
     home: /path/to/storage
     vault: /path/to/vault
   
   models:
     llm: llama3.2:3b
     embedding: all-MiniLM-L6-v2
   
   services:
     ollama_url: http://localhost:11434
     redis_url: redis://localhost:6379

Load with:

.. code-block:: bash

   LIFEARCH_CONFIG_FILE=config.yaml lifearchivist server

Validation
----------

Validate your configuration:

.. code-block:: bash

   lifearchivist config validate
   lifearchivist config show