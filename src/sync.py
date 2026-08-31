import os
import sys
import time
from pathlib import Path
from tqdm import tqdm
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .parser import parse_file
from .graph_client import GraphClient
from .vector_client import VectorClient

VAULT_DIR = Path("./vault")

class LogseqSyncHandler(FileSystemEventHandler):
    def __init__(self, graph_client, vector_client):
        self.graph = graph_client
        self.vector = vector_client

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".md"):
            self._sync_file(Path(event.src_path))

    def _sync_file(self, filepath: Path):
        try:
            # Let Logseq finish flushing file adjustments safely
            time.sleep(0.5)
            doc = parse_file(filepath)
            print(f"\n⚡ Auto-Syncing: [[{doc.title}]]")
            self.graph.sync_document(doc)
            self.vector.upsert_document(doc)
            print("🚀 Systems synced successfully.")
        except Exception as e:
            print(f"❌ Auto-sync failed for {filepath.name}: {e}")

def run_full_sync(graph, vector):
    print("🔄 Running a Full Workspace Sync...")
    
    pages_dir = VAULT_DIR / "pages"
    journals_dir = VAULT_DIR / "journals"
    
    all_files = []
    for folder in [pages_dir, journals_dir]:
        if folder.exists():
            for file in folder.rglob("*.md"):
                all_files.append(file)
                
    if not all_files:
        print("⚠️ No Logseq documents detected! Is your markdown database placed inside the './vault/' directory?")
        return

    for file_path in tqdm(all_files, desc="Indexing Knowledge Core Base"):
        try:
            doc = parse_file(file_path)
            graph.sync_document(doc)
            vector.upsert_document(doc)
        except Exception as e:
            print(f"\n❌ Error syncing {file_path.name}: {e}")

    print("✨ Core Index Updated. Ready to Query.")

def main():
    if not VAULT_DIR.exists():
         os.makedirs(VAULT_DIR / "pages", exist_ok=True)
         os.makedirs(VAULT_DIR / "journals", exist_ok=True)

    # Initialize Connections
    graph = GraphClient()
    vector = VectorClient()

    mode = sys.argv[1] if len(sys.argv) > 1 else "full"

    if mode == "full":
        run_full_sync(graph, vector)
        graph.close()
    elif mode == "watch":
        run_full_sync(graph, vector)
        print(f"\n👁️ Monitoring '{VAULT_DIR}' for active modifications. Press Ctrl+C to stop.")
        
        event_handler = LogseqSyncHandler(graph, vector)
        observer = Observer()
        observer.schedule(event_handler, path=str(VAULT_DIR), recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
        graph.close()
    else:
        print("❌ Unknown execution argument. Run with 'full' or 'watch'.")

if __name__ == "__main__":
    main()