from pathlib import Path
from fastapi import UploadFile, HTTPException
from datetime import datetime
from typing import Optional

from app.schemas import PageRange
from app.services.pdf_processor import PDFProcessor

# Define the folder for storing chat images
CHAT_IMAGES_DIR = Path("chat_images")
CHAT_IMAGES_DIR.mkdir(exist_ok=True)


async def save_chat_image(image: Optional[UploadFile]) -> Optional[str]:
    if not image:
        return None
    image_path = CHAT_IMAGES_DIR / f"{datetime.utcnow().timestamp()}_{image.filename}"
    with open(image_path, "wb") as buffer:
        buffer.write(await image.read())
    return str(image_path)


async def process_file_upload(file: UploadFile, page_range: PageRange) -> str:
    content = await file.read()

    if file.filename.endswith(".pdf"):
        return PDFProcessor.process_pdf(
            content,
            start_page=None if page_range.all_pages else page_range.start,
            end_page=None if page_range.all_pages else page_range.end,
        )
    elif file.filename.endswith(".txt"):
        return content.decode("utf-8")
    else:
        raise HTTPException(400, "Unsupported file format")
