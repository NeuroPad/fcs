"""
MinerU API Service for document processing
Replaces Docling for PDF and document processing
"""

import asyncio
import logging
import time
import requests
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class MinerUService:
    """Service for processing documents using MinerU API"""
    
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://mineru.net/api/v4"
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_token}',
            'Accept': '*/*'
        }
    
    async def get_upload_url(self, filename: str, is_ocr: bool = True, data_id: str = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Get upload URL for a file using MinerU batch upload API
        Returns: (batch_id, upload_url)
        """
        url = f"{self.base_url}/file-urls/batch"
        
        data = {
            "enable_formula": True,
            "language": "auto",  # Auto-detect language
            "enable_table": True,
            "extra_formats": ["html"],  # Get HTML in addition to markdown and json
            "files": [
                {
                    "name": filename,
                    "is_ocr": is_ocr,
                    "data_id": data_id or f"doc_{int(time.time())}"
                }
            ]
        }
        
        try:
            # Use asyncio to run the request in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(url, headers=self.headers, json=data)
            )
            
            logger.info(f"Upload URL request status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.debug(f"Upload URL response: {result}")
                
                if result["code"] == 0:
                    batch_id = result["data"]["batch_id"]
                    file_urls = result["data"]["file_urls"]
                    return batch_id, file_urls[0] if file_urls else None
                else:
                    logger.error(f"Failed to get upload URL: {result.get('msg', 'Unknown error')}")
                    return None, None
            else:
                logger.error(f"HTTP error: {response.status_code}, Response: {response.text}")
                return None, None
                
        except Exception as e:
            logger.error(f"Error getting upload URL: {str(e)}")
            return None, None
    
    async def upload_file(self, file_path: Path, upload_url: str) -> bool:
        """Upload file to the provided URL"""
        try:
            def _upload():
                with open(file_path, 'rb') as f:
                    # Don't set Content-Type header for file upload
                    response = requests.put(upload_url, data=f)
                return response
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, _upload)
            
            logger.info(f"File upload status: {response.status_code}")
            
            if response.status_code == 200:
                logger.info(f"Successfully uploaded {file_path.name}")
                return True
            else:
                logger.error(f"Failed to upload file: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return False
    
    async def check_processing_status(self, batch_id: str) -> Dict[str, Any]:
        """Check the processing status of a batch"""
        url = f"{self.base_url}/extract-results/batch/{batch_id}"
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(url, headers=self.headers)
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.debug(f"Batch status: {result}")
                
                if result["code"] == 0:
                    return result["data"]
                else:
                    logger.error(f"API error checking status: {result.get('msg', 'Unknown error')}")
                    return {"error": result.get('msg', 'Unknown error')}
            else:
                logger.error(f"HTTP error checking status: {response.status_code}")
                return {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error checking batch status: {str(e)}")
            return {"error": str(e)}
    
    async def wait_for_completion(self, batch_id: str, max_wait_time: int = 600, check_interval: int = 10) -> Dict[str, Any]:
        """
        Wait for document processing to complete
        Returns the final result or error after max_wait_time seconds
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status_data = await self.check_processing_status(batch_id)
            
            if "error" in status_data:
                return {"status": "error", "error": status_data["error"]}
            
            extract_results = status_data.get("extract_result", [])
            
            for file_result in extract_results:
                state = file_result.get("state")
                file_name = file_result.get("file_name")
                
                if state == "done":
                    logger.info(f"Processing completed for {file_name}")
                    return {
                        "status": "completed",
                        "file_name": file_name,
                        "zip_url": file_result.get("full_zip_url"),
                        "data_id": file_result.get("data_id")
                    }
                elif state == "failed":
                    error_msg = file_result.get("err_msg", "Unknown processing error")
                    logger.error(f"Processing failed for {file_name}: {error_msg}")
                    return {
                        "status": "failed",
                        "file_name": file_name,
                        "error": error_msg
                    }
                elif state == "running":
                    progress = file_result.get("extract_progress", {})
                    extracted = progress.get("extracted_pages", 0)
                    total = progress.get("total_pages", 0)
                    logger.info(f"Processing {file_name}: {extracted}/{total} pages")
                else:
                    logger.info(f"File {file_name} status: {state}")
            
            # Wait before next check
            await asyncio.sleep(check_interval)
        
        # Timeout
        logger.warning(f"Processing timed out after {max_wait_time} seconds")
        return {"status": "timeout", "error": f"Processing timed out after {max_wait_time} seconds"}
    
    async def download_and_extract_results(self, zip_url: str, output_dir: Path) -> Optional[Path]:
        """
        Download the result ZIP file and extract markdown content
        Returns path to the extracted markdown file
        """
        try:
            # Create output directory if it doesn't exist
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Download ZIP file
            def _download():
                response = requests.get(zip_url)
                return response
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, _download)
            
            if response.status_code != 200:
                logger.error(f"Failed to download results: {response.status_code}")
                return None
            
            # Save ZIP to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
                temp_zip.write(response.content)
                temp_zip_path = Path(temp_zip.name)
            
            try:
                # Extract ZIP file
                with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(output_dir)
                
                # Find the markdown file
                markdown_files = list(output_dir.glob("*.md"))
                if markdown_files:
                    markdown_path = markdown_files[0]
                    logger.info(f"Extracted markdown file: {markdown_path}")
                    return markdown_path
                else:
                    logger.warning("No markdown file found in extracted results")
                    return None
                    
            finally:
                # Clean up temporary ZIP file
                temp_zip_path.unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"Error downloading and extracting results: {str(e)}")
            return None
    
    async def process_document(self, file_path: Path, output_dir: Path, data_id: str = None) -> Dict[str, Any]:
        """
        Complete workflow to process a document with MinerU
        Returns processing result with markdown path or error
        """
        try:
            logger.info(f"Starting MinerU processing for: {file_path.name}")
            
            # Step 1: Get upload URL
            logger.info("Getting upload URL...")
            batch_id, upload_url = await self.get_upload_url(
                filename=file_path.name,
                is_ocr=True,
                data_id=data_id
            )
            
            if not upload_url:
                return {"status": "error", "error": "Failed to get upload URL"}
            
            logger.info(f"Got upload URL and batch_id: {batch_id}")
            
            # Step 2: Upload file
            logger.info("Uploading file...")
            if not await self.upload_file(file_path, upload_url):
                return {"status": "error", "error": "Failed to upload file"}
            
            logger.info("File uploaded successfully")
            
            # Step 3: Wait for processing
            logger.info("Waiting for processing to complete...")
            result = await self.wait_for_completion(batch_id)
            
            if result["status"] != "completed":
                return result
            
            # Step 4: Download and extract results
            logger.info("Downloading results...")
            zip_url = result["zip_url"]
            markdown_path = await self.download_and_extract_results(zip_url, output_dir)
            
            if not markdown_path:
                return {"status": "error", "error": "Failed to extract markdown content"}
            
            return {
                "status": "success",
                "markdown_path": str(markdown_path),
                "zip_url": zip_url,
                "file_name": result["file_name"],
                "data_id": result.get("data_id")
            }
            
        except Exception as e:
            logger.error(f"Error in MinerU processing: {str(e)}")
            return {"status": "error", "error": str(e)} 