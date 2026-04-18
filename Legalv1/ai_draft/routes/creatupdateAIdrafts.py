from bson import ObjectId
from core.llm_client import chat_complete

import os
import math
from io import BytesIO
from docx import Document
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from core.init_clients import get_mongo_client
from pdfminer.high_level import extract_text as extract_text_from_pdf
import datetime
import json
import traceback
import logging
logger = logging.getLogger('django')

class CreateupdatefetchAIdrafts:
    def __init__(self,user_id):
        self.user_id = user_id

    def get_mongo_client_db(self):
        mongo = get_mongo_client()
        if not mongo:
            return ''
        db = mongo['legaldb']
        collection = db['aidrafts_complete_data']
        # Indexes are created via scripts/optimize_database_indexes.py
        # No need to create them on every request
        return collection

    def get_total_drafts_count(self):
        try:
            total_drafts = self.get_mongo_client_db().count_documents({'user_id': self.user_id})
            return total_drafts
        except Exception as e:
            logger.error(f" error at ---- get_total_drafts_count ---> {traceback.format_exc()}")
            return 0

    def start_new_session(self, user_query, draft_for, location={}, language='English'):
        """Create session and generate draft synchronously (legacy method - use async version)"""
        try:
            logger.info(f"[start_session] Received user_query: {user_query}")
            time_now = datetime.datetime.now(datetime.timezone.utc)

            # Create a new session
            session = {
                'user_id': self.user_id,
                'user_query': user_query,
                'draft_for': draft_for,
                'ai_suggested_update_count': 0,
                'location': location,
                'language': language,
                'draft_sections': [],
                'conversation_history': [],
                'created_on': time_now,
                'last_updated_on': time_now,
                'status': 'generating'
            }
            session_id = self.get_mongo_client_db().insert_one(session).inserted_id
            self.generate_draft(session_id, user_query, location, language)
            logger.info(f"[start_session] New session created with session_id: {session_id}")
            return session_id
        except Exception as err:
            logger.error(f" error at ---- start_new_session ---> {traceback.format_exc()}")
            return ''

    def start_new_session_without_ai(self, user_query, draft_for, location={}, language='English'):
        """Create session WITHOUT generating draft (for async processing)"""
        try:
            logger.info(f"[start_session_async] Received user_query: {user_query}")
            time_now = datetime.datetime.now(datetime.timezone.utc)

            session = {
                'user_id': self.user_id,
                'user_query': user_query,
                'draft_for': draft_for,
                'ai_suggested_update_count': 0,
                'location': location,
                'language': language,
                'draft_sections': [],
                'conversation_history': [],
                'created_on': time_now,
                'last_updated_on': time_now,
                'status': 'generating'  # Will be updated by async task
            }
            session_id = self.get_mongo_client_db().insert_one(session).inserted_id
            logger.info(f"[start_session_async] New session created: {session_id}. AI generation will be async.")
            return session_id
        except Exception as err:
            logger.error(f"Error at start_new_session_without_ai: {traceback.format_exc()}")
            return ''

    def auto_save_initial_draft(self, session_id, draft_name, draft_sections):
        """
        Pushes a first “Untitled …” saved_draft inside the session.
        Returns draft metadata.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        draft_id = str(ObjectId())
        self.get_mongo_client_db().update_one(
            {'_id': ObjectId(session_id)},
            {'$push': {'saved_drafts': {
                'draft_id'  : draft_id,
                'draft_name': draft_name,
                'sections'  : draft_sections,
                'saved_at'  : now
            }},
             '$set':  {'last_updated_on': now}}
        )
        return {
            'draft_id': draft_id,
            'saved_at': now,
            'last_updated_on': now,
        }


    # def update_location_for_draft_creation(self, session_id, state, district):
    #     """
    #         -- initially was used, now shifted the code flow, not needed anymore
    #     """
    #     try:
    #         # Update session with location
    #         time_now = datetime.datetime.now(datetime.timezone.utc)
    #         self.get_mongo_client_db().update_one(
    #             {'_id': ObjectId(session_id)},
    #             {'$set': {'location': {'state': state, 'district': district, 'last_updated_on': time_now}}}
    #         )

    #         logger.info(f"[set_location] Updated session {session_id} with location: {state}, {district}")

    #         # Retrieve updated session
    #         session = self.get_mongo_client_db().find_one({'_id': ObjectId(session_id)})
    #         if not session:
    #             logger.error(f"[set_location] Session {session_id} not found.")
    #             return {'mssg': False}

    #         # filter applied that if loading template sections are already present, so no need to generate again...
    #         if not len(session.get("draft_sections")):
    #             # Generate draft
    #             self.generate_draft(session_id, session['user_query'], state, district)

    #         logger.info(f"[set_location] Draft generated for session {session_id}")

    #         return {'mssg': True}
    #     except Exception as err:
    #         logger.error(f" error at ---- update_location_for_draft_creation ---> {traceback.format_exc()}")
    #         return {'mssg': False}

    def fetch_existing_template_text(self, draft_file_name, draft_type):
        """
        Retrieve the document from the 'draft_content_data' collection
        that matches the given 'draft_file_name' and 'draft_type',
        and return the 'content' field if found.
        """
        query = {
            "filename": draft_file_name,  # The 'filename' you store in Mongo
            "draft_type": draft_type
        }

        mongo = get_mongo_client()
        if not mongo:
            return ''
        db = mongo['legaldb']

        document = db['draft_content_data'].find_one(query)
        logger.info(f"fetch_existing_template_text ----> query: {query}, document: {document}")

        if document:
            return document.get("content", "")
        else:
            return None


    def generate_draft(self, session_id, user_query, location, language):
        logger.info(f"[generate_draft] Generating draft for session_id: {session_id} ----location >>> {location}")
        location_string = ''
        if len(location):
            if 'court' in location and 'district' in location and 'state' in location:
                location_string =  f"""for court "{location.get('court')}" in the district "{location.get('district')}" of state "{location.get('state')}" """
            elif 'district' in location and 'state' in location:
                location_string =  f"""in the district "{location.get('district')}" of state "{location.get('state')}" """
            elif 'state' in location:
                location_string =  f"""for the state "{location.get('state')}" """

        # Construct prompt
        prompt = f"""
You are a legal expert specializing in drafting legal documents as per Indian legal standards and the Indian constitution.

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

        logger.info(f"[generate_draft] Prompt sent to LLM: {prompt}")

        try:
            draft_content = chat_complete(
                messages=[{'role': 'user', 'content': prompt}],
                app_scenario='ai_draft:generate',
                temperature=0.3,  # Low temp → reliable JSON structure
                max_tokens=4000,
            )
            logger.info(f"[generate_draft] Received draft_content from LLM: {draft_content}")

        except Exception as e:
            logger.error(f"[generate_draft] Error while calling ChatGPT API: {e}")
            return

        # Parse draft into sections
        draft_sections = self.parse_draft_into_sections(draft_content)

        logger.info(f"[generate_draft] Parsed draft_sections: {draft_sections}")

        # Update session with draft sections
        self.get_mongo_client_db().update_one(
            {'_id': ObjectId(session_id)},
            {'$set': {'draft_sections': draft_sections,
                    'original_draft': draft_sections}}
        )

        logger.info(f"[generate_draft] Session {session_id} updated with draft_sections.")


    def parse_draft_into_sections(self, draft_content):
        logger.info("[parse_draft_into_sections] Parsing draft content into sections.")

        # Remove Markdown code block syntax if present
        if draft_content.startswith("```") and draft_content.endswith("```"):
            # Remove the first line (```json) and the last line (```)
            draft_content = '\n'.join(draft_content.split('\n')[1:-1])

        # Check if draft_content is non-empty
        if not draft_content.strip():
            logger.error("[parse_draft_into_sections] draft_content is empty.")
            return []

        # Try to parse the JSON
        try:
            logger.info("[parse_draft_into_sections] draft_content to be parsed: %s", draft_content)  # Corrected logging
            sections = json.loads(draft_content)  # Attempt JSON parsing

            # Validate each section in the parsed JSON
            for section in sections:
                if not isinstance(section, dict) or 'section_name' not in section or 'content' not in section:
                    logger.error("[parse_draft_into_sections] Invalid section format.")
                    return []
                section['section_id'] = str(ObjectId())  # Add unique ID to each section

            logger.info("[parse_draft_into_sections] Successfully parsed sections.")
            return sections

        except json.JSONDecodeError as e:
            logger.error("[parse_draft_into_sections] JSONDecodeError: %s", str(e))
            logger.error("[parse_draft_into_sections] draft_content received: %s", draft_content)
            return []
        except Exception as e:
            logger.error(f"[parse_draft_into_sections] Exception: {traceback.format_exc()}")
            return []

    def update_specific_section_of_the_draft(self, session_id, section_id, section_name, content):
        try:
            session = self.get_mongo_client_db().find_one({'_id': ObjectId(session_id)})
            section = next((s for s in session['draft_sections'] if s['section_id'] == section_id), None)
            if section:
                # Save the current content in history
                history_entry = {
                    'section_name': section['section_name'],
                    'content': section['content'],
                    'timestamp': datetime.datetime.now(datetime.timezone.utc)
                }
                self.get_mongo_client_db().update_one(
                    {'_id': ObjectId(session_id), 'draft_sections.section_id': section_id},
                    {'$push': {'draft_sections.$.history': history_entry}}
                )
                logger.info(f"update_specific_section_of_the_draft ========>>> {history_entry} || updateddd")
            else:
                return {'mssg': False}
            time_now = datetime.datetime.now(datetime.timezone.utc)
            # Update the section in the session
            result = self.get_mongo_client_db().update_one(
                {'_id': ObjectId(session_id), 'draft_sections.section_id': section_id},
                {'$set': {
                    'draft_sections.$.section_name': section_name,
                    'draft_sections.$.content': content,
                    'last_updated_on': time_now
                }}
            )
            return {'mssg': True}
        except Exception as e:
            logger.error(f"[update_specific_section_of_the_draft]  ============>>>>>>: {traceback.format_exc()}")
            return {'mssg': False}

    def delete_specific_section_of_the_draft(self, session_id, section_id):
        try:
            time_now = datetime.datetime.now(datetime.timezone.utc)
            # Remove the section from the session
            result = self.get_mongo_client_db().update_one(
                {'_id': ObjectId(session_id)},
                {'$pull': {'draft_sections': {'section_id': section_id}},
                 '$set': {'last_updated_on': time_now}}
            )

            if result.modified_count == 0:
                logger.error(f"[delete_section] No matching section to delete for session_id: {session_id}, section_id: {section_id}")
                return {'mssg': False}

            logger.info(f"[delete_section] Section {section_id} deleted successfully from session {session_id}.")
            return {'mssg': True}
        except Exception as e:
            logger.error(f"[delete_specific_section_of_the_draft]  ============>>>>>>: {traceback.format_exc()}")
            return {'mssg': False}

    def update_content_using_AI_with_user_input(self, session_id, section_id, suggestion):
        try:
            session = self.get_mongo_client_db().find_one({'_id': ObjectId(session_id)})
            all_sections = session.get('draft_sections', [])
            section = next(
                (s for s in all_sections if s['section_id'] == section_id), None
            )

            # Build a brief summary of the other sections for context
            other_sections_context = '\n'.join(
                f'  - {s["section_name"]}: {(s.get("content") or "")[:300].strip()}{"..." if len(s.get("content") or "") > 300 else ""}'
                for s in all_sections if s['section_id'] != section_id and (s.get('content') or '').strip()
            )
            context_block = (
                f"\nFor context, the rest of the draft contains these sections:\n{other_sections_context}\n"
                if other_sections_context else ''
            )

            # Construct prompt for LLM
            prompt = f"""You are refining one section of a legal draft.{context_block}
The section to update is titled "{section['section_name']}":

{section['content']}

The user's instruction for this section:

{suggestion}

Update ONLY this section, incorporating the user's instruction. Ensure the content aligns with the rest of the draft and complies with Indian legal standards.

Return ONLY the updated section content. Do not include any headings, labels, preamble, or extra commentary."""

            updated_content = chat_complete(
                messages=[{'role': 'user', 'content': prompt}],
                app_scenario='ai_draft:update_section',
                temperature=0.4,
                max_tokens=2000,
            )
            return {'mssg': updated_content}
        except Exception as e:
            logger.error(f"[update_content_using_AI_with_user_input]  ============>>>>>>: {traceback.format_exc()}")
            return {'mssg': False}

    def add_new_section_in_existing_draft(self, session_id, section_name, content):
        try:
            section_id = str(ObjectId())
            new_section = {
                'section_id': section_id,
                'section_name': section_name,
                'content': content
            }
            time_now = datetime.datetime.now(datetime.timezone.utc)
            # Add the new section to the session
            result = self.get_mongo_client_db().update_one(
                {'_id': ObjectId(session_id)},
                {'$push': {'draft_sections': new_section},
                 '$set': {'last_updated_on': time_now}}
            )

            if result.modified_count == 0:
                logger.error(f"[add_section] Failed to add section to session {session_id}.")
                return {'mssg': False}

            logger.info(f"[add_section] Section {section_id} added successfully to session {session_id}.")
            return {'mssg': new_section}
        except Exception as e:
            logger.error(f"[add_new_section_in_existing_draft]  ============>>>>>>: {traceback.format_exc()}")
            return {'mssg': False}

    def prepare_content_for_download(self, session_id):
        try:
            # Retrieve session
            session = self.get_mongo_client_db().find_one({'_id': ObjectId(session_id)})
            if not session:
                logger.error(f"[download_draft] Session {session_id} not found.")
                return {'mssg': False} 

            draft_sections = session.get('draft_sections', [])
            if not draft_sections:
                logger.error(f"[download_draft] No draft sections found for session {session_id}.")
                return {'mssg': False} 

            logger.info(f"[download_draft] Compiling draft sections for session {session_id}.")

            # Compile all sections into one document
            document = Document()
            for section in draft_sections:
                section_name = section.get('section_name', 'Untitled Section')
                content = section.get('content', '')

                document.add_heading(section_name, level=1)
                document.add_paragraph(content)

                logger.info(f"[download_draft] Added section: {section_name}")

            # Save document to a BytesIO stream

            doc_io = BytesIO()
            document.save(doc_io)
            doc_io.seek(0)
            return {'mssg': doc_io}
        except Exception as e:
            logger.error(f"[prepare_content_for_download]  ============>>>>>>: {traceback.format_exc()}")
            return {'mssg': False}

    def adjust_section_position_in_draft(self, session_id,draft_sections):
        try:
            # Ensure that only the section_ids and their order are updated
            new_order = [{'section_id': s['section_id']} for s in draft_sections]

            # Fetch current sections
            session = self.get_mongo_client_db().find_one({'_id': ObjectId(session_id)})
            current_sections = session['draft_sections']

            # Create a mapping from section_id to section data
            section_map = {s['section_id']: s for s in current_sections}

            # Reorder sections
            reordered_sections = [section_map[s['section_id']] for s in new_order]

            time_now = datetime.datetime.now(datetime.timezone.utc)
            # Update the session with the new order
            self.get_mongo_client_db().update_one(
                {'_id': ObjectId(session_id)},
                {'$set': {'draft_sections': reordered_sections, 'last_updated_on': time_now}},
            )
            return {'mssg': True}
        except Exception as e:
            logger.error(f"[adjust_section_position_in_draft]  ============>>>>>>: {traceback.format_exc()}")
            return {'mssg': False}

    def retrieve_history_of_section_of_draft_if_updated(self, session_id, section_id):
        try:
            # Retrieve session and section
            session = self.get_mongo_client_db().find_one({'_id': ObjectId(session_id)})
            if not session:
                return {'mssg': False}

            section = next(
                (s for s in session['draft_sections'] if s['section_id'] == section_id), None
            )
            if not section:
                return {'mssg': False}

            history = section.get('history', [])
            return {'mssg': history}
        except Exception as e:
            logger.error(f"[retrieve_history_of_section_of_draft_if_updated]  ============>>>>>>: {traceback.format_exc()}")
            return {'mssg': False}

    def retrieve_sections_of_draft(self, session_id):
        try:
            # Retrieve session
            session = self.get_mongo_client_db().find_one({'_id': ObjectId(session_id)})
            if not session:
                logger.error(f"[get_draft_sections] Session {session_id} not found.")
                return {'mssg': False, 'status': 'not_found'}

            draft_sections = session.get('draft_sections', [])
            final_count = session.get('ai_suggested_update_count', 0)
            status = session.get('status', 'completed')
            
            logger.info(f"[get_draft_sections] Retrieved {len(draft_sections)} sections for session {session_id}. Status: {status}")
            return {
                'mssg': draft_sections, 
                'ai_suggested_update_count': final_count,
                'status': status
            }
        except Exception as e:
            logger.error(f"[retrieve_sections_of_draft]  ============>>>>>>: {traceback.format_exc()}")
            return {'mssg': False, 'ai_suggested_update_count': 0, 'status': 'error'}

    def retrieve_single_section_from_session(self, session_id, section_id):
        try:
            draft_section = self.get_mongo_client_db().find_one(
                        {
                            '_id': ObjectId(session_id),  # Match the session by session_id
                            'user_id': self.user_id,
                            'draft_sections.section_id': section_id  # Match the section_id within the draft_sections array
                        },
                        {
                            'draft_sections.$': 1  # Project the matched section from draft_sections
                        }
                    )
            latest_content = draft_section['draft_sections'][0]['content']
            logger.info(f"retrieve_single_section_from_session ========== <><><><><><><><> {latest_content}")
            return {'mssg': latest_content}
        except Exception as e:
            logger.error(f"[retrieve_single_section_from_session]  ============>>>>>>: {traceback.format_exc()}")
            return {'mssg': False}

    def revert_draft_changes_to_intial_stage(self, session_id):
        try:
            session = self.get_mongo_client_db().find_one({'_id': ObjectId(session_id)})
            if not session or 'original_draft' not in session:
                return {'mssg': False}
            time_now = datetime.datetime.now(datetime.timezone.utc)
            self.get_mongo_client_db().update_one(
                {'_id': ObjectId(session_id)},
                {'$set': {'draft_sections': session['original_draft'], 'last_updated_on': time_now}}
            )
            return {'mssg': True}
        except Exception as e:
            logger.error(f"[revert_draft_changes_to_intial_stage]  ============>>>>>>: {traceback.format_exc()}")
            return {'mssg': False}


    def save_semi_filled_drafts(self, session_id, draft_name, draft_sections, draft_id=None):
        """
        If draft_id is given, try to update that existing saved draft.
        If not found or not given, insert a new one.
        """
        try:
            session_object_id = ObjectId(session_id)

            # Validate the session
            session = self.get_mongo_client_db().find_one({'_id': session_object_id, 'user_id': self.user_id})
            if not session:
                logger.error(f"[save_semi_filled_drafts] Session not found for session_id: {session_id}")
                return {'mssg': False}

            # Make sure 'saved_drafts' is in the session
            if 'saved_drafts' not in session:
                self.get_mongo_client_db().update_one(
                    {'_id': session_object_id},
                    {'$set': {'saved_drafts': []}}
                )

            time_now = datetime.datetime.now(datetime.timezone.utc)

            if draft_id:
                # Overwrite the existing entry if it exists
                result = self.get_mongo_client_db().update_one(
                    {
                        '_id': session_object_id,
                        'user_id': self.user_id,
                        'saved_drafts.draft_id': draft_id
                    },
                    {
                        '$set': {
                            'saved_drafts.$.draft_name': draft_name,
                            'saved_drafts.$.sections': draft_sections,
                            'saved_drafts.$.saved_at': time_now,
                            'last_updated_on': time_now,
                        }
                    }
                )
                if result.modified_count > 0:
                    logger.info(f"[save_semi_filled_drafts] Updated existing saved draft: {draft_id}")
                    return {
                        'mssg': True,
                        'draft_id': draft_id,
                        'saved_at': time_now,
                        'last_updated_on': time_now,
                    }

                # If no match found, we proceed to create new 
                # or you can return an error if you'd prefer.

            # Otherwise, create a new saved draft
            new_draft_id = str(ObjectId())
            saved_draft = {
                'draft_id': new_draft_id,
                'draft_name': draft_name,
                'sections': draft_sections,
                'saved_at': time_now
            }
            self.get_mongo_client_db().update_one(
                {'_id': session_object_id, 'user_id': self.user_id},
                {
                    '$push': {'saved_drafts': saved_draft},
                    '$set': {'last_updated_on': time_now},
                }
            )
            logger.info(f"[save_semi_filled_drafts] Created new saved draft: {new_draft_id}")
            return {
                'mssg': True,
                'draft_id': new_draft_id,
                'saved_at': time_now,
                'last_updated_on': time_now,
            }

        except Exception as e:
            logger.error(f"[save_semi_filled_drafts] Exception: {traceback.format_exc()}")
            return {'mssg': False}


    # def get_saved_draft_list(self):
    #     try:
    #         # Fetch all sessions for the user
    #         sessions = self.get_mongo_client_db().find({'user_id': self.user_id}, {'saved_drafts': 1})

    #         saved_drafts = []
    #         for session in sessions:
    #             for draft in session.get('saved_drafts', []):
    #                 saved_drafts.append({
    #                     'draft_name': draft['draft_name'],
    #                     'draft_id': draft['draft_id'],
    #                     'created_on': draft['saved_at'],
    #                     'last_updated_on': draft.get('last_updated_on', draft['saved_at']),
    #                     'session_id': str(session['_id'])
    #                 })
    #         return {'mssg': saved_drafts}
    #     except Exception as e:
    #         logger.error(f"[get_saved_draft_list]  ============>>>>>>: {traceback.format_exc()}")
    #         return {'mssg': False}

    def get_saved_draft_list(self, page, page_size, filter_query):
        try:
            # Calculate total count for pagination
            total_count = self.get_mongo_client_db().count_documents(filter_query)
            logger.info(f"get_saved_draft_list ============== total_count ===============>.>>>>> {total_count}")
            # Calculate total pages
            total_pages = math.ceil(total_count / page_size) if page_size > 0 else 1

            # Ensure page is within bounds
            if page < 1:
                page = 1
            elif page > total_pages and total_pages > 0:
                page = total_pages

            # Define the aggregation pipeline
            pipeline = [
                        {'$match': filter_query},
                        {'$unwind': '$saved_drafts'},
                        {'$project': {
                            'draft_name': '$saved_drafts.draft_name',
                            'draft_id': {'$toString': '$saved_drafts.draft_id'},
                            'draft_for': '$draft_for',  # Extract draft_for from the top-level document
                            'created_on': {
                                '$dateToString': {
                                    'format': '%Y-%m-%dT%H:%M:%SZ',
                                    'date': '$created_on'
                                }
                            },
                            'last_updated_on': {
                                '$dateToString': {
                                    'format': '%Y-%m-%dT%H:%M:%SZ',
                                    'date': '$last_updated_on'
                                }
                            },
                            'session_id': {'$toString': '$_id'}
                        }},
                        {'$sort': {'created_on': -1}},  # Adjust sort as needed
                        {'$facet': {
                            'paginatedResults': [
                                {'$skip': (page - 1) * page_size},
                                {'$limit': page_size}
                            ],
                            'totalCount': [
                                {'$count': 'count'}
                            ]
                        }}
                    ]

            aggregation_result = list(self.get_mongo_client_db().aggregate(pipeline))

            if not aggregation_result:
                saved_drafts = []
                total_count = 0
            else:
                paginated_results = aggregation_result[0].get('paginatedResults', [])
                saved_drafts = []
                for draft in paginated_results:
                    saved_drafts.append({
                        'draft_name': draft.get('draft_name', 'N/A'),
                        'draft_id': draft.get('draft_id', 'N/A'),
                        'created_on': draft.get('created_on', datetime.datetime.now(datetime.timezone.utc).isoformat() + 'Z'),
                        'last_updated_on': draft.get('last_updated_on', datetime.datetime.now(datetime.timezone.utc).isoformat() + 'Z'),
                        'session_id': draft.get('session_id', 'N/A'),
                        'draft_for': draft.get('draft_for', {})
                    })
                #total_count = aggregation_result[0].get('totalCount', [{'count': 0}])[0].get('count', 0)
                total_count = aggregation_result[0].get('totalCount', [{'count': 0}])
                #logger.info(f"total_count ==========>>>> {total_count}")
                if len(total_count):
                    total_count = total_count[0].get('count', 0)
                else:
                    total_count = 0

            # Calculate total pages
            total_pages = math.ceil(total_count / page_size) if page_size > 0 else 1
            #logger.info(f"get_saved_draft_list ============== saved_drafts ===============>.>>>>> {saved_drafts[-1]}")

            return {
                'saved_drafts': saved_drafts,
                'pagination': {
                    'current_page': page,
                    'page_size': page_size,
                    'total_pages': total_pages,
                    'total_count': total_count
                }
            }
        except Exception as e:
            logger.error(f"[get_saved_draft_list]  ============>>>>>>: {traceback.format_exc()}")
            return {'err': False}

    def delete_saved_draft(self, session_id, draft_id):
        try:
            try:
                session_object_id = ObjectId(session_id)
                draft_object_id = ObjectId(draft_id)
            except Exception as e:
                logger.error(f"Invalid session_id or draft_id format.")
                {'mssg': False}

            # Remove the draft from saved_drafts
            result = self.get_mongo_client_db().update_one(
                {'_id': session_object_id, 'user_id':self.user_id},
                {'$pull': {'saved_drafts': {'draft_id': draft_id}}}
            )
            return {'mssg': True}
        except Exception as e:
            logger.error(f"[delete_saved_draft]  ============>>>>>>: {traceback.format_exc()}")
            return {'mssg': False}

    def load_saved_draft_details(self, session_id, draft_id):
        try:
            try:
                session_object_id = ObjectId(session_id)
            except Exception as e:
                logger.error(f"Invalid session_id format: {session_id}")
                return {'error': 'Invalid session_id format.'}

            # Fetch the session document
            session = self.get_mongo_client_db().find_one({'user_id':self.user_id, '_id': session_object_id})

            if not session:
                logger.error(f"Session not found for session_id: {session_id}")
                return {'error': 'Session not found.'}

            # Find the saved draft
            saved_draft = next((draft for draft in session.get('saved_drafts', [])
                                if draft['draft_id'] == draft_id), None)

            if not saved_draft:
                logger.error(f"Draft not found for draft_id: {draft_id}")
                return {'error': 'Draft not found.'}

            return {'draft_sections': saved_draft['sections']}

        except Exception as e:
            logger.error(f"Exception in load_saved_draft: {traceback.format_exc()}")
            return {'error': 'An error occurred while loading the draft.'}


    def save_draft_from_template(self, draft_type, draft_sections, draft_for=None):
        try:
            if draft_for is None:
                draft_for = {}
            time_now = datetime.datetime.now(datetime.timezone.utc)
            # Create a new session
            session = {
                'user_id': self.user_id,
                'user_query': draft_type,
                'draft_for': draft_for,
                'location': {
                    'last_updated_on': time_now
                },
                'draft_sections': draft_sections,
                'conversation_history': [],
                'created_on': time_now,
                'last_updated_on': time_now,
                'original_draft': draft_sections.copy()
            }

            # Insert the session into MongoDB
            result = self.get_mongo_client_db().insert_one(session)
            session_id = str(result.inserted_id)
            return {"mssg":session_id}
        except Exception as e:
            logger.error(f"Exception in load_saved_draft: {traceback.format_exc()}")
            return {'error': 'An error occurred while loading the draft.'}

    # def extract_text_from_file(self,file_path):
    #     """
    #     Extract text from a file (PDF, DOC, TXT).
    #     """
    #     text = textract.process(file_path).decode('utf-8')
    #     return text

    # def generate_draft_sections_from_template(self,file_text, draft_type, state, district):
    #     """
    #     Generate draft sections from the extracted text.
    #     You can customize this function to parse the text and create sections.
    #     """
    #     # For simplicity, we'll create one section with the entire text
    #     draft_sections = [{
    #         'section_id': str(ObjectId()),
    #         'section_name': 'Template Content',
    #         'content': file_text
    #     }]
    #     return draft_sections

    def split_text_into_sections(self, text):
        """
        Split the generated text into sections.
        """
        # For simplicity, let's assume sections are separated by headings
        # Customize this function based on your needs
        lines = text.split('\n')
        sections = []
        current_section = {'section_id': str(ObjectId()), 'section_name': '', 'content': ''}
        for line in lines:
            if line.isupper():
                # Start of a new section
                if current_section['section_name']:
                    sections.append(current_section)
                    current_section = {'section_id': str(ObjectId()), 'section_name': line, 'content': ''}
                else:
                    current_section['section_name'] = line
            else:
                current_section['content'] += line + '\n'
        if current_section['section_name']:
            sections.append(current_section)
        return sections

    def insert_draft_session_for_casedocument(self, draft_sections, draft_for, language='English'):
        try:
            # Validate 'draft_for'
            if not isinstance(draft_for, dict):
                logger.warning("draft_for is not a dictionary.")
                draft_for = {}

            # Allowed keys
            allowed_keys = {'caseid', 'clientid', 'caseid_with_clientid'}

            # Filter out unwanted keys and ensure values are lists
            draft_for_filtered = {k: v for k, v in draft_for.items() if k in allowed_keys and isinstance(v, list) and len(v) > 0}

            if 'personal' in draft_for.keys():
                draft_for_filtered['personal']='Y'
            # logger.info(f"insert_draft_session_for_casedocument ---  draft_for_filtered  ->>>>> {draft_for_filtered} ====== {draft_for}")
            # Check how many keys are populated
            # populated_keys = [k for k, v in draft_for_filtered.items() if v]
            # Create a new session
            session = {
                'user_id': self.user_id,
                'user_query': 'case_document',
                'draft_for': draft_for_filtered,
                'language': language,
                'location': {},  # No state and district needed
                'draft_sections': draft_sections,
                'conversation_history': [],
                'created_on': datetime.datetime.now(datetime.timezone.utc),
                'last_updated_on': datetime.datetime.now(datetime.timezone.utc),
                'original_draft': draft_sections.copy()
            }

            # Insert the session into MongoDB
            result = self.get_mongo_client_db().insert_one(session)
            session_id = str(result.inserted_id)
            return {"mssg":session_id}
        except Exception as e:
            logger.error(f"[generate_draft_sections_with_gpt]  ============>>>>>>: {traceback.format_exc()}")
            return {"mssg":False}

    def extract_text_from_file(self, file_stream, file_name):
        """
        Extract text from a file-like object based on its type.
        Supports PDF, DOCX, TXT.
        """
        try:
            if file_name.endswith('.pdf'):
                # Use pdfminer.six
                text = extract_text_from_pdf(file_stream)
                return text
            elif file_name.endswith('.docx'):
                # Use python-docx
                document = Document(file_stream)
                text = '\n'.join([paragraph.text for paragraph in document.paragraphs])
                return text
            elif file_name.endswith('.txt'):
                # For text files
                text = file_stream.read().decode('utf-8')
                return text
            elif file_name.endswith('.doc'):
                # For .doc files, we need to use external tools or convert to DOCX
                logger.error("Unsupported file format: .doc")
                return None
            else:
                logger.error("Unsupported file format.")
                return None
        except Exception as e:
            logger.error(f"Exception in extract_text_from_file: {traceback.format_exc()}")
            return None

    def generate_draft_sections_from_template(self, file_text, draft_type):
        """
        Use OpenAI to process the file text and generate draft sections.
        """
        # Create the prompt
        prompt = f"""
You are a legal expert specializing in drafting legal documents as per Indian legal standards and the Indian constitution.

A user has requested: "{draft_type}" and to use this template text {file_text} only to generate the draft and follow the instructions below.

**Formatting Instructions:**

- Output the draft in **JSON** format.
- The JSON should be an array of sections.
- Each section should be an object with two properties:
  - `"section_name"`: The name of the section.
  - `"content"`: The content of the section, including placeholders where specific user information is required (like names, dates, addresses) in ALL CAPS (e.g., `[YOUR FULL NAME]`, `[DATE OF BIRTH]`).
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
]
        """

        try:
            generated_text = chat_complete(
                messages=[{'role': 'user', 'content': prompt}],
                app_scenario='ai_draft:generate_from_tpl',
                temperature=0.3,
                max_tokens=4000,
            ).strip()

            # Parse the generated text into draft sections
            draft_sections = self.parse_draft_into_sections(generated_text)

            return draft_sections

        except Exception as e:
            logger.error(f"Exception in generate_draft_sections_from_template: {traceback.format_exc()}")
            return None

    def generate_draft_sections_with_gpt(self,file_text, language='English'):
        """
        Use OpenAI to generate draft sections from the case document text.
        """
        # Create the prompt
        prompt = f"""
You are a legal expert specializing in drafting legal documents as per Indian legal standards and the Indian constitution.

Analyze the following case document and generate a legal draft accordingly **in {language}**.

**Formatting Instructions:**

- Output the draft in **JSON** format.
- The JSON should be an array of sections.
- Each section should be an object with two properties:
  - `"section_name"`: The name of the section.
  - `"content"`: The content of the section, including placeholders where specific user information is required (like names, dates, addresses) in ALL CAPS (e.g., `[YOUR FULL NAME]`, `[DATE OF BIRTH]`). Beside each placeholder, fill in the value if it can be found in the case document provided.
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
]

Here is the case document:

{file_text}
        """

        try:
            generated_text = chat_complete(
                messages=[{'role': 'user', 'content': prompt}],
                app_scenario='ai_draft:generate_from_case',
                temperature=0.3,
                max_tokens=4000,
            ).strip()

            # Parse the generated text into draft sections
            draft_sections = self.parse_draft_into_sections(generated_text)

            return draft_sections

        except Exception as e:
            logger.error(f"Exception in generate_draft_sections_with_gpt: {traceback.format_exc()}")
            return None


    def update_ai_suggested_content_count(self, session_id):
        try:
            session_object_id = ObjectId(session_id)
            update_result = self.get_mongo_client_db().find_one_and_update(
                {'user_id': self.user_id, '_id': session_object_id},
                {'$inc': {'ai_suggested_update_count': 1}},
                return_document=ReturnDocument.AFTER
            )

            # Now you can access the final count from the updated document
            final_count = (update_result or {}).get('ai_suggested_update_count', 0)
            return final_count
        except Exception as e:
            logger.error(f"Exception in update_ai_suggested_content_count: {traceback.format_exc()}")
            return 0


    def get_ai_suggested_content_count(self, session_id):
        try:
            session_object_id = ObjectId(session_id)
            draft = self.get_mongo_client_db().find_one(
                {'user_id': self.user_id, '_id': session_object_id},
                {'ai_suggested_update_count': 1},
            )
            return int((draft or {}).get('ai_suggested_update_count', 0))
        except Exception:
            logger.error(f"Exception in get_ai_suggested_content_count: {traceback.format_exc()}")
            return 0


    def fetch_draft_for(self,session_id):
        try:
            # Assuming session_id is unique and corresponds to a single document
            session_object_id = ObjectId(session_id)
            draft = self.get_mongo_client_db().find_one({'user_id':self.user_id, '_id': session_object_id})
            # draft = drafts_collection.find_one({'user_id': session_id})
            if not draft:
                return {'error': 'Draft not found for the provided session_id.'}

            draft_for = draft.get('draft_for', {})
            return {'draft_for': draft_for}
        except Exception as e:
            logger.error(f"Exception in generate_draft_sections_with_gpt: {traceback.format_exc()}")
            return {'error': 'An error occurred while fetching draft details.'}
