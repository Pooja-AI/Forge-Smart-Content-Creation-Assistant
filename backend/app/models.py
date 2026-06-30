from pydantic import BaseModel, Field
from typing import Optional


class ContentRequest(BaseModel):
    topic: str = Field(..., description="Topic or content request from the user")
    content_type: str = Field("blog", description="blog | article | social_post | marketing_copy | landing_page")
    tone: str = Field("professional, engaging", description="Desired tone")
    keywords: list[str] = Field(default_factory=list, description="Seed SEO keywords")
    llm_provider: Optional[str] = Field(None, description="Override default LLM provider: ollama|gemini|openai_compatible")


class FeedbackRequest(BaseModel):
    job_id: str
    section_edits: Optional[str] = None
    approve: bool = True


class IngestRequest(BaseModel):
    texts: list[str]
    source: str = "user_upload"
