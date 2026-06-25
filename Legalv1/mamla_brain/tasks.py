import hashlib
import re
from datetime import datetime
from pathlib import Path

from celery import shared_task

from talkdoc.tasks import embed_texts

from .retrieval import ensure_knowledge_index, knowledge_source_dir


def _section_chunks(text, source_name):
    normalized = (text or '').strip()
    if not normalized:
        return []

    chunks = []
    section_pattern = re.compile(r'^\s*(?:Section|SECTION)\s+[A-Za-z0-9.-]+', re.MULTILINE)
    matches = list(section_pattern.finditer(normalized))
    if matches:
        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
            chunk_text = normalized[start:end].strip()
            if chunk_text:
                chunks.append(chunk_text)
    else:
        paragraphs = [paragraph.strip() for paragraph in normalized.split('\n\n') if paragraph.strip()]
        current = []
        current_len = 0
        for paragraph in paragraphs:
            if current and current_len + len(paragraph) > 2200:
                chunks.append('\n\n'.join(current))
                current = [paragraph]
                current_len = len(paragraph)
            else:
                current.append(paragraph)
                current_len += len(paragraph)
        if current:
            chunks.append('\n\n'.join(current))

    results = []
    for index, chunk_text in enumerate(chunks, start=1):
        lines = [line.strip() for line in chunk_text.splitlines() if line.strip()]
        heading = lines[0] if lines else f'{source_name} chunk {index}'
        section_number = ''
        match = re.search(r'(Section|SECTION)\s+([A-Za-z0-9.-]+)', heading)
        if match:
            section_number = match.group(2)
        results.append({
            'chunk_id': hashlib.sha1(f'{source_name}:{index}:{heading}'.encode('utf-8')).hexdigest(),
            'title': heading,
            'text': chunk_text,
            'section_number': section_number,
            'section_title': heading,
        })
    return results


@shared_task
def ingest_knowledge_base(domain_key='legal', source_dir=None):
    source_root = knowledge_source_dir(domain_key) if source_dir is None else Path(source_dir)
    if not source_root.exists():
        return {'indexed': 0, 'domain_key': domain_key, 'source_dir': str(source_root), 'warning': 'source_dir_missing'}

    client, index_name = ensure_knowledge_index(domain_key)
    bulk_lines = []
    indexed = 0

    for source_file in sorted(source_root.glob('*.txt')):
        text = source_file.read_text(encoding='utf-8', errors='ignore')
        chunks = _section_chunks(text, source_file.stem)
        if not chunks:
            continue

        vectors = embed_texts([chunk['text'] for chunk in chunks])
        for chunk, vector in zip(chunks, vectors):
            document = {
                'chunk_id': chunk['chunk_id'],
                'domain_key': domain_key,
                'source_id': source_file.stem,
                'source_name': source_file.stem,
                'title': chunk['title'],
                'text': chunk['text'],
                'act': source_file.stem,
                'section_number': chunk['section_number'],
                'section_title': chunk['section_title'],
                'jurisdiction': 'india' if domain_key == 'legal' else domain_key,
                'source_url': '',
                'vector': vector,
                'created_at': datetime.utcnow().isoformat(),
            }
            bulk_lines.append({'index': {'_index': index_name, '_id': chunk['chunk_id']}})
            bulk_lines.append(document)
            indexed += 1

    if bulk_lines:
        client.bulk(body=bulk_lines, refresh=True)

    return {'indexed': indexed, 'domain_key': domain_key, 'source_dir': str(source_root), 'index_name': index_name}
