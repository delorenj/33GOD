from pydantic import BaseModel
from typing import List, Optional

class Sentence(BaseModel):
    text: str
    speaker_name: Optional[str] = None
    start_time: Optional[float] = None

class TranscriptData(BaseModel):
    id: str
    title: str
    date: str
    sentences: List[Sentence]
