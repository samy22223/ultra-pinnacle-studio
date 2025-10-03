"""
Search models and indexing for Ultra Pinnacle AI Studio
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, UniqueConstraint, Index
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone
from .logging_config import logger

Base = declarative_base()

# Note: SearchIndex is a virtual FTS5 table created manually in create_search_tables()
# It cannot be a SQLAlchemy model due to FTS5 virtual table limitations

class SearchQuery(Base):
    """Tracks search queries for analytics and history"""
    __tablename__ = "search_queries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=True)  # Null for anonymous searches
    query = Column(Text, nullable=False)
    filters = Column(JSON, default=dict)  # Applied filters
    result_count = Column(Integer, default=0)
    search_time = Column(Float)  # Time taken in seconds
    ip_address = Column(String(45))  # IPv4/IPv6
    user_agent = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_search_queries_user_time', 'user_id', 'created_at'),
        Index('idx_search_queries_query', 'query'),
    )

class SearchAnalytics(Base):
    """Analytics for search queries and performance"""
    __tablename__ = "search_analytics"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False, unique=True)
    result_count = Column(Integer, default=0)
    avg_search_time = Column(Float, default=0.0)
    popularity_score = Column(Float, default=0.0)  # Calculated popularity score
    search_count = Column(Integer, default=0)
    last_searched = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    first_searched = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class SavedSearch(Base):
    """User-saved searches"""
    __tablename__ = "saved_searches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    query = Column(Text, nullable=False)
    filters = Column(JSON, default=dict)
    description = Column(Text)
    is_public = Column(Integer, default=0)  # 0=private, 1=public
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_used = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='unique_user_search_name'),
        Index('idx_saved_searches_user', 'user_id', 'last_used'),
    )

class SearchSuggestion(Base):
    """Autocomplete suggestions"""
    __tablename__ = "search_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    suggestion = Column(String(255), nullable=False, unique=True)
    popularity = Column(Integer, default=0)
    category = Column(String(50))  # 'query', 'tag', 'user', 'topic'
    last_used = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_suggestions_popularity', 'popularity', 'last_used'),
        Index('idx_suggestions_category', 'category'),
    )

class SearchFacet(Base):
    """Dynamic facets for search results"""
    __tablename__ = "search_facets"

    id = Column(Integer, primary_key=True, index=True)
    facet_name = Column(String(100), nullable=False)  # 'content_type', 'user_type', 'language', etc.
    facet_value = Column(String(255), nullable=False)
    facet_count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('facet_name', 'facet_value', name='unique_facet'),
        Index('idx_facets_name_count', 'facet_name', 'facet_count'),
    )

class SearchExport(Base):
    """Search result exports"""
    __tablename__ = "search_exports"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    query = Column(Text, nullable=False)
    filters = Column(JSON, default=dict)
    format = Column(String(20), nullable=False)  # 'json', 'csv', 'pdf'
    status = Column(String(20), default="pending")  # 'pending', 'processing', 'completed', 'failed'
    file_path = Column(String(500))
    file_size = Column(Integer)
    result_count = Column(Integer, default=0)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime)

    __table_args__ = (
        Index('idx_search_exports_user', 'user_id', 'created_at'),
        Index('idx_search_exports_status', 'status'),
    )

def create_search_tables(engine):
    """Create search-related tables including FTS5 virtual table"""
    try:
        # Create regular tables
        Base.metadata.create_all(bind=engine)

        # Create FTS5 virtual table manually using raw sqlite3
        import sqlite3
        from sqlalchemy import text

        db_path = engine.url.database
        if db_path and db_path != ":memory:":
            with sqlite3.connect(db_path) as conn:
                # Drop existing FTS table if it exists
                try:
                    conn.execute("DROP TABLE IF EXISTS search_index")
                except:
                    pass  # Table might not exist

                # Create FTS5 virtual table with proper configuration
                conn.execute("""
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

                conn.commit()

        logger.info("Search tables created successfully")

    except Exception as e:
        logger.error(f"Error creating search tables: {e}")
        raise

def init_search_data(db_session):
    """Initialize search data by indexing existing content"""
    try:
        from .database import Conversation, Message, CollaborativeDocument, HelpArticle, User
        from pathlib import Path
        import json

        logger.info("Initializing search index with existing data...")

        # Index conversations and messages
        conversations = db_session.query(Conversation).all()
        for conv in conversations:
            messages = db_session.query(Message).filter(Message.conversation_id == conv.id).all()
            content = " ".join([msg.content for msg in messages])

            # Insert into search index
            db_session.execute("""
                INSERT INTO search_index (id, content_type, content_id, title, content, summary, metadata, language_code, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"conv_{conv.id}",
                "conversation",
                conv.id,
                conv.title or "Untitled Conversation",
                content,
                content[:200] + "..." if len(content) > 200 else content,
                json.dumps({
                    "user_id": conv.created_by,
                    "is_public": conv.is_public,
                    "model": conv.model,
                    "message_count": len(messages)
                }),
                "en",  # Default language
                conv.created_at.isoformat(),
                conv.updated_at.isoformat()
            ))

        # Index collaborative documents
        documents = db_session.query(CollaborativeDocument).all()
        for doc in documents:
            db_session.execute("""
                INSERT INTO search_index (id, content_type, content_id, title, content, summary, metadata, language_code, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"doc_{doc.id}",
                "document",
                doc.id,
                doc.title,
                doc.content,
                doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                json.dumps({
                    "user_id": doc.created_by,
                    "document_type": doc.document_type,
                    "language": doc.language,
                    "version": doc.version
                }),
                doc.language or "en",
                doc.created_at.isoformat(),
                doc.updated_at.isoformat()
            ))

        # Index help articles
        help_articles = db_session.query(HelpArticle).all()
        for article in help_articles:
            full_content = f"{article.title} {article.summary or ''} {article.content}"
            db_session.execute("""
                INSERT INTO search_index (id, content_type, content_id, title, content, summary, tags, metadata, language_code, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"help_{article.id}",
                "help",
                article.id,
                article.title,
                full_content,
                article.summary or article.content[:200] + "...",
                json.dumps(article.tags or []),
                json.dumps({
                    "category_id": article.category_id,
                    "difficulty_level": article.difficulty_level,
                    "view_count": article.view_count
                }),
                "en",  # Default language
                article.created_at.isoformat(),
                article.updated_at.isoformat()
            ))

        # Index encyclopedia articles
        encyclopedia_dir = Path("encyclopedia")
        if encyclopedia_dir.exists():
            for md_file in encyclopedia_dir.rglob("*.md"):
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Extract title from first line
                    lines = content.split('\n')
                    title = "Untitled"
                    if lines and lines[0].startswith('#'):
                        title = lines[0].lstrip('#').strip()

                    # Create relative path as ID
                    rel_path = md_file.relative_to(encyclopedia_dir)
                    article_id = str(rel_path).replace('.md', '').replace('/', '_')

                    db_session.execute("""
                        INSERT INTO search_index (id, content_type, content_id, title, content, summary, metadata, language_code, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        f"ency_{article_id}",
                        "encyclopedia",
                        article_id,
                        title,
                        content,
                        content[:300] + "..." if len(content) > 300 else content,
                        json.dumps({
                            "file_path": str(rel_path),
                            "file_size": md_file.stat().st_size
                        }),
                        "en",  # Default language
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))

                except Exception as e:
                    logger.warning(f"Error indexing encyclopedia file {md_file}: {e}")

        # Index users (for @ mentions and user search)
        users = db_session.query(User).all()
        for user in users:
            content = f"{user.username} {user.full_name or ''} {user.email}"
            db_session.execute("""
                INSERT INTO search_index (id, content_type, content_id, title, content, summary, metadata, language_code, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"user_{user.id}",
                "user",
                user.id,
                user.username,
                content,
                f"{user.username} ({user.full_name or 'No name'})",
                json.dumps({
                    "user_type_id": user.user_type_id,
                    "is_active": user.is_active,
                    "is_superuser": user.is_superuser
                }),
                "en",
                user.created_at.isoformat(),
                user.updated_at.isoformat()
            ))

        db_session.commit()
        logger.info("Search index initialization completed")

    except Exception as e:
        logger.error(f"Error initializing search data: {e}")
        db_session.rollback()
        raise