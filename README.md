Research OS - v0.1

Research OS is a hybrid knowledge substrate and retrieval system designed to index, search, and semantically expand structured personal knowledge bases (such as Logseq vaults). By combining dense vector embeddings for semantic retrieval with a graph database for contextual and structural traversal, Research OS bridges the gap between neural text similarity and graph-based knowledge networks.

Overview
What It Does

Research OS parses Markdown knowledge vaults containing bullet-point hierarchies, extracts inline properties (key:: value), wiki links ([[link]]), and hashtags (#tag), and indexes these elements concurrently across two database systems:

Qdrant: Stores vector embeddings of block content to support semantic search.
Neo4j: Stores block structure, block-to-block hierarchies, page ownership, wiki-link edges, and hashtag associations.

When queried, the system performs a hybrid search: it first finds top-matching blocks via vector similarity, then expands the graph context in Neo4j to retrieve connected concepts and tags.

Key Technical Characteristics
Hybrid Retrieval Strategy: Integrates dense vector embeddings (all-MiniLM-L6-v2) with Neo4j Cypher pattern matching.
Hierarchical Bullet-Block Parsing: Handles Logseq-style bullet indentation levels, mapping block parent-child relationships.
Real-Time Workspace Synchronization: Supports both batch synchronization and real-time filesystem monitoring via watchdog.
Containerized Data Infrastructure: Pre-configured using Docker Compose for simple local deployment.
Features
Logseq-Compatible Parsing: Extracts Markdown headers, indented bullet points, inline properties, [[Wiki Links]], and #tags.
Dual Indexing Engine:
Vectorizes text blocks into 384-dimensional embeddings stored in Qdrant.
Construct graph structures (Pages, Blocks, Tags, Links) with Neo4j.
Incremental & Workspace Sync: Synchronizes entire vaults or monitors file modification events in real time.
Hybrid Query Pipeline: Combines semantic similarity scores with graph-traversal context expansion in a unified CLI.
Architecture

Research OS reads Markdown files from a target directory (./vault), parses blocks and structural metadata, and populates both Neo4j and Qdrant. Queries traverse the vector index first and then expand related graph context.

flowchart TD
    subgraph Storage ["Vault Storage"]
        Vault["/vault Directory\n(pages/ & journals/)"]
    end

    subgraph Core ["Research OS Core Engine"]
        Parser["Parser (src/parser.py)\n- Parses Logseq Bullet Hierarchies\n- Extracts Properties, Links, Tags"]
        Sync["Sync Manager (src/sync.py)\n- Full Sync & Watchdog File Observer"]
    end

    subgraph Data ["Databases (Docker)"]
        Qdrant[("Qdrant Vector DB\n(Port 6333 / 6343)")]
        Neo4j[("Neo4j Graph DB\n(Port 7474 / 7687)")]
    end

    subgraph Query ["Retrieval Interface"]
        CLI["Query CLI (query.py)\n1. Vector Search (Qdrant)\n2. Graph Context Expansion (Neo4j)"]
    end

    Vault -->|Read Files / Watch Changes| Sync
    Sync --> Parser
    Parser -->|Upsert Document Blocks| VectorClient["VectorClient (src/vector_client.py)"]
    Parser -->|Sync Graph Relationships| GraphClient["GraphClient (src/graph_client.py)"]
    VectorClient -->|Vector Embeddings| Qdrant
    GraphClient -->|Nodes & Edges| Neo4j
    CLI -->|Semantic Query| Qdrant
    CLI -->|Cypher Context Lookup| Neo4j

Technology Stack
Technology	Purpose
Python	Core application language
Neo4j	Graph database for page, block hierarchy, wiki links, and tag networks
Qdrant	Vector database for storing and searching dense vector embeddings
SentenceTransformers	Embedding generation model (all-MiniLM-L6-v2)
Watchdog	File system monitoring service for real-time vault synchronization
Docker Compose	Orchestration of Neo4j and Qdrant containerized infrastructure
HTTPX	HTTP client for vector REST API operations
TQDM	Progress bar display during workspace indexing
Project Structure
Research-OS-v0.1/
├── src/
│   ├── __init__.py
│   ├── graph_client.py     # Neo4j graph operations and Cypher queries
│   ├── parser.py           # Logseq markdown bullet/block hierarchy parser
│   ├── sync.py             # Full vault indexing and watchdog file monitoring
│   └── vector_client.py    # Qdrant client integration and embedding generation
├── vault/
│   ├── journals/           # Logseq journal entry storage
│   └── pages/              # Logseq note pages storage
├── docker-compose.yml      # Service orchestration for Neo4j and Qdrant
├── query.py                # CLI query execution interface
└── requirements.txt        # Python package dependencies

Requirements
Python: ^3.8 (Recommended Python 3.10+)
Docker & Docker Compose: For hosting Neo4j and Qdrant instances
Hardware/Memory: Standard CPU (SentenceTransformer model runs locally)
Installation

Clone the Repository:

git clone <repository-url>
cd Research-OS-v0.1


Set Up a Virtual Environment:

python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate


Install Dependencies:

pip install -r requirements.txt


Start Database Containers:

docker-compose up -d

Configuration

Database credentials and service ports are configured by default in docker-compose.yml and client initializations:

Environment Variable / Config	Default Value	Purpose
NEO4J_AUTH	neo4j/researchospassword	Neo4j database authentication credentials
Neo4j Bolt URI	bolt://localhost:7687	Connection string for Neo4j Bolt protocol
Neo4j HTTP Port	7474	Neo4j Web Console / HTTP API port
Qdrant HTTP Port	6333	Qdrant REST API port
Qdrant gRPC Port	6343	Qdrant gRPC API port
Vector Model	all-MiniLM-L6-v2	SentenceTransformer model used for embeddings
Running the Project
1. Synchronize Knowledge Base

Before querying, populate the databases with your vault contents. Place markdown notes in ./vault/pages/ or ./vault/journals/.

Run a One-Time Workspace Indexing:

python -m src.sync full


Start Real-Time Vault Monitoring:

python -m src.sync watch

2. Querying the Knowledge Base

Execute queries via the CLI:

python query.py "your search phrase here"


If no argument is passed, query.py defaults to running a sample test query.

How It Works
Vault Ingestion: src/parser.py reads Markdown files. It builds hierarchical Block objects based on indentation levels and extracts links ([[...]]), tags (#tag), and key-value properties (key:: value).
Graph Indexing: src/graph_client.py writes nodes (Page, Block, Tag) and relationships (HAS_ROOT_BLOCK, CHILD_OF, LINKS_TO, HAS_TAG) into Neo4j.
Vector Indexing: src/vector_client.py computes dense embeddings for every non-empty block using SentenceTransformer('all-MiniLM-L6-v2') and stores them in Qdrant along with payload metadata.
Hybrid Search Execution:
query.py queries Qdrant to retrieve top matching text blocks based on cosine similarity.
It takes the primary matched page context and executes a Neo4j Cypher query to retrieve associated [[Wiki Links]] and #tags tied to those blocks.
Core Components
src/parser.py: Handles parsing of markdown files, maintaining parent-child relationships across nested list structures, and extracting block-level attributes.
src/graph_client.py: Manages the Neo4j connection pool, sets up uniqueness constraints on block and page IDs, and handles batch database operations.
src/vector_client.py: Manages Qdrant vector collections, formats payloads, converts string IDs to 64-bit integer hashes, and performs vector queries via HTTP.
src/sync.py: CLI handler that coordinates file traversal across vault directories and manages file watcher events using watchdog.
query.py: Interface for combined semantic search and graph context retrieval.
Database Schema & Graph Model
Neo4j Graph Model

Node Labels:

:Page {name: STRING}
:Block {id: STRING, text: STRING, page: STRING, properties: JSON_STRING}
:Tag {name: STRING}

Relationships:

(:Page)-[:HAS_ROOT_BLOCK]->(:Block)
(:Block)-[:CHILD_OF]->(:Block)
(:Block)-[:LINKS_TO]->(:Page)
(:Block)-[:HAS_TAG]->(:Tag)
Qdrant Vector Payload
Collection Name: research_blocks
Vector Dimension: 384 (Distance Metric: Cosine)
Payload Schema:
{
  "block_id": "string",
  "page_name": "string",
  "text": "string",
  "properties": {}
}

Docker Configuration

The application relies on Docker Compose to manage persistent database services:

version: '3.8'

services:
  neo4j:
    image: neo4j:5.12.0-community
    container_name: researchos_graph
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/researchospassword
    volumes:
      - neo4j_data:/data

  qdrant:
    image: qdrant/qdrant:v1.7.0
    container_name: researchos_vector
    ports:
      - "6333:6333"
      - "6343:6343"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  neo4j_data:
  qdrant_data:


To reset container state and clear stored database data:

docker-compose down -v
docker-compose up -d

Security Considerations
Default Credentials: Default credentials (neo4j/researchospassword) are hardcoded in docker-compose.yml, graph_client.py, and query.py. Override these defaults before deploying to external or production environments.
Network Interfaces: Ensure Neo4j (7474, 7687) and Qdrant (6333, 6343) ports are bound to 127.0.0.1 or restricted behind a firewall if deployed on a shared network.
Troubleshooting

Database Connection Failure:

Verify that Docker containers are running using docker ps.
Check container status: docker-compose logs neo4j or docker-compose logs qdrant.

No Documents Detected During Sync:

Ensure Markdown files are placed inside ./vault/pages/ or ./vault/journals/.

Missing Graph Insights on Query:

Ensure a full synchronization (python -m src.sync full) has been completed after adding new files.
License

License