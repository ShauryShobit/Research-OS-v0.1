import re
import uuid
import hashlib
from pathlib import Path

class Block:
    def __init__(self, content: str, level: int, page: str, properties=None):
        self.content = content.strip()
        self.level = level
        self.page = page
        self.properties = properties or {}
        self.children = []
        self.links = []
        self.tags = []
        
        # Extract metadata and clean text
        self._process_meta()
        
        # Generate a deterministic unique ID if Logseq hasn't assigned one
        if "id" not in self.properties:
            hash_input = f"{self.page}_{self.level}_{self.content}_{id(self)}"
            self.id = str(uuid.UUID(hashlib.md5(hash_input.encode()).hexdigest()))
        else:
            self.id = self.properties["id"]

    def _process_meta(self):
        # 1. Parse inline properties (key:: value) and strip them from content
        prop_matches = re.findall(r"(\b\w+)::\s*(.*)", self.content)
        for key, val in prop_matches:
            self.properties[key] = val.strip()
        self.content = re.sub(r"\b\w+::.*", "", self.content).strip()

        # 2. Extract [[Wiki Links]]
        self.links = [link.strip() for link in re.findall(r"\[\[(.*?)\]\]", self.content) if link.strip()]

        # 3. Extract #Tags (avoiding hash colors or markdown headers)
        self.tags = [tag.strip() for tag in re.findall(r"(?<!#)#(\w+)", self.content) if tag.strip()]


class Document:
    def __init__(self, title: str, blocks: list):
        self.title = title
        self.blocks = blocks  # List of top-level (level 0) root blocks


def _flatten(blocks):
    """Generator to recursively yield blocks in a flat sequence (used by graph/vector engines)."""
    for block in blocks:
        yield block
        yield from _flatten(block.children)


def parse_file(filepath: Path) -> Document:
    title = filepath.stem
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    root_blocks = []
    block_stack = []  # Track hierarchical layout stack

    for line in lines:
        # Match Logseq bullet layouts: optional spaces followed by "-"
        match = re.match(r"^(\s*)-\s(.*)", line)
        if not match:
            # Handle plain text properties at the very top of a document if any exist
            continue

        indent, raw_content = match.groups()
        # Logseq maps 2 spaces or 4 spaces consistently per nested tab layer
        level = (len(indent) + 1) // 2 if len(indent) > 0 else 0

        # Construct new individual block instance
        new_block = Block(content=raw_content, level=level, page=title)

        # Manage parent-child hierarchy assignments using the stack
        while len(block_stack) > level:
            block_stack.pop()

        if level == 0:
            root_blocks.append(new_block)
        else:
            if block_stack:
                block_stack[-1].children.append(new_block)

        block_stack.append(new_block)

    return Document(title=title, blocks=root_blocks)