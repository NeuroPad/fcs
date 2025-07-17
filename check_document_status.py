#!/usr/bin/env python3
"""
Check document processing status
"""

import sqlite3
from pathlib import Path

def check_document_status():
    """Check the status of uploaded documents"""
    print("📋 Checking Document Processing Status")
    print("=" * 50)
    
    # Connect to database
    db_path = Path("memduo.db")
    if not db_path.exists():
        print("❌ Database file not found")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get recent documents
        cursor.execute("""
            SELECT id, filename, status, markdown_path, error_message, created_at, processed_at
            FROM documents 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        
        documents = cursor.fetchall()
        
        if not documents:
            print("📭 No documents found")
            return
        
        print(f"📄 Found {len(documents)} recent documents:")
        print()
        
        for doc in documents:
            doc_id, filename, status, markdown_path, error_message, created_at, processed_at = doc
            
            print(f"🆔 Document ID: {doc_id}")
            print(f"📄 Filename: {filename}")
            print(f"📊 Status: {status}")
            print(f"📝 Markdown Path: {markdown_path or 'None'}")
            print(f"⏰ Created: {created_at}")
            print(f"✅ Processed: {processed_at or 'Not processed'}")
            
            if error_message:
                print(f"❌ Error: {error_message}")
            
            # Check if markdown file exists
            if markdown_path:
                markdown_file = Path(markdown_path)
                if markdown_file.exists():
                    file_size = markdown_file.stat().st_size
                    print(f"📄 Markdown file exists ({file_size} bytes)")
                    
                    # Show first few lines
                    try:
                        with open(markdown_file, 'r', encoding='utf-8') as f:
                            content = f.read(200)
                        print(f"📝 Content preview: {content[:100]}...")
                    except Exception as e:
                        print(f"⚠️  Could not read markdown file: {e}")
                else:
                    print(f"❌ Markdown file not found at {markdown_path}")
            
            print("-" * 40)
            
    except Exception as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_document_status()