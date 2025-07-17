#!/usr/bin/env python3
"""
Test script for document upload endpoint
"""

import requests
import json
from pathlib import Path

def test_upload_endpoint():
    """Test the document upload endpoint"""
    print("🧪 Testing Document Upload Endpoint")
    print("=" * 50)
    
    # API endpoint
    base_url = "http://localhost:8000"
    upload_url = f"{base_url}/api/v1/documents/upload"
    
    # Find a test PDF file
    uploads_dir = Path("uploads")
    pdf_files = list(uploads_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found in uploads directory")
        return False
    
    test_file = pdf_files[0]
    print(f"📄 Using test file: {test_file.name}")
    
    # First, let's try to register a user and get a token
    print("\n🔐 Step 1: Creating test user and getting token...")
    
    # Register user
    register_data = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    try:
        register_response = requests.post(f"{base_url}/api/v1/auth/register", json=register_data)
        print(f"Register response: {register_response.status_code}")
        
        if register_response.status_code == 200:
            print("✅ User registered successfully")
        elif register_response.status_code == 400:
            print("ℹ️  User already exists, proceeding with login")
        else:
            print(f"❌ Registration failed: {register_response.text}")
    except Exception as e:
        print(f"❌ Registration error: {str(e)}")
    
    # Login to get token
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    try:
        login_response = requests.post(f"{base_url}/api/v1/auth/login", json=login_data)
        print(f"Login response: {login_response.status_code}")
        
        if login_response.status_code == 200:
            token_data = login_response.json()
            access_token = token_data.get("access_token")
            print("✅ Login successful, got access token")
        else:
            print(f"❌ Login failed: {login_response.text}")
            return False
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return False
    
    # Test file upload
    print("\n📤 Step 2: Testing file upload...")
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    try:
        with open(test_file, 'rb') as f:
            files = {'files': (test_file.name, f, 'application/pdf')}
            
            upload_response = requests.post(upload_url, headers=headers, files=files)
            print(f"Upload response status: {upload_response.status_code}")
            
            if upload_response.status_code == 200:
                response_data = upload_response.json()
                print("✅ Upload successful!")
                print(f"📋 Response: {json.dumps(response_data, indent=2)}")
                
                # Check if document was queued for processing
                if response_data and len(response_data) > 0:
                    document = response_data[0]
                    status = document.get('status')
                    print(f"📊 Document status: {status}")
                    
                    if status == 'processing':
                        print("🔄 Document queued for MinerU processing")
                        return True
                    elif status == 'uploaded':
                        print("⚠️  Document uploaded but not processed (MinerU unavailable)")
                        return False
                    elif status == 'failed':
                        error_msg = document.get('error_message', 'Unknown error')
                        print(f"❌ Document processing failed: {error_msg}")
                        return False
                    else:
                        print(f"ℹ️  Document status: {status}")
                        return True
                else:
                    print("❌ No document data in response")
                    return False
            else:
                print(f"❌ Upload failed: {upload_response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_upload_endpoint()
    
    if success:
        print("\n🎉 Upload endpoint test PASSED!")
    else:
        print("\n💥 Upload endpoint test FAILED!")