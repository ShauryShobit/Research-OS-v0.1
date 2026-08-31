import sys
from src.vector_client import VectorClient
from neo4j import GraphDatabase

def test_query(query_str):
    print(f"\n🔍 Querying Knowledge Substrate for: '{query_str}'\n")
    
    # 1. Vector Search
    vector = VectorClient()
    semantic_results = vector.search(query_str, limit=3)
    
    print("--- 🧠 SEMANTIC SEARCH RESULTS (Qdrant) ---")
    top_page = None
    matched_texts = []
    
    for res in semantic_results:
        payload = getattr(res, 'payload', None) or res.get('payload', {})
        score = getattr(res, 'score', 0.0) or res.get('score', 0.0)
        
        page_name = payload.get('page_name', 'Unknown Page')
        text = payload.get('text', 'No content text found.')
        
        if not top_page:
            top_page = page_name
        matched_texts.append(text)
            
        print(f"• [{page_name}] -> {text} (Score: {score:.3f})")

    # 2. Advanced Graph Context Expansion
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "researchospassword"))
    
    if top_page and top_page != 'Unknown Page':
        print(f"\n--- 🕸️ CONNECTED KNOWLEDGE SUBSTRATE (Neo4j) ---")
        
        # Cypher query that finds explicit pages and tags mentioned near our target text
        graph_query = """
        MATCH (b:Block {page: $page_name})
        WHERE any(term in $matched_texts WHERE b.text CONTAINS term)
        OPTIONAL MATCH (b)-[:LINKS_TO]->(p:Page)
        OPTIONAL MATCH (b)-[:HAS_TAG]->(t:Tag)
        RETURN collect(DISTINCT p.name) as links, collect(DISTINCT t.name) as tags
        """
        
        with driver.session() as session:
            result = session.run(graph_query, page_name=top_page, matched_texts=matched_texts)
            record = result.single()
            
            if record:
                links = record["links"]
                tags = record["tags"]
                
                if links:
                    print("🔗 Related Concepts in Context:")
                    for link in links:
                        print(f"  • [[{link}]]")
                if tags:
                    print("\n🏷️ Contextual Hashtags:")
                    for tag in tags:
                        print(f"  • #{tag}")
            else:
                print("No deep graph insights for this specific slice.")
                
    driver.close()

if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "where is the world cup final match"
    test_query(q)