
from pydantic import BaseModel, Field
from typing import List, Optional, Union
from datetime import datetime
from app.models.video_job import JobStatus # Import Enum

# --- Base Schema ---
# Common fields, used for inheritance
class JobBase(BaseModel):
    source_type: str
    source_value: str
    status: JobStatus = JobStatus.PENDING
    status_message: Optional[str] = None

# --- Schema for Creating a Job ---
# This might not be directly used if input comes from form-data,
# but good practice to define expected fields.
class JobCreate(BaseModel):
    source_type: str = Field(..., description="Type of input: 'prompt', 'youtube_url', 'audio_file'")
    # Use Union for fields that depend on source_type
    # FastAPI will handle these based on form data names in the router
    prompt_text: Optional[str] = None
    youtube_url: Optional[str] = None
    # audio_file: UploadFile # Handled separately in FastAPI endpoint

# --- Schema for Reading Job Details (API Response) ---
class Job(JobBase):
    id: int
    created_at: datetime
    updated_at: datetime
    transcript: Optional[str] = None
    transcript_fetched: bool = False
    script_genre: Optional[str] = None
    topics: Optional[List[str]] = None # Topics will be a list of strings

    class Config:
        from_attributes = True # Pydantic V2 way to enable ORM mode

# --- Schema for Basic Job Status Response ---
class JobStatusResponse(BaseModel):
    job_id: int
    status: JobStatus
    status_message: Optional[str] = None
    # Optionally include transcript/topics if available at this status check
    transcript: Optional[str] = None
    topics: Optional[List[str]] = None

# --- Schema for Job Submission Response ---
class JobSubmissionResponse(BaseModel):
    message: str = "Job submitted successfully"
    job_id: int
    status: JobStatus