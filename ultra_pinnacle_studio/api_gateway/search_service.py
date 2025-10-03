"""
Advanced search service for Ultra Pinnacle AI Studio
"""
import json
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
from pathlib import Path
from functools import lru_cache
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .logging_config import logger
from .database import get_db
from .search_models import (
    SearchQuery, SearchAnalytics, SavedSearch, SearchSuggestion,
    SearchFacet, SearchExport, create_search_tables, init_search_data
)
from .translation_service import get_translation_service

class SearchService:
    """Advanced search service with indexing, ranking, and analytics"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.translation_service = get_translation_service(None)  # Will be initialized later
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._init_search_tables()

    def _init_search_tables(self):
        """Initialize search tables"""
        try:
            from .database import engine
            create_search_tables(engine)
            logger.info("Search tables initialized")
        except Exception as e:
            logger.error(f"Error initializing search tables: {e}")

    def _get_db_session(self):
        """Get database session"""
        db = next(get_db())
        return db

    async def index_content(self, content_type: str, content_id: Any, data: Dict[str, Any]):
        """Index new or updated content"""
        try:
            db = self._get_db_session()

            # Prepare search document
            search_id = f"{content_type[:4]}_{content_id}"
            title = data.get('title', '')
            content = data.get('content', '')
            summary = data.get('summary', content[:200] + '...' if len(content) > 200 else content)
            tags = data.get('tags', [])
            metadata = data.get('metadata', {})
            language_code = data.get('language_code', 'en')

            # Remove existing entry
            from sqlalchemy import text
            db.execute(text("DELETE FROM search_index WHERE id = :search_id"), {"search_id": search_id})

            # Insert new entry
            db.execute(text("""
                INSERT INTO search_index (
                    id, content_type, content_id, title, content, summary,
                    tags, metadata, language_code, created_at, updated_at
                ) VALUES (:id, :content_type, :content_id, :title, :content, :summary,
                         :tags, :metadata, :language_code, :created_at, :updated_at)
            """), {
                "id": search_id,
                "content_type": content_type,
                "content_id": str(content_id),
                "title": title,
                "content": content,
                "summary": summary,
                "tags": json.dumps(tags),
                "metadata": json.dumps(metadata),
                "language_code": language_code,
                "created_at": data.get('created_at', datetime.now().isoformat()),
                "updated_at": data.get('updated_at', datetime.now().isoformat())
            })

            db.commit()
            logger.debug(f"Indexed {content_type} {content_id}")

        except Exception as e:
            logger.error(f"Error indexing content {content_type} {content_id}: {e}")
        finally:
            db.close()

    async def remove_from_index(self, content_type: str, content_id: Any):
        """Remove content from search index"""
        try:
            db = self._get_db_session()
            search_id = f"{content_type[:4]}_{content_id}"
            db.execute("DELETE FROM search_index WHERE id = ?", (search_id,))
            db.commit()
            logger.debug(f"Removed {content_type} {content_id} from index")
        except Exception as e:
            logger.error(f"Error removing content from index: {e}")
        finally:
            db.close()

    def _build_search_query(self, query: str, filters: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """Build FTS5 search query with filters"""
        fts_query_parts = []

        # Handle different query types
        if query.startswith('"') and query.endswith('"'):
            # Exact phrase search
            fts_query_parts.append(f'"{query[1:-1]}"')
        elif ' OR ' in query.upper():
            # OR search
            terms = [term.strip() for term in query.upper().split(' OR ')]
            fts_query_parts.append(' OR '.join(terms))
        elif ' AND ' in query.upper():
            # AND search
            terms = [term.strip() for term in query.upper().split(' AND ')]
            fts_query_parts.append(' AND '.join(terms))
        else:
            # Default AND search for multiple terms
            terms = query.split()
            if len(terms) > 1:
                fts_query_parts.append(' AND '.join(terms))
            else:
                fts_query_parts.append(query)

        # Add field-specific searches
        if 'title:' in query.lower():
            title_match = re.search(r'title:("([^"]+)"|(\S+))', query.lower())
            if title_match:
                title_term = title_match.group(2) or title_match.group(3)
                fts_query_parts.append(f'title:{title_term}')

        # Build the final FTS query
        fts_query = ' AND '.join(fts_query_parts)

        # Build WHERE conditions for filters
        where_conditions = []
        params = []

        # Content type filter
        if 'content_types' in filters and filters['content_types']:
            placeholders = ','.join('?' * len(filters['content_types']))
            where_conditions.append(f"content_type IN ({placeholders})")
            params.extend(filters['content_types'])

        # Language filter
        if 'languages' in filters and filters['languages']:
            placeholders = ','.join('?' * len(filters['languages']))
            where_conditions.append(f"language_code IN ({placeholders})")
            params.extend(filters['languages'])

        # Date range filter
        if 'date_from' in filters:
            where_conditions.append("datetime(created_at) >= datetime(?)")
            params.append(filters['date_from'])
        if 'date_to' in filters:
            where_conditions.append("datetime(created_at) <= datetime(?)")
            params.append(filters['date_to'])

        # User filter
        if 'user_ids' in filters and filters['user_ids']:
            # This requires joining with metadata JSON
            user_conditions = []
            for user_id in filters['user_ids']:
                user_conditions.append("metadata LIKE ?")
                params.append(f'%"user_id": {user_id}%')
            if user_conditions:
                where_conditions.append(f"({' OR '.join(user_conditions)})")

        # Tags filter
        if 'tags' in filters and filters['tags']:
            tag_conditions = []
            for tag in filters['tags']:
                tag_conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')
            if tag_conditions:
                where_conditions.append(f"({' OR '.join(tag_conditions)})")

        where_clause = " AND ".join(where_conditions) if where_conditions else ""

        return fts_query, where_clause, params

    def _calculate_relevance_score(self, row: Dict[str, Any], query: str) -> float:
        """Calculate relevance score for search results"""
        score = 0.0

        # Title matches are most important
        if query.lower() in row['title'].lower():
            score += 10.0

        # Content matches
        content_lower = row['content'].lower()
        query_lower = query.lower()
        if query_lower in content_lower:
            score += 5.0

        # Partial matches in title
        title_words = set(row['title'].lower().split())
        query_words = set(query_lower.split())
        title_matches = len(title_words.intersection(query_words))
        if title_matches > 0:
            score += title_matches * 2.0

        # Recency bonus (newer content gets slight boost)
        try:
            created_at = datetime.fromisoformat(row['created_at'])
            days_old = (datetime.now(timezone.utc) - created_at).days
            recency_bonus = max(0, 1.0 - (days_old / 365.0))  # 1 year decay
            score += recency_bonus
        except:
            pass

        # Content type weights
        content_type_weights = {
            'help': 1.2,  # Help articles are important
            'encyclopedia': 1.1,  # Encyclopedia is valuable
            'document': 1.0,  # Documents are standard
            'conversation': 0.9,  # Conversations are common
            'user': 0.8  # Users are least prioritized
        }
        score *= content_type_weights.get(row['content_type'], 1.0)

        return score

    async def search(self, query: str, filters: Dict[str, Any] = None,
                    user_id: Optional[int] = None, limit: int = 50,
                    offset: int = 0, sort_by: str = 'relevance',
                    ip_address: str = None, user_agent: str = None) -> Dict[str, Any]:
        """Perform advanced search with ranking and analytics"""
        start_time = time.time()
        filters = filters or {}

        try:
            db = self._get_db_session()

            # Build search query
            fts_query, where_clause, params = self._build_search_query(query, filters)

            # Execute search
            sql = f"""
                SELECT id, content_type, content_id, title, content, summary,
                       tags, metadata, language_code, created_at, updated_at,
                       rank
                FROM search_index
                WHERE search_index MATCH ?
                {'AND ' + where_clause if where_clause else ''}
                ORDER BY rank
                LIMIT ? OFFSET ?
            """

            all_params = [fts_query] + params + [limit, offset]
            result = db.execute(sql, all_params)
            rows = result.fetchall()

            # Process results
            results = []
            facets = {
                'content_types': {},
                'languages': {},
                'tags': {},
                'date_ranges': {}
            }

            for row in rows:
                row_dict = dict(row)

                # Parse JSON fields
                row_dict['tags'] = json.loads(row_dict['tags'] or '[]')
                row_dict['metadata'] = json.loads(row_dict['metadata'] or '{}')

                # Calculate relevance score
                row_dict['relevance_score'] = self._calculate_relevance_score(row_dict, query)

                results.append(row_dict)

                # Update facets
                ct = row_dict['content_type']
                lang = row_dict['language_code']
                facets['content_types'][ct] = facets['content_types'].get(ct, 0) + 1
                facets['languages'][lang] = facets['languages'].get(lang, 0) + 1

                # Tag facets
                for tag in row_dict['tags']:
                    facets['tags'][tag] = facets['tags'].get(tag, 0) + 1

                # Date facets
                try:
                    created_date = datetime.fromisoformat(row_dict['created_at'])
                    month_key = created_date.strftime('%Y-%m')
                    facets['date_ranges'][month_key] = facets['date_ranges'].get(month_key, 0) + 1
                except:
                    pass

            # Sort results
            if sort_by == 'relevance':
                results.sort(key=lambda x: x['relevance_score'], reverse=True)
            elif sort_by == 'date':
                results.sort(key=lambda x: x['created_at'], reverse=True)
            elif sort_by == 'title':
                results.sort(key=lambda x: x['title'].lower())

            # Record search analytics
            search_time = time.time() - start_time
            await self._record_search_analytics(query, len(results), search_time, user_id, filters, ip_address, user_agent)

            # Update suggestions
            await self._update_suggestions(query)

            return {
                'query': query,
                'results': results,
                'total': len(results),
                'facets': facets,
                'search_time': search_time,
                'filters_applied': filters
            }

        except Exception as e:
            logger.error(f"Error performing search: {e}")
            return {
                'query': query,
                'results': [],
                'total': 0,
                'facets': {},
                'search_time': time.time() - start_time,
                'error': str(e)
            }
        finally:
            db.close()

    async def _record_search_analytics(self, query: str, result_count: int, search_time: float,
                                     user_id: Optional[int], filters: Dict[str, Any],
                                     ip_address: str, user_agent: str):
        """Record search analytics"""
        try:
            db = self._get_db_session()

            # Record search query
            search_query = SearchQuery(
                user_id=user_id,
                query=query,
                filters=filters,
                result_count=result_count,
                search_time=search_time,
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.add(search_query)

            # Update search analytics
            analytics = db.query(SearchAnalytics).filter(SearchAnalytics.query == query).first()
            if not analytics:
                analytics = SearchAnalytics(
                    query=query,
                    result_count=result_count,
                    avg_search_time=search_time,
                    search_count=1
                )
                db.add(analytics)
            else:
                # Update running averages
                total_searches = analytics.search_count + 1
                analytics.avg_search_time = ((analytics.avg_search_time * analytics.search_count) + search_time) / total_searches
                analytics.result_count = result_count
                analytics.search_count = total_searches
                analytics.last_searched = datetime.now(timezone.utc)

                # Calculate popularity score (searches per day * recency)
                days_since_first = (datetime.now(timezone.utc) - analytics.first_searched).days
                if days_since_first > 0:
                    analytics.popularity_score = analytics.search_count / days_since_first

            db.commit()

        except Exception as e:
            logger.error(f"Error recording search analytics: {e}")
        finally:
            db.close()

    async def _update_suggestions(self, query: str):
        """Update search suggestions based on query"""
        try:
            db = self._get_db_session()

            # Extract potential suggestions (individual words and phrases)
            words = re.findall(r'\b\w+\b', query.lower())
            phrases = re.findall(r'"([^"]*)"', query.lower())

            suggestions = words + phrases

            for suggestion in suggestions:
                if len(suggestion) < 3:  # Skip very short suggestions
                    continue

                existing = db.query(SearchSuggestion).filter(
                    SearchSuggestion.suggestion == suggestion
                ).first()

                if existing:
                    existing.popularity += 1
                    existing.last_used = datetime.now(timezone.utc)
                else:
                    new_suggestion = SearchSuggestion(
                        suggestion=suggestion,
                        category='query'
                    )
                    db.add(new_suggestion)

            db.commit()

        except Exception as e:
            logger.error(f"Error updating suggestions: {e}")
        finally:
            db.close()

    async def get_suggestions(self, prefix: str, limit: int = 10) -> List[str]:
        """Get autocomplete suggestions"""
        try:
            db = self._get_db_session()

            suggestions = db.query(SearchSuggestion).filter(
                SearchSuggestion.suggestion.like(f'{prefix}%')
            ).order_by(
                SearchSuggestion.popularity.desc(),
                SearchSuggestion.last_used.desc()
            ).limit(limit).all()

            return [s.suggestion for s in suggestions]

        except Exception as e:
            logger.error(f"Error getting suggestions: {e}")
            return []
        finally:
            db.close()

    async def get_popular_queries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get popular search queries"""
        try:
            db = self._get_db_session()

            queries = db.query(SearchAnalytics).order_by(
                SearchAnalytics.popularity_score.desc()
            ).limit(limit).all()

            return [{
                'query': q.query,
                'search_count': q.search_count,
                'avg_search_time': q.avg_search_time,
                'popularity_score': q.popularity_score,
                'last_searched': q.last_searched.isoformat()
            } for q in queries]

        except Exception as e:
            logger.error(f"Error getting popular queries: {e}")
            return []
        finally:
            db.close()

    async def save_search(self, user_id: int, name: str, query: str,
                         filters: Dict[str, Any], description: str = None) -> bool:
        """Save a search for later use"""
        try:
            db = self._get_db_session()

            saved_search = SavedSearch(
                user_id=user_id,
                name=name,
                query=query,
                filters=filters,
                description=description
            )
            db.add(saved_search)
            db.commit()

            return True

        except Exception as e:
            logger.error(f"Error saving search: {e}")
            return False
        finally:
            db.close()

    async def get_saved_searches(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's saved searches"""
        try:
            db = self._get_db_session()

            searches = db.query(SavedSearch).filter(
                SavedSearch.user_id == user_id
            ).order_by(SavedSearch.last_used.desc()).all()

            return [{
                'id': s.id,
                'name': s.name,
                'query': s.query,
                'filters': s.filters,
                'description': s.description,
                'usage_count': s.usage_count,
                'created_at': s.created_at.isoformat(),
                'last_used': s.last_used.isoformat()
            } for s in searches]

        except Exception as e:
            logger.error(f"Error getting saved searches: {e}")
            return []
        finally:
            db.close()

    async def export_search_results(self, query: str, filters: Dict[str, Any],
                                  format: str, user_id: int) -> str:
        """Export search results to file"""
        try:
            # Perform search
            results = await self.search(query, filters, user_id, limit=1000)

            # Generate export
            export_id = f"export_{int(time.time())}_{user_id}"

            if format == 'json':
                data = json.dumps(results['results'], indent=2, default=str)
                filename = f"search_results_{export_id}.json"
            elif format == 'csv':
                import csv
                import io
                output = io.StringIO()
                if results['results']:
                    writer = csv.DictWriter(output, fieldnames=results['results'][0].keys())
                    writer.writeheader()
                    for row in results['results']:
                        # Convert complex types to strings
                        clean_row = {}
                        for k, v in row.items():
                            if isinstance(v, (list, dict)):
                                clean_row[k] = json.dumps(v)
                            else:
                                clean_row[k] = str(v)
                        writer.writerow(clean_row)
                data = output.getvalue()
                filename = f"search_results_{export_id}.csv"
            else:
                raise ValueError(f"Unsupported format: {format}")

            # Save to file
            export_dir = Path("exports")
            export_dir.mkdir(exist_ok=True)
            file_path = export_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(data)

            # Record export
            db = self._get_db_session()
            export_record = SearchExport(
                id=export_id,
                user_id=user_id,
                query=query,
                filters=filters,
                format=format,
                status='completed',
                file_path=str(file_path),
                file_size=len(data.encode('utf-8')),
                result_count=len(results['results']),
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                completed_at=datetime.now(timezone.utc)
            )
            db.add(export_record)
            db.commit()

            return export_id

        except Exception as e:
            logger.error(f"Error exporting search results: {e}")
            raise
        finally:
            db.close()

    async def reindex_all_content(self):
        """Reindex all content in the background"""
        try:
            logger.info("Starting full reindexing...")
            db = self._get_db_session()

            # Clear existing index
            db.execute("DELETE FROM search_index")

            # Reinitialize with current data
            init_search_data(db)

            logger.info("Full reindexing completed")

        except Exception as e:
            logger.error(f"Error during reindexing: {e}")
        finally:
            db.close()

    async def get_search_stats(self) -> Dict[str, Any]:
        """Get comprehensive search statistics"""
        try:
            db = self._get_db_session()

            # Total indexed documents
            total_docs = db.execute("SELECT COUNT(*) FROM search_index").scalar()

            # Documents by type
            docs_by_type = db.execute("""
                SELECT content_type, COUNT(*) as count
                FROM search_index
                GROUP BY content_type
            """).fetchall()

            # Recent searches
            recent_searches = db.query(SearchQuery).order_by(
                SearchQuery.created_at.desc()
            ).limit(100).all()

            # Popular queries
            popular_queries = db.query(SearchAnalytics).order_by(
                SearchAnalytics.popularity_score.desc()
            ).limit(10).all()

            return {
                'total_indexed_documents': total_docs,
                'documents_by_type': dict(docs_by_type),
                'recent_searches_count': len(recent_searches),
                'popular_queries': [{
                    'query': q.query,
                    'search_count': q.search_count,
                    'popularity_score': q.popularity_score
                } for q in popular_queries],
                'avg_search_time': db.query(SearchQuery).filter(
                    SearchQuery.search_time.isnot(None)
                ).with_entities(SearchQuery.search_time).all()
            }

        except Exception as e:
            logger.error(f"Error getting search stats: {e}")
            return {}
        finally:
            db.close()