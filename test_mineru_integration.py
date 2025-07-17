#!/usr/bin/env python3
"""
Test script for MinerU integration with DocumentService
"""

import asyncio
from pathlib import Path
from app.services.mineru_service import MinerUService
from app.core.config import settings

async def test_mineru_integration():
    """Test MinerU service integration"""
    print("🧪 Testing MinerU Integration")
    print("=" * 50)
    
    # Check if API token is configured
    if not settings.MINERU_API_TOKEN:
        print("❌ MinerU API token not configured in settings")
        return False
    
    print(f"✅ MinerU API token configured")
    print(f"🔑 Token (first 50 chars): {settings.MINERU_API_TOKEN[:50]}...")
    
    # Initialize MinerU service
    mineru_service = MinerUService(settings.MINERU_API_TOKEN)
    print("✅ MinerU service initialized")
    
    # Find a test PDF file
    uploads_dir = Path("uploads")
    pdf_files = list(uploads_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found in uploads directory")
        return False
    
    test_file = pdf_files[0]
    print(f"📄 Using test file: {test_file.name}")
    
    # Check file size
    file_size_mb = test_file.stat().st_size / (1024 * 1024)
    if file_size_mb > 200:
        print(f"⚠️  File too large ({file_size_mb:.1f} MB) - selecting smaller file")
        for pdf_file in pdf_files:
            size_mb = pdf_file.stat().st_size / (1024 * 1024)
            if size_mb <= 200:
                test_file = pdf_file
                file_size_mb = size_mb
                break
        else:
            print("❌ No suitable PDF files found (all exceed 200MB limit)")
            return False
    
    print(f"📊 File size: {file_size_mb:.1f} MB (within limit)")
    
    # Create output directory
    output_dir = uploads_dir / f"test_mineru_output_{int(asyncio.get_event_loop().time())}"
    output_dir.mkdir(exist_ok=True)
    
    print(f"📁 Output directory: {output_dir}")
    
    # Test the processing
    print("\n🚀 Starting MinerU processing test...")
    try:
        result = await mineru_service.process_document(
            file_path=test_file,
            output_dir=output_dir,
            data_id=f"integration_test_{int(asyncio.get_event_loop().time())}"
        )
        
        print(f"\n📋 Processing result:")
        print(f"  Status: {result['status']}")
        
        if result["status"] == "success":
            print(f"  ✅ Markdown file: {result['markdown_path']}")
            print(f"  📦 ZIP URL: {result.get('zip_url', 'N/A')}")
            
            # Check if markdown file exists
            markdown_path = Path(result['markdown_path'])
            if markdown_path.exists():
                file_size = markdown_path.stat().st_size
                print(f"  📄 Markdown file size: {file_size} bytes")
                
                # Read first few lines
                with open(markdown_path, 'r', encoding='utf-8') as f:
                    content = f.read(500)  # First 500 characters
                print(f"  📝 Content preview:\n{content[:200]}...")
                
                print("\n🎉 Integration test PASSED!")
                return True
            else:
                print(f"  ❌ Markdown file not found at {markdown_path}")
                return False
        else:
            print(f"  ❌ Processing failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Integration test failed with exception: {str(e)}")
        return False

async def main():
    """Main test function"""
    success = await test_mineru_integration()
    
    if success:
        print("\n✅ All tests passed! MinerU integration is working correctly.")
        print("You can now use MinerU for document processing in your application.")
    else:
        print("\n❌ Integration test failed. Please check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())