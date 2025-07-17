#!/usr/bin/env python3
"""
Test script for document upload functionality
"""

import requests
import json
from pathlib import Path

# API configuration
BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_registration():
    """Test user registration"""
    print("🔐 Testing user registration...")
    
    registration_data = {
        "email": "test@example.com",
        "name": "Test User",
        "password": "testpassword123",
        "machine_name": "test-machine",
        "contradiction_tolerance": 0.5,
        "belief_sensitivity": "moderate"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=registration_data)
        print(f"Registration status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Registration successful: {result.get('email')}")
            return True
        else:
            print(f"❌ Registration failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Registration error: {str(e)}")
        return False

def test_login():
    """Test user login and get access token"""
    print("\n🔑 Testing user login...")
    
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Login status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            access_token = result.get('access_token')
            print(f"✅ Login successful, got token")
            return access_token
        else:
            print(f"❌ Login failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return None

def test_document_upload(access_token):
    """Test document upload"""
    print("\n📄 Testing document upload...")
    
    # Find a test file
    uploads_dir = Path("uploads")
    test_files = list(uploads_dir.glob("*.pdf"))
    
    if not test_files:
        print("❌ No PDF files found in uploads directory")
        return False
    
    test_file = test_files[0]
    print(f"📁 Using test file: {test_file.name}")
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    try:
        with open(test_file, 'rb') as f:
            files = {'files': (test_file.name, f, 'application/pdf')}
            response = requests.post(f"{BASE_URL}/documents/upload", files=files, headers=headers)
        
        print(f"Upload status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Upload successful!")
            print(f"📋 Response: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ Upload failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        return False

def main():
    """Main test function"""
    print("🧪 Document Upload Test")
    print("=" * 40)
    
    # Test registration (might fail if user exists, that's ok)
    test_registration()
    
    # Test login
    access_token = test_login()
    if not access_token:
        print("❌ Cannot proceed without access token")
        return
    
    # Test document upload
    success = test_document_upload(access_token)
    
    if success:
        print("\n✅ All tests passed! Document upload is working correctly.")
    else:
        print("\n❌ Document upload test failed.")

if __name__ == "__main__":
    main()