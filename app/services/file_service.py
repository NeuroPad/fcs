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
from docling.datamodel.pipeline_options import AcceleratorDevice

logger = logging.getLogger(__name__)

IMAGE_RESOLUTION_SCALE = 2.0


class FileService:
    def __init__(
        self,
        upload_dir: Path,
        processed_files_dir: Path,
        image_rag_service=None,
    ):
        self.upload_dir = upload_dir
        self.processed_files_dir = processed_files_dir
        self.image_rag_service = image_rag_service

        # Create directories
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.processed_files_dir.mkdir(parents=True, exist_ok=True)

    def ensure_dir(self, path: Path) -> Path:
        """Ensure directory exists, create if it doesn't"""
        path.mkdir(parents=True, exist_ok=True)
        return path

    def clean_filename(self, filename: str) -> str:
        """Clean filename to remove spaces and special characters, ensuring only underscores between words while preserving extension"""
        # Split filename into name and extension
        name, extension = Path(filename).stem, Path(filename).suffix

        # Clean the name part
        clean_name = "".join("_" if not c.isalnum() else c for c in name)

        # Replace multiple underscores with single underscore
        while "__" in clean_name:
            clean_name = clean_name.replace("__", "_")

        # Remove leading/trailing underscores
        clean_name = clean_name.strip("_")

        # Combine with original extension
        return f"{clean_name}{extension}"

    async def save_upload_file(self, file: UploadFile) -> Path:
        """Save an uploaded file to the appropriate directory"""
        clean_name = self.clean_filename(file.filename)
        
        # Determine target directory based on file type
        if file.filename.endswith(".pdf"):
            target_dir = self.upload_dir
        else:
            target_dir = self.processed_files_dir
        
        # Ensure target directory exists
        self.ensure_dir(target_dir)
        file_path = target_dir / clean_name

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Saved file: {file_path}")
        return file_path

    async def process_single_pdf(self, pdf_path: Path) -> Dict:
        """Process a single PDF file following the original structure"""
        try:
            # Initialize options each time to ensure fresh state
            pipeline_options = PdfPipelineOptions()
            pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
            pipeline_options.generate_page_images = False  # Disable page images
            pipeline_options.generate_picture_images = True

            pipeline_options.accelerator_options.device = AcceleratorDevice.MPS
            pipeline_options.accelerator_options.num_threads = 8

            # Create converter with options
            doc_converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )

            start_time = time.time()

            # Convert the PDF
            conv_res = doc_converter.convert(pdf_path)

            # Create output directories
            doc_filename = conv_res.input.file.stem

            # Save markdown versions
            # md_filename = self.processed_files_dir / f"{doc_filename}-with-images.md"
            # self.ensure_dir(md_filename.parent)  # Ensure markdown dir exists
            # conv_res.document.save_as_markdown(md_filename, image_mode=ImageRefMode.EMBEDDED)

            md_ref_filename = self.processed_files_dir / f"{doc_filename}-with-refs.md"
            conv_res.document.save_as_markdown(
                md_ref_filename, image_mode=ImageRefMode.REFERENCED
            )

            end_time = time.time() - start_time

            logger.info(
                f"Document converted and figures exported in {end_time:.2f} seconds."
            )

            return {
                "pdf": str(pdf_path),
                # "markdown": str(md_filename),
                "markdown_with_refs": str(md_ref_filename),
                "processing_time": f"{end_time:.2f} seconds",
            }

        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {str(e)}")
            raise

    async def process_uploads(self) -> Dict:
        """Process all PDFs in the upload directory"""
        # Ensure upload directory exists
        self.ensure_dir(self.upload_dir)

        processed_files = []
        skipped_files = []
        start_time = time.time()

        pdf_files = list(self.upload_dir.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files to process")

        def is_already_processed(pdf_file: Path) -> bool:
            """Check if PDF has already been processed by looking for markdown files"""
            doc_filename = pdf_file.stem
            refs_md = self.processed_files_dir / f"{doc_filename}-with-refs.md"
            images_md = self.processed_files_dir / f"{doc_filename}-with-images.md"
            return refs_md.exists() and images_md.exists()

        for pdf_file in pdf_files:
            try:
                if is_already_processed(pdf_file):
                    logger.info(f"Skipping already processed file: {pdf_file}")
                    skipped_files.append(str(pdf_file))
                    continue

                result = await self.process_single_pdf(pdf_file)
                processed_files.append(result)
            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {str(e)}")
                continue

        end_time = time.time() - start_time

        return {
            "processing_time": f"{end_time:.2f} seconds",
            "processed_files": processed_files,
            "skipped_files": skipped_files,
        }

    async def delete_file_and_associated_files(self, filename: str) -> Dict:
        """Delete file and its associated files if any"""
        try:
            clean_name = self.clean_filename(filename)
            
            # Check both directories for the file
            pdf_path = self.upload_dir / clean_name
            processed_path = self.processed_files_dir / clean_name
            
            files_deleted = []
            
            if filename.endswith(".pdf"):
                # Handle PDF file deletion with associated files
                if not pdf_path.exists():
                    raise FileNotFoundError(f"PDF file {filename} not found")
                
                doc_filename = pdf_path.stem
                md_with_images = self.processed_files_dir / f"{doc_filename}-with-images.md"
                md_with_refs = self.processed_files_dir / f"{doc_filename}-with-refs.md"
                artifacts_dir = self.processed_files_dir / f"{doc_filename}-with-refs_artifacts"

                # Delete PDF and associated files
                if pdf_path.exists():
                    pdf_path.unlink()
                    files_deleted.append(str(pdf_path))

                if md_with_images.exists():
                    md_with_images.unlink()
                    files_deleted.append(str(md_with_images))

                if md_with_refs.exists():
                    md_with_refs.unlink()
                    files_deleted.append(str(md_with_refs))

                if artifacts_dir.exists():
                    for file in artifacts_dir.glob("*"):
                        file.unlink()
                        files_deleted.append(str(file))
                    artifacts_dir.rmdir()
                    files_deleted.append(str(artifacts_dir))
            else:
                # Handle non-PDF file deletion
                if not processed_path.exists():
                    raise FileNotFoundError(f"File {filename} not found")
                
                processed_path.unlink()
                files_deleted.append(str(processed_path))

            return {
                "status": "success",
                "message": f"Deleted {len(files_deleted)} files",
                "deleted_files": files_deleted,
            }

        except Exception as e:
            logger.error(f"Error deleting files for {filename}: {str(e)}")
            raise

    async def get_any_file(self, filename: str) -> Path:
        """Get file path if it exists, serving PDFs from upload_dir and other formats from processed_files_dir"""
        clean_name = self.clean_filename(filename)
        
        # Determine source directory based on file type
        if filename.endswith('.pdf'):
            file_path = self.upload_dir / clean_name
        else:
            file_path = self.processed_files_dir / clean_name

        if not file_path.exists():
            raise FileNotFoundError(f"File {filename} not found")

        return file_path

    async def get_uploaded_files(self) -> List[Dict]:
        """Get list of all uploaded files with their metadata and indexing status"""
        try:
            self.ensure_dir(self.upload_dir)
            self.ensure_dir(self.processed_files_dir)

            files_info = []
            
            # Get PDF files from upload directory
            pdf_files = list(self.upload_dir.glob("*.pdf"))
            
            # Get other files from processed directory (excluding markdown files from PDFs)
            other_files = [
                f for f in self.processed_files_dir.glob("*")
                if not (f.name.endswith("-with-refs.md") or 
                       f.name.endswith("-with-images.md") or 
                       f.name.endswith("_artifacts"))
            ]

            # Process PDF files
            for pdf_file in pdf_files:
                doc_filename = pdf_file.stem
                refs_md = self.processed_files_dir / f"{doc_filename}-with-refs.md"
                images_md = self.processed_files_dir / f"{doc_filename}-with-images.md"
                is_processed = refs_md.exists() and images_md.exists()

                stats = pdf_file.stat()
                suffix = "-with-refs_artifacts"
                new_file_name = doc_filename + suffix
                images_indexed = (
                    self.image_rag_service.has_indexed_images(new_file_name)
                    if self.image_rag_service
                    else False
                )

                files_info.append({
                    "filename": pdf_file.name,
                    "uploadDate": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stats.st_mtime)),
                    "size": stats.st_size,
                    "isProcessed": is_processed,
                    "imagesIndexed": images_indexed,
                    "knowledgeBaseIndexed": False,
                    "status": self._get_status(is_processed, images_indexed),
                    "path": str(pdf_file),
                    "type": "pdf"
                })

            # Process other files
            for other_file in other_files:
                stats = other_file.stat()
                files_info.append({
                    "filename": other_file.name,
                    "uploadDate": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stats.st_mtime)),
                    "size": stats.st_size,
                    "isProcessed": True,  # Non-PDF files are considered processed by default
                    "imagesIndexed": False,
                    "knowledgeBaseIndexed": False,
                    "status": "Processed",
                    "path": str(other_file),
                    "type": "other"
                })

            return sorted(files_info, key=lambda x: x["uploadDate"], reverse=True)

        except Exception as e:
            logger.error(f"Error reading uploaded files: {str(e)}")
            raise

    def _get_status(self, is_processed: bool, images_indexed: bool) -> str:
        """Helper method to determine status based on processing and indexing states"""
        if images_indexed:
            return "Image Indexed"
        elif is_processed:
            return "Processed"
        return "Pending"
