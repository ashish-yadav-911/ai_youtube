# import logging
# import json
# from typing import List, Optional, Tuple
# # --- Import BOTH clients and Base Error ---
# from openai import AsyncOpenAI, OpenAI, OpenAIError # Import Sync OpenAI

# from app.celery_app import celery
# from app.core.config import settings
# from app.services.database_service import DatabaseService
# from app.models.video_job import JobStatus
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.database import AsyncSessionLocal

# logger = logging.getLogger(__name__)

# # --- Initialize BOTH clients ---
# async_client: Optional[AsyncOpenAI] = None # Keep async for flexibility if needed elsewhere
# sync_client: Optional[OpenAI] = None # Sync client for use in task

# if not settings.OPENAI_API_KEY:
#     logger.warning("OPENAI_API_KEY not found. LLM features will fail.")
# else:
#     # Consider timeout settings for longer LLM calls
#     async_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=120.0)
#     sync_client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=120.0) # Initialize Sync client

# # --- Constants for Prompts (keep as before) ---
# GENRE_DETERMINATION_PROMPT_TEMPLATE = """
# Analyze the following script and determine its primary genre or category from the list below.
# Focus on the overall theme, style, and content.

# Possible Genres:
# - Storytelling / Narrative
# - Educational / Explainer
# - Historical Fact / Analysis
# - Current Events / News Commentary
# - Product Review / Tutorial
# - Opinion / Rant
# - Comedy / Sketch
# - Inspirational / Motivational
# - Science / Technology Update
# - Travel / Exploration
# - Personal Vlog / Update

# Script:
# \"\"\"
# {script_text}
# \"\"\"

# Output only the *single most fitting genre* from the list above.
# Genre:"""

# TOPIC_GENERATION_PROMPT_TEMPLATE = """
# Based on the following script and its identified genre, generate {topic_count} unique and engaging YouTube video topic ideas that are closely related or follow-up logically.
# The topics should be suitable for short-form or medium-length faceless YouTube videos.

# Script Genre: {genre}

# Script Content:
# \"\"\"
# {script_text}
# \"\"\"

# Generate exactly {topic_count} topics. Format the output as a JSON list of strings.
# Example JSON Output:
# ["Topic Idea 1", "Topic Idea 2", "Topic Idea 3"]

# JSON Topic List:"""


# class LLMService:
#     """Interacts with LLMs for script analysis and topic generation."""

#     # --- Renamed and converted to SYNCHRONOUS ---
#     def _call_openai_api_sync(self, prompt: str, model: str = "gpt-3.5-turbo") -> Optional[str]:
#         """Helper function to call the OpenAI ChatCompletion API SYNCHRONOUSLY."""
#         if not sync_client: # Use sync_client
#             logger.error("OpenAI sync client not initialized. Cannot call API.")
#             return None
#         try:
#             logger.debug(f"Calling SYNC OpenAI API with model {model}. Prompt length: {len(prompt)}")
#             # --- Use sync client, NO await ---
#             response = sync_client.chat.completions.create(
#                 model=model,
#                 messages=[
#                     {"role": "system", "content": "You are a helpful assistant analyzing video scripts."},
#                     {"role": "user", "content": prompt}
#                 ],
#                 temperature=0.7,
#                 max_tokens=1500,
#             )
#             result = response.choices[0].message.content
#             logger.debug(f"Received SYNC response from OpenAI. Length: {len(result or '')}")
#             return result.strip() if result else None
#         # --- Catch base OpenAIError (works for sync/async) ---
#         except OpenAIError as e:
#             logger.error(f"SYNC OpenAI API Error: {str(e)}") # Log str(e), remove exc_info
#             return None
#         except Exception as e:
#             logger.error(f"Unexpected error calling SYNC OpenAI API: {str(e)}") # Log str(e), remove exc_info
#             return None

#     # --- Remains async def, calls sync helper ---
#     async def determine_genre(self, script_text: str) -> Optional[str]:
#         """Determines the genre of the script using an LLM (via sync call)."""
#         if not script_text:
#             logger.warning("Cannot determine genre from empty script.")
#             return None

#         prompt = GENRE_DETERMINATION_PROMPT_TEMPLATE.format(script_text=script_text[:4000]) # Limit input size
#         # --- Call sync helper, NO await ---
#         genre = self._call_openai_api_sync(prompt, model="gpt-3.5-turbo") # Use cheaper model for classification

#         if genre and genre in [
#             "Storytelling / Narrative", "Educational / Explainer", "Historical Fact / Analysis",
#             "Current Events / News Commentary", "Product Review / Tutorial", "Opinion / Rant",
#             "Comedy / Sketch", "Inspirational / Motivational", "Science / Technology Update",
#             "Travel / Exploration", "Personal Vlog / Update"
#         ]:
#             logger.info(f"Determined genre: {genre}")
#             return genre
#         else:
#             logger.warning(f"Could not determine a valid genre. LLM response: {genre}")
#             return "Unknown" # Default or fallback genre

#     # --- Remains async def, calls sync helper ---
#     async def generate_topics(self, script_text: str, genre: str, topic_count: int = 10) -> Optional[List[str]]:
#         """Generates related video topics using an LLM (via sync call)."""
#         if not script_text or not genre:
#             logger.warning("Cannot generate topics without script or genre.")
#             return None

#         prompt = TOPIC_GENERATION_PROMPT_TEMPLATE.format(
#             script_text=script_text[:4000], # Limit input size
#             genre=genre,
#             topic_count=topic_count
#         )
#         model="gpt-3.5-turbo" # Start with 3.5 turbo

#         # --- Call sync helper, NO await ---
#         raw_response = self._call_openai_api_sync(prompt, model=model)

#         if not raw_response:
#             logger.error("Failed to get response from LLM for topic generation.")
#             return None

#         # Attempt to parse the JSON response
#         try:
#             json_start = raw_response.find('[')
#             json_end = raw_response.rfind(']') + 1
#             if json_start != -1 and json_end != -1:
#                 json_str = raw_response[json_start:json_end]
#                 topics = json.loads(json_str)
#                 if isinstance(topics, list) and all(isinstance(t, str) for t in topics):
#                      if abs(len(topics) - topic_count) > topic_count * 0.5:
#                          logger.warning(f"LLM returned {len(topics)} topics, expected around {topic_count}.")
#                      logger.info(f"Successfully parsed {len(topics)} topics from LLM response.")
#                      return topics[:topic_count]
#                 else:
#                     logger.error(f"LLM response parsed but is not a list of strings: {topics}")
#                     return None
#             else:
#                 logger.error(f"Could not find JSON list in LLM response: {raw_response}")
#                 return None
#         except json.JSONDecodeError as e:
#              logger.error(f"Failed to decode JSON from LLM response: {str(e)}\nResponse snippet: {raw_response[:200]}") # Log str(e)
#              return None
#         except Exception as e:
#              logger.error(f"Error processing LLM topic response: {str(e)}\nResponse snippet: {raw_response[:200]}") # Log str(e)
#              return None


#     @staticmethod
#     # --- Fixed typo: ignore_result=True ---
#     @celery.task(name="tasks.generate_topics", bind=True, ignore_result=True)
#     async def generate_topics_task(self, job_id: int):
#         # --- Task remains async ---
#         logger.info(f"Starting topic generation task for job_id: {job_id}")
#         db_service = DatabaseService()
#         llm_service = LLMService()
#         final_status = JobStatus.FAILED
#         status_message = "Topic generation failed"
#         generated_topics = None
#         determined_genre = None

#         # --- Manual Session Management ---
#         session: AsyncSession = AsyncSessionLocal()
#         try:
#             # 1. Get the job and its transcript (await DB call)
#             job = await db_service.get_job(session, job_id) # Use session
#             if not job:
#                 raise ValueError(f"Job {job_id} not found.")
#             if not job.transcript:
#                 raise ValueError(f"Job {job_id} has no transcript to process.")

#             if job.status == JobStatus.COMPLETED and job.topics:
#                 logger.warning(f"Job {job_id} already has topics. Skipping generation.")
#                 final_status = JobStatus.COMPLETED
#                 status_message = "Topics already generated."
#                 generated_topics = job.topics
#                 determined_genre = job.script_genre
#             else:
#                 # 2. Update status to processing start (await DB call)
#                 await db_service.update_job_status(session, job_id, JobStatus.PROCESSING, "Determining script genre...")
#                 await session.commit()

#                 # 3. Determine Genre (await async method which wraps sync call)
#                 determined_genre = await llm_service.determine_genre(job.transcript)
#                 if not determined_genre or determined_genre == "Unknown":
#                     status_message = "Could not determine script genre."
#                     final_status = JobStatus.FAILED
#                     raise ValueError(status_message)

#                 # Update status after genre determination (await DB call)
#                 await db_service.update_job(session, job_id, {
#                     "status": JobStatus.PROCESSING,
#                     "status_message": f"Genre determined: {determined_genre}. Generating topics...",
#                     "script_genre": determined_genre
#                 })
#                 await session.commit()

#                 # 4. Generate Topics (await async method which wraps sync call)
#                 logger.info(f"Generating topics for job {job_id} with genre '{determined_genre}'")
#                 generated_topics = await llm_service.generate_topics(job.transcript, determined_genre, topic_count=60)

#                 if generated_topics is not None:
#                     logger.info(f"Successfully generated {len(generated_topics)} topics for job {job_id}.")
#                     final_status = JobStatus.COMPLETED
#                     status_message = f"Successfully generated {len(generated_topics)} topics."
#                 else:
#                     status_message = "Failed to generate topics from LLM."
#                     final_status = JobStatus.FAILED

#                 # 5. Final Update within try block IF SUCCESSFUL (await DB call)
#                 update_data = {
#                     "status": final_status,
#                     "status_message": status_message,
#                     "script_genre": determined_genre,
#                     "topics": generated_topics
#                 }
#                 update_data_cleaned = {k: v for k, v in update_data.items() if v is not None or k in ['topics','script_genre']}
#                 if update_data_cleaned:
#                     await db_service.update_job(session, job_id, update_data_cleaned) # Use session
#                     await session.commit()
#                     logger.info(f"Final status update committed successfully for job {job_id}")

#         except Exception as e:
#             # --- Use simplified logging without exc_info ---
#             logger.error(f"Exception caught in generate_topics_task for job {job_id}: {str(e)}")
#             status_message = "Topic generation failed due to an internal error."
#             final_status = JobStatus.FAILED
#             try:
#                 await session.rollback()
#                 logger.info(f"Session rolled back for job {job_id} due to exception.")
#             except Exception as rb_err:
#                 logger.error(f"Error during session rollback for job {job_id}: {str(rb_err)}")

#             try:
#                  logger.warning(f"Attempting to mark job {job_id} as FAILED in DB after exception.")
#                  await db_service.update_job_status(session, job_id, JobStatus.FAILED, status_message)
#                  await session.commit()
#             except Exception as final_db_err:
#                  logger.error(f"CRITICAL: Failed even to update job {job_id} status to FAILED: {str(final_db_err)}")

#         finally:
#             # Ensure session is always closed (await close)
#             try:
#                 await session.close()
#                 logger.info(f"Session closed for job {job_id}")
#             except Exception as close_err:
#                  logger.error(f"Error closing session for job {job_id}: {str(close_err)}")
#         # --- END Manual Session Management ---


#         logger.info(f"Task generate_topics_task completing for job {job_id}. Final determined status: {final_status.value}")
#         # This return value is ignored by Celery due to ignore_result=True
#         return f"Job {job_id} processing finished with status {final_status.value}"

import logging
import json
from typing import List, Optional, Tuple
# --- Import Only Sync OpenAI client and Base Error ---
from openai import OpenAI, OpenAIError

# --- Database Imports for Sync ---
from sqlalchemy.orm import Session as SyncSession # Import synchronous Session
from app.database import SyncSessionLocal # Import synchronous Session factory

from app.celery_app import celery
from app.core.config import settings
from app.services.database_service import DatabaseService # Still need the service class
from app.models.video_job import JobStatus

logger = logging.getLogger(__name__)

# --- Initialize ONLY Sync client ---
sync_client: Optional[OpenAI] = None
if not settings.OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not found. LLM features will fail.")
else:
    sync_client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=120.0) # Use Sync client

# --- Constants (keep as before) ---
GENRE_DETERMINATION_PROMPT_TEMPLATE = """...""" # Keep prompt templates
TOPIC_GENERATION_PROMPT_TEMPLATE = """..."""


class LLMService:
    """Interacts with LLMs for script analysis and topic generation (SYNC Methods)."""

    # --- Kept SYNCHRONOUS ---
    def _call_openai_api_sync(self, prompt: str, model: str = "gpt-3.5-turbo") -> Optional[str]:
        """Helper function to call the OpenAI ChatCompletion API SYNCHRONOUSLY."""
        if not sync_client:
            logger.error("OpenAI sync client not initialized. Cannot call API.")
            return None
        try:
            logger.debug(f"Calling SYNC OpenAI API with model {model}. Prompt length: {len(prompt)}")
            response = sync_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant analyzing video scripts."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500,
            )
            result = response.choices[0].message.content
            logger.debug(f"Received SYNC response from OpenAI. Length: {len(result or '')}")
            return result.strip() if result else None
        except OpenAIError as e:
            logger.error(f"SYNC OpenAI API Error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling SYNC OpenAI API: {str(e)}")
            return None

    # --- Changed to SYNCHRONOUS (def, no await) ---
    def determine_genre(self, script_text: str) -> Optional[str]:
        """Determines the genre of the script using an LLM (via sync call)."""
        if not script_text:
            logger.warning("Cannot determine genre from empty script.")
            return None

        prompt = GENRE_DETERMINATION_PROMPT_TEMPLATE.format(script_text=script_text[:4000])
        genre = self._call_openai_api_sync(prompt, model="gpt-3.5-turbo")

        if genre and genre in [ # Keep genre list
            "Storytelling / Narrative", "Educational / Explainer", "Historical Fact / Analysis",
            "Current Events / News Commentary", "Product Review / Tutorial", "Opinion / Rant",
            "Comedy / Sketch", "Inspirational / Motivational", "Science / Technology Update",
            "Travel / Exploration", "Personal Vlog / Update"
        ]:
            logger.info(f"Determined genre: {genre}")
            return genre
        else:
            logger.warning(f"Could not determine a valid genre. LLM response: {genre}")
            return "Unknown"

    # --- Changed to SYNCHRONOUS (def, no await) ---
    def generate_topics(self, script_text: str, genre: str, topic_count: int = 10) -> Optional[List[str]]:
        """Generates related video topics using an LLM (via sync call)."""
        if not script_text or not genre:
            logger.warning("Cannot generate topics without script or genre.")
            return None

        prompt = TOPIC_GENERATION_PROMPT_TEMPLATE.format(
            script_text=script_text[:4000],
            genre=genre,
            topic_count=topic_count
        )
        model="gpt-3.5-turbo"
        raw_response = self._call_openai_api_sync(prompt, model=model)

        if not raw_response:
            logger.error("Failed to get response from LLM for topic generation.")
            return None

        try: # Keep JSON parsing logic
            json_start = raw_response.find('[')
            json_end = raw_response.rfind(']') + 1
            if json_start != -1 and json_end != -1:
                json_str = raw_response[json_start:json_end]
                topics = json.loads(json_str)
                if isinstance(topics, list) and all(isinstance(t, str) for t in topics):
                     if abs(len(topics) - topic_count) > topic_count * 0.5:
                         logger.warning(f"LLM returned {len(topics)} topics, expected around {topic_count}.")
                     logger.info(f"Successfully parsed {len(topics)} topics from LLM response.")
                     return topics[:topic_count]
                else:
                    logger.error(f"LLM response parsed but is not a list of strings: {topics}")
                    return None
            else:
                logger.error(f"Could not find JSON list in LLM response: {raw_response}")
                return None
        except json.JSONDecodeError as e:
             logger.error(f"Failed to decode JSON from LLM response: {str(e)}\nResponse snippet: {raw_response[:200]}")
             return None
        except Exception as e:
             logger.error(f"Error processing LLM topic response: {str(e)}\nResponse snippet: {raw_response[:200]}")
             return None


    # --- Celery Task Definition ---
    @staticmethod
    # --- Changed to def, kept ignore_result=True ---
    @celery.task(name="tasks.generate_topics", bind=True, ignore_result=True)
    def generate_topics_task(self, job_id: int): # Changed async def to def
        logger.info(f"Starting SYNC topic generation task for job_id: {job_id}")
        db_service = DatabaseService() # Instantiate service
        llm_service = LLMService()   # Instantiate service
        final_status = JobStatus.FAILED
        status_message = "Topic generation failed"
        generated_topics = None
        determined_genre = None

        # --- Use Sync Session ---
        session: SyncSession = SyncSessionLocal()
        try:
            # 1. Get job using SYNC method
            job = db_service.get_job_sync(session, job_id) # Use sync method
            if not job:
                raise ValueError(f"Job {job_id} not found.")
            if not job.transcript:
                raise ValueError(f"Job {job_id} has no transcript to process.")

            if job.status == JobStatus.COMPLETED and job.topics:
                logger.warning(f"Job {job_id} already has topics. Skipping generation.")
                final_status = JobStatus.COMPLETED
                status_message = "Topics already generated."
                generated_topics = job.topics
                determined_genre = job.script_genre
            else:
                # 2. Update status using SYNC method
                db_service.update_job_status_sync(session, job_id, JobStatus.PROCESSING, "Determining script genre...")
                session.commit() # Sync commit

                # 3. Determine Genre using SYNC method (NO await)
                determined_genre = llm_service.determine_genre(job.transcript)
                if not determined_genre or determined_genre == "Unknown":
                    status_message = "Could not determine script genre."
                    final_status = JobStatus.FAILED
                    raise ValueError(status_message)

                # Update status after genre determination using SYNC method
                db_service.update_job_sync(session, job_id, { # Use sync method
                    "status": JobStatus.PROCESSING,
                    "status_message": f"Genre determined: {determined_genre}. Generating topics...",
                    "script_genre": determined_genre
                })
                session.commit() # Sync commit

                # 4. Generate Topics using SYNC method (NO await)
                logger.info(f"Generating topics for job {job_id} with genre '{determined_genre}'")
                generated_topics = llm_service.generate_topics(job.transcript, determined_genre, topic_count=60) # Use correct topic_count

                if generated_topics is not None:
                    logger.info(f"Successfully generated {len(generated_topics)} topics for job {job_id}.")
                    final_status = JobStatus.COMPLETED
                    status_message = f"Successfully generated {len(generated_topics)} topics."
                else:
                    status_message = "Failed to generate topics from LLM."
                    final_status = JobStatus.FAILED

                # 5. Final Update within try block IF SUCCESSFUL using SYNC method
                update_data = {
                    "status": final_status,
                    "status_message": status_message,
                    "script_genre": determined_genre,
                    "topics": generated_topics
                }
                update_data_cleaned = {k: v for k, v in update_data.items() if v is not None or k in ['topics','script_genre']}
                if update_data_cleaned:
                    db_service.update_job_sync(session, job_id, update_data_cleaned) # Use sync method
                    session.commit() # Sync commit
                    logger.info(f"Final status update committed successfully for job {job_id}")

        except Exception as e:
            logger.error(f"Exception caught in generate_topics_task for job {job_id}: {str(e)}")
            status_message = "Topic generation failed due to an internal error."
            final_status = JobStatus.FAILED
            try:
                session.rollback() # Sync rollback
                logger.info(f"Session rolled back for job {job_id} due to exception.")
            except Exception as rb_err:
                logger.error(f"Error during session rollback for job {job_id}: {str(rb_err)}")

            # Attempt to update DB status to FAILED in a final try
            try:
                 logger.warning(f"Attempting to mark job {job_id} as FAILED in DB after exception.")
                 db_service.update_job_status_sync(session, job_id, JobStatus.FAILED, status_message) # Use sync method
                 session.commit() # Sync commit
            except Exception as final_db_err:
                 logger.error(f"CRITICAL: Failed even to update job {job_id} status to FAILED: {str(final_db_err)}")
                 session.rollback() # Sync rollback

        finally:
            # Ensure session is always closed
            try:
                session.close() # Sync close
                logger.info(f"Session closed for job {job_id}")
            except Exception as close_err:
                 logger.error(f"Error closing session for job {job_id}: {str(close_err)}")
        # --- END Sync Session Management ---

        logger.info(f"SYNC Task generate_topics_task completing for job {job_id}. Final determined status: {final_status.value}")
        # Return value is ignored by Celery anyway
        return f"Job {job_id} processing finished with status {final_status.value}"