"""
Celery tasks for AI drafting operations to prevent blocking HTTP requests.
All AI operations should be async to handle 100-200 concurrent users.
"""
from celery import shared_task
import os
import datetime
import logging
import traceback
from bson import ObjectId
from core.init_clients import get_mongo_client, get_mongo_db
from core.llm_client import chat_complete
from django.core.cache import cache
from ai_draft.drafting.classify import DraftContext, classify
from ai_draft.routes.creatupdateAIdrafts import (
    CreateupdatefetchAIdrafts,
    draft_cache_key,
)

logger = logging.getLogger('django')

def _get_collection():
    """Get MongoDB collection for AI drafts"""
    mongo = get_mongo_client()
    if not mongo:
        return None
    return get_mongo_db()['aidrafts_complete_data']


#: Two retries, not three. Every attempt is a full Sonnet-5 generation of an
#: 8-10k-token instrument (44-177s measured, plus its own correction turn), so
#: an unfixable request would otherwise burn four of them and minutes of worker
#: time before settling on the failure the user can already see.
@shared_task(bind=True, max_retries=2)
def generate_draft_async(self, session_id, user_query, location, language, document_type=None,
                         user_id=None):
    """
    Asynchronously generate a draft, by delegating to the synchronous engine.

    This task used to carry its own copy of the prompt, the parser and the
    encryption helper — the worst of the four prompt copies, having never even
    received the 2023-codes paragraph the other three had. Everything now runs
    through `CreateupdatefetchAIdrafts.generate_draft`, so enabling Celery
    cannot revert the playbooks, the repair ladder, the validator's correction
    turn, or the advisory schema. The task owns only what is genuinely
    Celery's: retry policy and cache invalidation.
    """
    logger.info(f"[ASYNC_DRAFT] Generating draft for session_id: {session_id}")

    try:
        collection = _get_collection()
        if not collection:
            raise Exception("MongoDB connection failed")

        # Prefer the context the session was created with, so the worker and the
        # request path cannot disagree about the document type.
        session = collection.find_one({'_id': ObjectId(session_id)}) or {}
        ctx = DraftContext.from_dict(session.get('draft_context'))
        if ctx is None:
            ctx = classify(user_query, document_type)

        collection.update_one(
            {'_id': ObjectId(session_id)},
            {'$set': {'status': 'generating',
                      'last_updated_on': datetime.datetime.now(datetime.timezone.utc)}}
        )

        obj = CreateupdatefetchAIdrafts(user_id or session.get('user_id'))
        # generate_draft writes sections, advisories, validation metadata and
        # the terminal status itself.
        obj.generate_draft(session_id, user_query, location, language, ctx=ctx)

        # The request path created the "Untitled …" saved_draft row while the
        # sections were still empty, so that the draft appears in the user's
        # list immediately. Fill in its snapshot now that they exist.
        obj.backfill_initial_saved_draft(session_id)

        # The read path caches only completed drafts, but a stale entry from
        # before this run must not survive it.
        cache.delete(draft_cache_key(session_id))

        refreshed = collection.find_one({'_id': ObjectId(session_id)}) or {}
        status = refreshed.get('status')
        count = len(refreshed.get('draft_sections') or [])
        if status != 'completed':
            # `generate_draft` has already recorded status='failed', so a retry
            # that also fails leaves the session in a state the UI can explain.
            raise Exception(f'draft generation did not complete (status={status})')

        logger.info(f"[ASYNC_DRAFT] Draft generation completed for session_id: {session_id}")
        return {'success': True, 'session_id': str(session_id), 'sections_count': count}

    except Exception as e:
        logger.error(f"[ASYNC_DRAFT] Error: {traceback.format_exc()}")
        collection = _get_collection()
        if collection:
            collection.update_one(
                {'_id': ObjectId(session_id)},
                {'$set': {'status': 'failed', 'error': str(e),
                          'last_updated_on': datetime.datetime.now(datetime.timezone.utc)}}
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


# `_parse_draft_into_sections` used to live here as a third copy of the parser.
# It has been deleted: the single parser is `drafting.draft_validator`, reached
# through `CreateupdatefetchAIdrafts.generate_draft`.
