import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("=" * 50)
    print("Video Title Generator - Database Setup")
    print("=" * 50)
    print()
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL not found in .env")
        print("   Please add your Neon DB connection string to .env")
        return 1
    
    print(f"Database: {database_url.split('@')[1].split('/')[0]}")
    print()
    
    # Test connection
    print("Testing connection...")
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        print("✅ Connected to database")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return 1
    
    # Check if schema already exists
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'users'
    """)
    table_exists = cur.fetchone()[0] > 0
    
    if table_exists:
        print()
        print("⚠️  Tables already exist!")
        response = input("Do you want to drop and recreate? (yes/no): ")
        
        if response.lower() != 'yes':
            print("Skipping schema creation.")
            conn.close()
            return 0
        
        print("Dropping existing tables...")
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        conn.commit()
    
    # Run schema
    print()
    print("Creating schema...")
    
    schema_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "schema.sql"
    )
    
    if not os.path.exists(schema_path):
        print(f"❌ Schema file not found: {schema_path}")
        conn.close()
        return 1
    
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    try:
        cur.execute(schema_sql)
        conn.commit()
        print("✅ Schema created successfully!")
    except Exception as e:
        print(f"❌ Schema creation failed: {e}")
        conn.rollback()
        conn.close()
        return 1
    
    # Verify
    print()
    print("Verifying installation...")
    
    cur.execute("""
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    table_count = cur.fetchone()[0]
    
    cur.execute("""
        SELECT COUNT(*) FROM pg_type WHERE typtype = 'e'
    """)
    enum_count = cur.fetchone()[0]
    
    cur.execute("""
        SELECT COUNT(*) FROM information_schema.views 
        WHERE table_schema = 'public'
    """)
    view_count = cur.fetchone()[0]
    
    print(f"  Tables created: {table_count}")
    print(f"  ENUM types created: {enum_count}")
    print(f"  Views created: {view_count}")
    
    if table_count >= 10 and enum_count >= 4:
        print()
        print("✅ Database setup complete!")
        print()
        print("You can now run the server:")
        print("  uvicorn app.main:app --reload")
    else:
        print()
        print("⚠️  Some objects may be missing. Please check schema.sql")
    
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
