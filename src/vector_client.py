import hashlib
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

class VectorClient:
    def __init__(self, host="localhost", port=6333):
        self.client = QdrantClient(host=host, port=port)
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2') 
        self.collection_name = "research_blocks"
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
        except Exception as e:
            print(f"⚠️ Vector engine initialization warning: {e}. Check if Docker container is fully running.")

    def _convert_id_to_int(self, text_id: str) -> int:
        """Deterministic string ID to 64-bit int for Qdrant payload rules."""
        return int(hashlib.md5(text_id.encode()).hexdigest()[:15], 16)

    def upsert_document(self, doc):
        """Batches and vectorizes flat block items of a Document."""
        from .parser import _flatten
        flat_blocks = [b for b in _flatten(doc.blocks) if b.content.strip()]
        
        if not flat_blocks:
            return

        points = []
        texts = [b.content for b in flat_blocks]
        embeddings = self.encoder.encode(texts, batch_size=32, show_progress_bar=False).tolist()

        for idx, block in enumerate(flat_blocks):
            points.append(PointStruct(
                id=self._convert_id_to_int(block.id),
                vector=embeddings[idx],
                payload={
                    "block_id": block.id,
                    "page_name": doc.title,
                    "text": block.content,
                    "properties": block.properties
                }
            ))

        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)

    def search(self, query_text: str, limit: int = 3):
        """Perform a semantic vector search bypassing client limitations via raw REST API."""
        import httpx
        
        query_vector = self.encoder.encode(query_text).tolist()
        
        # Target the native Qdrant REST API endpoint directly
        url = f"http://localhost:6333/collections/{self.collection_name}/points/search"
        payload = {
            "vector": query_vector,
            "limit": limit,
            "with_payload": True
        }
        
        # Post directly to the local container
        with httpx.Client() as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            results = response.json().get("result", [])
            
        return results