#!/usr/bin/env python3
"""
Database migration script to add missing user_type_id column and fix schema issues
Run this script to migrate existing databases to the current schema
"""

import sqlite3
import os
from pathlib import Path

def migrate_database():
    """Migrate the database to current schema"""
    # Find the database file
    db_paths = [
        "ultra_pinnacle_studio/ultra_pinnacle.db",
        "ultra_pinnacle.db",
        "api_gateway/ultra_pinnacle.db"
    ]

    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break

    if not db_path:
        print("❌ Database file not found. Please ensure the database exists.")
        return False

    print(f"📊 Found database at: {db_path}")

    try:
        with sqlite3.connect(db_path) as conn:
            # Check if user_type_id column exists
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]

            if 'user_type_id' not in column_names:
                print("🔧 Adding user_type_id column to users table...")
                cursor.execute("ALTER TABLE users ADD COLUMN user_type_id INTEGER DEFAULT 1")

                # Update existing users to have a default user type
                cursor.execute("UPDATE users SET user_type_id = 1 WHERE user_type_id IS NULL")
                print("✅ Added user_type_id column and set default values")
            else:
                print("✅ user_type_id column already exists")

            # Check if user_types table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_types'")
            if not cursor.fetchone():
                print("🔧 Creating user_types table...")
                cursor.execute("""
                    CREATE TABLE user_types (
                        id INTEGER PRIMARY KEY,
                        name VARCHAR(50) NOT NULL UNIQUE,
                        display_name VARCHAR(100) NOT NULL,
                        description TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Insert default user types
                cursor.execute("""
                    INSERT INTO user_types (name, display_name, description) VALUES
                    ('free', 'Free Tier', 'Basic access with limited requests'),
                    ('premium', 'Premium Tier', 'Enhanced access with higher limits'),
                    ('enterprise', 'Enterprise Tier', 'Unlimited access for organizations')
                """)
                print("✅ Created user_types table with default types")
            else:
                print("✅ user_types table already exists")

            # Check if search_index table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='search_index'")
            if not cursor.fetchone():
                print("🔧 Creating search_index FTS5 table...")
                cursor.execute("""
                    CREATE VIRTUAL TABLE search_index USING fts5(
                        id UNINDEXED,
                        content_type UNINDEXED,
                        content_id UNINDEXED,
                        title,
                        content,
                        summary,
                        tags UNINDEXED,
                        metadata UNINDEXED,
                        language_code UNINDEXED,
                        created_at UNINDEXED,
                        updated_at UNINDEXED,
                        tokenize = "porter unicode61 remove_diacritics 2",
                        prefix = '2 3 4',
                        columnsize = 0
                    )
                """)
                print("✅ Created search_index FTS5 table")
            else:
                print("✅ search_index table already exists")

            # Check if search-related tables exist
            search_tables = [
                'search_queries', 'search_analytics', 'saved_searches',
                'search_suggestions', 'search_exports'
            ]

            for table in search_tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if not cursor.fetchone():
                    print(f"🔧 Creating {table} table...")
                    if table == 'search_queries':
                        cursor.execute("""
                            CREATE TABLE search_queries (
                                id INTEGER PRIMARY KEY,
                                user_id INTEGER,
                                query TEXT NOT NULL,
                                filters TEXT,
                                result_count INTEGER DEFAULT 0,
                                search_time REAL,
                                ip_address VARCHAR(45),
                                user_agent TEXT,
                                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                            )
                        """)
                    elif table == 'search_analytics':
                        cursor.execute("""
                            CREATE TABLE search_analytics (
                                id INTEGER PRIMARY KEY,
                                query TEXT NOT NULL UNIQUE,
                                result_count INTEGER DEFAULT 0,
                                avg_search_time REAL DEFAULT 0.0,
                                popularity_score REAL DEFAULT 0.0,
                                search_count INTEGER DEFAULT 0,
                                last_searched DATETIME DEFAULT CURRENT_TIMESTAMP,
                                first_searched DATETIME DEFAULT CURRENT_TIMESTAMP
                            )
                        """)
                    elif table == 'saved_searches':
                        cursor.execute("""
                            CREATE TABLE saved_searches (
                                id INTEGER PRIMARY KEY,
                                user_id INTEGER NOT NULL,
                                name VARCHAR(200) NOT NULL,
                                query TEXT NOT NULL,
                                filters TEXT,
                                description TEXT,
                                is_public BOOLEAN DEFAULT 0,
                                usage_count INTEGER DEFAULT 0,
                                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                                last_used DATETIME DEFAULT CURRENT_TIMESTAMP,
                                UNIQUE(user_id, name)
                            )
                        """)
                    elif table == 'search_suggestions':
                        cursor.execute("""
                            CREATE TABLE search_suggestions (
                                id INTEGER PRIMARY KEY,
                                suggestion VARCHAR(255) NOT NULL UNIQUE,
                                popularity INTEGER DEFAULT 0,
                                category VARCHAR(50),
                                last_used DATETIME DEFAULT CURRENT_TIMESTAMP,
                                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                            )
                        """)
                    elif table == 'search_exports':
                        cursor.execute("""
                            CREATE TABLE search_exports (
                                id VARCHAR PRIMARY KEY,
                                user_id INTEGER NOT NULL,
                                query TEXT NOT NULL,
                                filters TEXT,
                                format VARCHAR(20) NOT NULL,
                                status VARCHAR(20) DEFAULT 'pending',
                                file_path VARCHAR(500),
                                file_size INTEGER,
                                result_count INTEGER DEFAULT 0,
                                expires_at DATETIME,
                                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                                completed_at DATETIME
                            )
                        """)
                    print(f"✅ Created {table} table")
                else:
                    print(f"✅ {table} table already exists")

            # Create indexes for better performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_users_user_type_id ON users(user_type_id)",
                "CREATE INDEX IF NOT EXISTS idx_search_queries_user_time ON search_queries(user_id, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_search_queries_query ON search_queries(query)",
                "CREATE INDEX IF NOT EXISTS idx_saved_searches_user ON saved_searches(user_id, last_used)",
                "CREATE INDEX IF NOT EXISTS idx_search_exports_user ON search_exports(user_id, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_search_exports_status ON search_exports(status)"
            ]

            for index_sql in indexes:
                cursor.execute(index_sql)
                print(f"✅ Ensured index: {index_sql.split()[-1]}")

            conn.commit()
            print("🎉 Database migration completed successfully!")
            return True

    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Ultra Pinnacle Studio database migration...")
    success = migrate_database()
    if success:
        print("✅ Migration completed successfully!")
        print("💡 You can now run the application with: python start_server.py")
    else:
        print("❌ Migration failed. Please check the error messages above.")
        exit(1)