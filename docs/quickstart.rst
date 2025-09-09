Quick Start
===========

This guide will help you get started with Life Archivist quickly.

Prerequisites
-------------

Make sure you have completed the :doc:`installation` guide first.

Starting Life Archivist
-----------------------

The fastest way to start Life Archivist is using the provided just commands:

.. code-block:: bash

   # Start everything (services + server + UI)
   just fullstack

This will:

1. Start Docker services (Ollama, Redis, Qdrant)
2. Start the backend API server on http://localhost:8000
3. Launch the Electron desktop application

First Time Setup
----------------

On first run, Life Archivist will:

1. Initialize the storage directories
2. Create the database schema
3. Download required AI models
4. Set up the vector index

Basic Usage
-----------

Importing Files
~~~~~~~~~~~~~~~

You can import files through:

1. **Web UI**: Drag and drop files or use the upload button
2. **API**: POST to `/api/files/upload`
3. **CLI**: `lifearchivist import <file>`

Searching
~~~~~~~~~

Life Archivist provides multiple search modes:

- **Semantic Search**: Find documents by meaning
- **Keyword Search**: Traditional text matching
- **Hybrid Search**: Combines both approaches

Asking Questions
~~~~~~~~~~~~~~~~

Use the Q&A feature to ask questions about your documents:

.. code-block:: python

   # Example API call
   POST /api/query
   {
     "question": "What are the main topics in my documents?",
     "similarity_top_k": 5
   }

Next Steps
----------

- Explore the :doc:`usage/overview` for detailed features
- Configure settings in :doc:`configuration`
- Learn about the :doc:`api/modules` for integration