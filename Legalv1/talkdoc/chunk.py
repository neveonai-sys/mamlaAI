import re
from typing import List, Dict

def split_into_chunks(text: str, max_tokens: int = 700, overlap: int = 80) -> List[Dict]:
    """
    Simple token-approx chunker (by words). In prod you can swap with tiktoken count.
    """
    words = re.findall(r'\S+\s*', text)
    chunks = []
    i = 0
    while i < len(words):
        block = ''.join(words[i:i+max_tokens])
        chunks.append({"text": block})
        i += (max_tokens - overlap)
    return chunks
