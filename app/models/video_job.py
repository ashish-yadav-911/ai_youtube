
# import datetime
# import enum
# from sqlalchemy import Boolean
# from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, JSON # Ensure JSON is imported

# #from sqlalchemy import (Column, Integer, String, DateTime, Enum, Text, ForeignKey, JSON) # Add JSON
# from sqlalchemy.orm import relationship
# from app.database import Base

# class JobStatus(enum.Enum):
#     PENDING = "PENDING"
#     PROCESSING = "PROCESSING"
#     EDITING = "EDITING" # Waiting for user edits
#     RENDERING = "RENDERING"
#     UPLOADING = "UPLOADING"
#     COMPLETED = "COMPLETED"
#     FAILED = "FAILED"

# class VideoJob(Base):
#     __tablename__ = "video_jobs"

#     id = Column(Integer, primary_key=True, index=True)
#     created_at = Column(DateTime, default=datetime.datetime.utcnow)
#     updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

#     source_type = Column(String, index=True) # e.g., "prompt", "youtube_url", "audio_file"
#     source_value = Column(Text) # The actual prompt, URL, or file path

#     transcript = Column(Text, nullable=True) # Store the generated transcript

#     status = Column(Enum(JobStatus), default=JobStatus.PENDING, index=True)
#     status_message = Column(String, nullable=True) # Store error messages or progress info

#     # --- Fields for Phase 2 ---
#     # Store sequence of media, timings, transitions, music etc. as JSON
#     editor_data = Column(JSON, nullable=True)
#     selected_music = Column(String, nullable=True) # Path or identifier for chosen music

#     # --- Fields for Phase 3 ---
#     render_path = Column(String, nullable=True) # Path to final rendered video
#     youtube_title = Column(String, nullable=True)
#     youtube_description = Column(Text, nullable=True)
#     youtube_tags = Column(JSON, nullable=True) # Store tags as a list
#     youtube_id = Column(String, nullable=True) # ID of the uploaded video
#     scheduled_upload_time = Column(DateTime, nullable=True)

#     # Relationship to generated topics (if storing topics separately)
#     # topics = relationship("Topic", back_populates="video_job") # Define Topic model later

#     def __repr__(self):
#         return f"<VideoJob(id={self.id}, status='{self.status.value}')>"

# # Make sure to import this model in app/models/__init__.py

import datetime
import enum
# Make sure Boolean is imported if you use it
from sqlalchemy import Boolean, Column, Integer, String, DateTime, Enum, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class JobStatus(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    EDITING = "EDITING" # Waiting for user edits
    RENDERING = "RENDERING"
    UPLOADING = "UPLOADING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class VideoJob(Base):
    __tablename__ = "video_jobs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    source_type = Column(String, index=True) # e.g., "prompt", "youtube_url", "audio_file"
    source_value = Column(Text) # The actual prompt, URL, or file path

    transcript = Column(Text, nullable=True) # Store the generated transcript
    # --- ADD THIS COLUMN BACK ---
    transcript_fetched = Column(Boolean, default=False, nullable=False) # Flag if transcript step is done

    status = Column(Enum(JobStatus), default=JobStatus.PENDING, index=True)
    status_message = Column(String, nullable=True) # Store error messages or progress info

    # --- ADD THESE COLUMNS BACK ---
    script_genre = Column(String, nullable=True) # Determined by LLM
    topics = Column(JSON, nullable=True) # Store list of generated topics

    # --- Fields for Phase 2 ---
    editor_data = Column(JSON, nullable=True)
    selected_music = Column(String, nullable=True) # Path or identifier for chosen music

    # --- Fields for Phase 3 ---
    render_path = Column(String, nullable=True) # Path to final rendered video
    youtube_title = Column(String, nullable=True)
    youtube_description = Column(Text, nullable=True)
    youtube_tags = Column(JSON, nullable=True) # Store tags as a list
    youtube_id = Column(String, nullable=True) # ID of the uploaded video
    scheduled_upload_time = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<VideoJob(id={self.id}, status='{self.status.value}')>"