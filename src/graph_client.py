import json
from neo4j import GraphDatabase

class GraphClient:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="researchospassword"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self._setup_constraints()

    def close(self):
        self.driver.close()

    def _setup_constraints(self):
        """Ensure unique indexes exist for performance."""
        queries = [
            "CREATE CONSTRAINT unique_page IF NOT EXISTS FOR (p:Page) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT unique_block IF NOT EXISTS FOR (b:Block) REQUIRE b.id IS UNIQUE"
        ]
        with self.driver.session() as session:
            for query in queries:
                try:
                    session.run(query)
                except Exception:
                    pass 

    def sync_document(self, doc):
        """Syncs parsed Document structural and link data in batches."""
        with self.driver.session() as session:
            session.execute_write(self._sync_document_tx, doc)

    @staticmethod
    def _sync_document_tx(tx, doc):
        # 1. Create or match page node
        tx.run("MERGE (p:Page {name: $name})", name=doc.title)

        # Flatten blocks to write relationships
        from .parser import _flatten
        flat_blocks = list(_flatten(doc.blocks))

        if not flat_blocks:
            return

        # 2. Write all Block Nodes
        block_batch = []
        for b in flat_blocks:
            if b.content.strip():
                # FIX: Convert the properties dictionary into a JSON string for Neo4j compatibility
                properties_json = json.dumps(b.properties)
                
                block_batch.append({
                    "id": b.id,
                    "text": b.content,
                    "page": b.page,
                    "properties": properties_json
                })

        tx.run("""
            UNWIND $batch as row
            MERGE (b:Block {id: row.id})
            SET b.text = row.text, b.page = row.page, b.properties = row.properties
        """, batch=block_batch)

        # 3. Create Hierarchical Tree & Semantic connections
        for b in flat_blocks:
            if not b.content.strip():
                continue

            # Link Root Blocks to Page Node
            if b.level == 0:
                tx.run("""
                    MATCH (p:Page {name: $page})
                    MATCH (b:Block {id: $block_id})
                    MERGE (p)-[:HAS_ROOT_BLOCK]->(b)
                """, page=doc.title, block_id=b.id)

            # Link Nesting Children
            for child in b.children:
                if child.content.strip():
                    tx.run("""
                        MATCH (parent:Block {id: $parent_id})
                        MATCH (child:Block {id: $child_id})
                        MERGE (child)-[:CHILD_OF]->(parent)
                    """, parent_id=b.id, child_id=child.id)

            # Link semantic references [[links]]
            for link in b.links:
                tx.run("MERGE (target:Page {name: $target_name})", target_name=link)
                tx.run("""
                    MATCH (b:Block {id: $block_id})
                    MATCH (target:Page {name: $target_name})
                    MERGE (b)-[:LINKS_TO]->(target)
                """, block_id=b.id, target_name=link)

            # Link #tags
            for tag in b.tags:
                tx.run("MERGE (t:Tag {name: $tag_name})", tag_name=tag)
                tx.run("""
                    MATCH (b:Block {id: $block_id})
                    MATCH (t:Tag {name: $tag_name})
                    MERGE (b)-[:HAS_TAG]->(t)
                """, block_id=b.id, tag_name=tag)