# services/file_service.py
import logging
import time
from pathlib import Path
import shutil
from typing import List, Dict
from fastapi import UploadFile

from docling_core.types.doc import ImageRefMode, PictureItem, TableItem
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

logger = logging.getLogger(__name__)

IMAGE_RESOLUTION_SCALE = 2.0


class PDFService:
    def __init__(self, upload_dir: Path, processed_dir: Path, markdown_dir: Path):
        self.upload_dir = upload_dir
        self.processed_dir = processed_dir
        self.markdown_dir = markdown_dir

        # Create directories
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.markdown_dir.mkdir(parents=True, exist_ok=True)

    def clean_filename(self, filename: str) -> str:
        """Clean filename to remove spaces and special characters"""
        clean_name = filename.replace(" ", "_")
        clean_name = "".join(c for c in clean_name if c.isalnum() or c in "_-.")
        return clean_name

    async def save_upload_file(self, file: UploadFile) -> Path:
        """Save an uploaded file to the upload directory"""
        if not file.filename.endswith(".pdf"):
            raise ValueError(f"File {file.filename} is not a PDF")

        clean_name = self.clean_filename(file.filename)
        file_path = self.upload_dir / clean_name

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Saved upload: {file_path}")
        return file_path

    async def process_single_pdf(self, pdf_path: Path) -> Dict:
        """Process a single PDF file following the original structure"""
        try:
            # Initialize options each time to ensure fresh state
            pipeline_options = PdfPipelineOptions()
            pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
            pipeline_options.generate_page_images = True
            pipeline_options.generate_picture_images = True

            # Create converter with options
            doc_converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )

            start_time = time.time()

            # Convert the PDF
            conv_res = doc_converter.convert(pdf_path)

            # Create output directory
            doc_filename = conv_res.input.file.stem
            output_dir = self.processed_dir / doc_filename
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save page images
            page_images = []
            for page_no, page in conv_res.document.pages.items():
                page_no = page.page_no
                page_image_filename = output_dir / f"{doc_filename}-{page_no}.png"
                with page_image_filename.open("wb") as fp:
                    page.image.pil_image.save(fp, format="PNG")
                page_images.append(str(page_image_filename))

            # Save images of figures and tables
            table_counter = 0
            picture_counter = 0
            table_paths = []
            figure_paths = []

            for element, _level in conv_res.document.iterate_items():
                if isinstance(element, TableItem):
                    table_counter += 1
                    element_image_filename = (
                        output_dir / f"{doc_filename}-table-{table_counter}.png"
                    )
                    with element_image_filename.open("wb") as fp:
                        element.get_image(conv_res.document).save(fp, "PNG")
                    table_paths.append(str(element_image_filename))

                if isinstance(element, PictureItem):
                    picture_counter += 1
                    element_image_filename = (
                        output_dir / f"{doc_filename}-picture-{picture_counter}.png"
                    )
                    with element_image_filename.open("wb") as fp:
                        element.get_image(conv_res.document).save(fp, "PNG")
                    figure_paths.append(str(element_image_filename))

            # Save markdown versions
            md_filename = self.markdown_dir / f"{doc_filename}-with-images.md"
            conv_res.document.save_as_markdown(
                md_filename, image_mode=ImageRefMode.EMBEDDED
            )

            md_ref_filename = self.markdown_dir / f"{doc_filename}-with-refs.md"
            conv_res.document.save_as_markdown(
                md_ref_filename, image_mode=ImageRefMode.REFERENCED
            )

            end_time = time.time() - start_time

            logger.info(
                f"Document converted and figures exported in {end_time:.2f} seconds."
            )

            return {
                "pdf": str(pdf_path),
                "markdown": str(md_filename),
                "markdown_with_refs": str(md_ref_filename),
                "images_dir": str(output_dir),
                "page_images": page_images,
                "table_images": table_paths,
                "figure_images": figure_paths,
                "processing_time": f"{end_time:.2f} seconds",
            }

        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {str(e)}")
            raise

    async def process_uploads(self) -> Dict:
        """Process all PDFs in the upload directory"""
        processed_files = []
        start_time = time.time()

        pdf_files = list(self.upload_dir.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files to process")

        for pdf_file in pdf_files:
            try:
                result = await self.process_single_pdf(pdf_file)
                processed_files.append(result)
            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {str(e)}")
                continue

        end_time = time.time() - start_time

        return {
            "processing_time": f"{end_time:.2f} seconds",
            "processed_files": processed_files,
        }
