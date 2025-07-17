#!/usr/bin/env python3
"""
Test script for MinerU API integration
This script demonstrates how to use MinerU API to process documents
"""

import os
import requests
import time
import json
from pathlib import Path

# MinerU API configuration
MINERU_BASE_URL = "https://mineru.net/api/v4"
API_TOKEN = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiI1MzMwNzQ3MCIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc1MjcwNjI3NiwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiIiwib3BlbklkIjpudWxsLCJ1dWlkIjoiZDIzNDFlMTQtNGJlNS00ZDljLWIzOTMtMjBlOTk0Mzk2NjU1IiwiZW1haWwiOiJhZGViaXNpam9lQGdtYWlsLmNvbSIsImV4cCI6MTc1MzkxNTg3Nn0.2yVtNjaQvibVX7-Bf3ZKDkklKbCKXhrMTnJ13b7Hqbpq4IJ5YfGa-aM7yDC0LT6vfFZ8eG6RbGPTcWHttPFtUw"

# Headers for API requests
HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {API_TOKEN}',
    'Accept': '*/*'
}

def get_upload_url_for_file(filename: str, is_ocr: bool = True, data_id: str = None):
    """
    Get upload URL for a file using MinerU batch upload API
    """
    url = f"{MINERU_BASE_URL}/file-urls/batch"
    
    data = {
        "enable_formula": True,
        "language": "auto",  # Auto-detect language
        "enable_table": True,
        "files": [
            {
                "name": filename,
                "is_ocr": is_ocr,
                "data_id": data_id or f"test_{int(time.time())}"
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=HEADERS, json=data)
        print(f"Upload URL request status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Upload URL response: {json.dumps(result, indent=2)}")
            
            if result["code"] == 0:
                batch_id = result["data"]["batch_id"]
                file_urls = result["data"]["file_urls"]
                return batch_id, file_urls[0] if file_urls else None
            else:
                print(f"Failed to get upload URL: {result.get('msg', 'Unknown error')}")
                return None, None
        else:
            print(f"HTTP error: {response.status_code}")
            print(f"Response: {response.text}")
            return None, None
            
    except Exception as e:
        print(f"Error getting upload URL: {str(e)}")
        return None, None

def upload_file_to_url(file_path: Path, upload_url: str):
    """
    Upload file to the provided URL
    """
    try:
        with open(file_path, 'rb') as f:
            # Note: Don't set Content-Type header for file upload
            response = requests.put(upload_url, data=f)
            
        print(f"File upload status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"Successfully uploaded {file_path.name}")
            return True
        else:
            print(f"Failed to upload file: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error uploading file: {str(e)}")
        return False

def check_batch_results(batch_id: str, max_retries: int = 30, delay: int = 10):
    """
    Check batch processing results
    """
    url = f"{MINERU_BASE_URL}/extract-results/batch/{batch_id}"
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=HEADERS)
            
            if response.status_code == 200:
                result = response.json()
                print(f"Batch status check {attempt + 1}: {json.dumps(result, indent=2)}")
                
                if result["code"] == 0:
                    extract_results = result["data"]["extract_result"]
                    
                    for file_result in extract_results:
                        state = file_result.get("state")
                        file_name = file_result.get("file_name")
                        
                        if state == "done":
                            print(f"✅ File {file_name} processing completed!")
                            zip_url = file_result.get("full_zip_url")
                            if zip_url:
                                print(f"📦 Download URL: {zip_url}")
                            return True
                        elif state == "failed":
                            print(f"❌ File {file_name} processing failed:")
                            print(f"Error: {file_result.get('err_msg', 'Unknown error')}")
                            return False
                        elif state == "running":
                            progress = file_result.get("extract_progress", {})
                            extracted = progress.get("extracted_pages", 0)
                            total = progress.get("total_pages", 0)
                            print(f"🔄 Processing {file_name}: {extracted}/{total} pages")
                        else:
                            print(f"📋 File {file_name} status: {state}")
                
                print(f"Waiting {delay} seconds before next check...")
                time.sleep(delay)
            else:
                print(f"HTTP error checking results: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error checking batch results: {str(e)}")
            return False
    
    print(f"❌ Processing did not complete after {max_retries} attempts")
    return False

def process_document_with_mineru(file_path: Path):
    """
    Complete workflow to process a document with MinerU
    """
    print(f"🚀 Starting MinerU processing for: {file_path.name}")
    print("=" * 60)
    
    # Step 1: Get upload URL
    print("📡 Step 1: Getting upload URL...")
    batch_id, upload_url = get_upload_url_for_file(
        filename=file_path.name,
        is_ocr=True,
        data_id=f"test_{file_path.stem}_{int(time.time())}"
    )
    
    if not upload_url:
        print("❌ Failed to get upload URL")
        return False
    
    print(f"✅ Got upload URL and batch_id: {batch_id}")
    
    # Step 2: Upload file
    print("\n📤 Step 2: Uploading file...")
    if not upload_file_to_url(file_path, upload_url):
        print("❌ Failed to upload file")
        return False
    
    print("✅ File uploaded successfully")
    
    # Step 3: Wait and check results
    print("\n⏳ Step 3: Waiting for processing to complete...")
    print("This may take several minutes depending on file size...")
    
    success = check_batch_results(batch_id)
    
    if success:
        print("\n🎉 Document processing completed successfully!")
    else:
        print("\n💥 Document processing failed or timed out")
    
    return success

def list_available_files():
    """
    List available PDF files in uploads folder
    """
    uploads_dir = Path("uploads")
    if not uploads_dir.exists():
        print("❌ Uploads directory not found")
        return []
    
    pdf_files = list(uploads_dir.glob("*.pdf"))
    print(f"📁 Found {len(pdf_files)} PDF files in uploads folder:")
    
    for i, file_path in enumerate(pdf_files, 1):
        file_size = file_path.stat().st_size / (1024 * 1024)  # Size in MB
        print(f"  {i}. {file_path.name} ({file_size:.1f} MB)")
    
    return pdf_files

def main():
    """
    Main function to run the MinerU test
    """
    print("🧪 MinerU API Test Script")
    print("=" * 40)
    
    # List available files
    pdf_files = list_available_files()
    
    if not pdf_files:
        print("❌ No PDF files found in uploads folder")
        return
    
    # For testing, use the first PDF file
    test_file = pdf_files[0]
    print(f"\n🎯 Selected file for testing: {test_file.name}")
    
    # Check file size (MinerU has 200MB limit)
    file_size_mb = test_file.stat().st_size / (1024 * 1024)
    if file_size_mb > 200:
        print(f"⚠️  Warning: File size ({file_size_mb:.1f} MB) exceeds MinerU limit of 200MB")
        print("Please select a smaller file for testing")
        return
    
    # Process the document
    success = process_document_with_mineru(test_file)
    
    if success:
        print("\n✅ Test completed successfully!")
        print("You can now integrate this workflow into your document service.")
    else:
        print("\n❌ Test failed. Please check the error messages above.")

if __name__ == "__main__":
    main() 