"""
Celery tasks for AI drafting operations to prevent blocking HTTP requests.
All AI operations should be async to handle 100-200 concurrent users.
"""
from celery import shared_task
import os
import json
import datetime
import logging
import traceback
from bson import ObjectId
from core.init_clients import get_mongo_client, get_mongo_db
from core.llm_client import chat_complete
from django.core.cache import cache
from users.routes.encryption import encrypt_field

logger = logging.getLogger('django')

def _get_collection():
    """Get MongoDB collection for AI drafts"""
    mongo = get_mongo_client()
    if not mongo:
        return None
    return get_mongo_db()['aidrafts_complete_data']


@shared_task(bind=True, max_retries=3)
def generate_draft_async(self, session_id, user_query, location, language):
    """
    Asynchronously generate draft using AI.
    This prevents blocking the HTTP request for 100-200 concurrent users.
    """
    logger.info(f"[ASYNC_DRAFT] Generating draft for session_id: {session_id}")
    
    try:
        collection = _get_collection()
        if not collection:
            raise Exception("MongoDB connection failed")
        
        # Build location string
        location_string = ''
        if location:
            if 'court' in location and 'district' in location and 'state' in location:
                location_string = f"""for court "{location.get('court')}" in the district "{location.get('district')}" of state "{location.get('state')}" """
            elif 'district' in location and 'state' in location:
                location_string = f"""in the district "{location.get('district')}" of state "{location.get('state')}" """
            elif 'state' in location:
                location_string = f"""for the state "{location.get('state')}" """

        # Construct optimized prompt
        prompt = f"""You are a legal expert specializing in drafting legal documents as per Indian legal standards and the Indian constitution.

A user has requested: "{user_query}" {location_string}.

Please generate a comprehensive draft **in {language}**, adhering to all relevant laws and regulations specific to this location.

**Formatting Instructions:**

- Output the draft in **JSON** format.
- The JSON should be an array of sections.
- Each section should be an object with two properties:
  - `"section_name"`: The name of the section.
  - `"content"`: The content of the section, including placeholders where specific user information is required (like names, dates, addresses) in ALL CAPS (e.g., `[YOUR FULL NAME]`, `[DATE OF BIRTH]`).
- Each section content should be at least 70-80 words where possible, comprehensive and accurate to Indian law.
- Return ONLY the JSON array. Do not include any explanatory text, markdown code fences, or commentary before or after the JSON.

Example:

[
{{
    "section_name": "TITLE OF THE SUIT",
    "content": "Content of section I..."
}},
{{
    "section_name": "PRELIMINARY STATEMENT",
    "content": "Content of section II..."
}}
]"""

        # Update status to processing
        collection.update_one(
            {'_id': ObjectId(session_id)},
            {'$set': {'status': 'generating', 'updated_at': datetime.datetime.utcnow()}}
        )

        # Call LLM via centralized client (async Celery task — won't block HTTP requests)
        draft_content = chat_complete(
            messages=[{'role': 'user', 'content': prompt}],
            app_scenario='ai_draft:generate',
            temperature=0.3,  # Low temp → reliable JSON structure
            max_tokens=4000,
        )
        logger.info(f"[ASYNC_DRAFT] Received draft content from ChatGPT")

        # Parse draft into sections
        draft_sections = _parse_draft_into_sections(draft_content)

        if not draft_sections:
            raise Exception("Failed to parse draft sections")

        # Update session with draft sections (encrypted at rest — Privacy
        # Policy Section 7 / Sensitive Personal Data: "Case details, legal
        # documents"). Cache below intentionally keeps the plaintext version
        # for fast in-process retrieval, matching cache.set()'s short TTL.
        encrypted_sections = [
            {**s, 'content': encrypt_field(s['content'])} if 'content' in s else s
            for s in draft_sections
        ]
        collection.update_one(
            {'_id': ObjectId(session_id)},
            {'$set': {
                'draft_sections': encrypted_sections,
                'original_draft': encrypted_sections,
                'status': 'completed',
                'last_updated_on': datetime.datetime.utcnow()
            }}
        )

        # Cache the result for quick retrieval
        cache_key = f"draft_sections:{session_id}"
        cache.set(cache_key, draft_sections, timeout=3600)  # 1 hour

        logger.info(f"[ASYNC_DRAFT] Draft generation completed for session_id: {session_id}")
        return {'success': True, 'session_id': str(session_id), 'sections_count': len(draft_sections)}

    except Exception as e:
        logger.error(f"[ASYNC_DRAFT] Error: {traceback.format_exc()}")
        collection = _get_collection()
        if collection:
            collection.update_one(
                {'_id': ObjectId(session_id)},
                {'$set': {'status': 'failed', 'error': str(e), 'updated_at': datetime.datetime.utcnow()}}
            )
        raise self.retry(exc=e, countdown=30)  # Retry after 30 seconds


@shared_task(bind=True, max_retries=3)
def update_section_with_ai_async(self, session_id, section_id, section_name, current_content, suggestion):
    """
    Asynchronously update a section using AI suggestions.
    """
    logger.info(f"[ASYNC_UPDATE] Updating section {section_id} for session {session_id}")
    
    try:
        prompt = f"""You previously drafted the following section titled "{section_name}":

{current_content}

The user has the following suggestions or changes:

{suggestion}

Please provide an updated version of this section, incorporating the user's suggestions, and ensure it complies with Indian legal standards.

Return ONLY the updated section content. Do not include any headings, labels, preamble, or extra commentary."""

        updated_content = chat_complete(
            messages=[{'role': 'user', 'content': prompt}],
            app_scenario='ai_draft:update_section',
            temperature=0.4,
            max_tokens=2000,
        )
        
        # Cache the AI response
        cache_key = f"ai_update:{session_id}:{section_id}:{hash(suggestion)}"
        cache.set(cache_key, updated_content, timeout=3600)
        
        logger.info(f"[ASYNC_UPDATE] Section update completed")
        return {'success': True, 'updated_content': updated_content}

    except Exception as e:
        logger.error(f"[ASYNC_UPDATE] Error: {traceback.format_exc()}")
        raise self.retry(exc=e, countdown=30)


def _parse_draft_into_sections(draft_content):
    """Parse AI response into structured sections"""
    logger.info("[PARSE] Parsing draft content into sections")

    # Remove Markdown code block syntax if present
    if draft_content.startswith("```") and draft_content.endswith("```"):
        draft_content = '\n'.join(draft_content.split('\n')[1:-1])

    if not draft_content.strip():
        logger.error("[PARSE] draft_content is empty")
        return []

    try:
        sections = json.loads(draft_content)

        # Validate and add section IDs
        for section in sections:
            if not isinstance(section, dict) or 'section_name' not in section or 'content' not in section:
                logger.error("[PARSE] Invalid section format")
                return []
            section['section_id'] = str(ObjectId())

        logger.info(f"[PARSE] Successfully parsed {len(sections)} sections")
        return sections

    except json.JSONDecodeError as e:
        logger.error(f"[PARSE] JSONDecodeError: {str(e)}")
        logger.error(f"[PARSE] Content: {draft_content[:500]}")
        return []
    except Exception as e:
        logger.error(f"[PARSE] Exception: {traceback.format_exc()}")
        return []
