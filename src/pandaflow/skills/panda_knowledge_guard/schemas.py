from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=500)
    language: Literal["zh", "en"] = "zh"
