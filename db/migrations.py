from sqlalchemy import create_engine, text
from db.session import SQLALCHEMY_DATABASE_URL

def run_migrations():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    # Add new columns to users table if they don't exist
    with engine.connect() as conn:
        # Check if columns exist
        result = conn.execute(text("PRAGMA table_info(users)"))
        columns = [row[1] for row in result.fetchall()]
        
        # Add machine_name column if it doesn't exist
        if 'machine_name' not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN machine_name VARCHAR"))
        
        # Add contradiction_tolerance column if it doesn't exist
        if 'contradiction_tolerance' not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN contradiction_tolerance INTEGER"))
        
        # Add belief_sensitivity column if it doesn't exist
        if 'belief_sensitivity' not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN belief_sensitivity VARCHAR"))
        
        conn.commit()

def add_nodes_referenced_column():
    """Migration to add nodes_referenced column to chat_messages table"""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    # Add the new column with SQL
    with engine.connect() as conn:
        try:
            # Check if column already exists (SQLite specific)
            result = conn.execute(text("PRAGMA table_info(chat_messages)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'nodes_referenced' not in columns:
                # Add the column if it doesn't exist
                conn.execute(text("ALTER TABLE chat_messages ADD COLUMN nodes_referenced TEXT"))
                conn.commit()
                print("Successfully added nodes_referenced column to chat_messages table")
            else:
                print("nodes_referenced column already exists in chat_messages table")
                
        except Exception as e:
            print(f"Error adding nodes_referenced column: {e}")
            conn.rollback()