.. Life Archivist documentation master file

Life Archivist Documentation
=============================

Welcome to Life Archivist's documentation!

Life Archivist is a personal knowledge management system that helps you organize, search, and interact with your digital life archive.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   quickstart
   configuration

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   usage/overview
   usage/file-management
   usage/search
   usage/ai-features

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/modules
   api/tools
   api/storage
   api/server

.. toctree::
   :maxdepth: 2
   :caption: Development

   development/setup
   development/architecture
   development/contributing
   development/testing

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Features
--------

* **Content-Addressed Storage**: Automatic file deduplication using SHA256 hashing
* **AI-Powered Search**: Semantic search using embeddings and LlamaIndex
* **Local-First**: All data stays on your machine with Ollama for LLM inference
* **Multi-Format Support**: Extract text from PDFs, documents, images, and more
* **Real-Time Processing**: WebSocket-based progress tracking for file imports
* **RESTful API**: Full-featured API for integration with other tools

Quick Links
-----------

* `GitHub Repository <https://github.com/yourusername/lifearchivist>`_
* `Issue Tracker <https://github.com/yourusername/lifearchivist/issues>`_
* `API Documentation </api/modules.html>`_