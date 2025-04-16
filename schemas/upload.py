from pydantic import BaseModel, Field
from typing import Optional, Union, List


class PageRange(BaseModel):
    start: Optional[int] = None
    end: Optional[int] = None
    all_pages: bool = False


class FileUpload(BaseModel):
    page_range: PageRange = Field(default=PageRange(all_pages=True))
