from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
import re
from .translations import setup_translations
from .database import get_db
from sqlalchemy.orm import Session
from .logging_config import logger

class LanguageMiddleware(BaseHTTPMiddleware):
    """Middleware for language detection and setup"""

    async def dispatch(self, request: Request, call_next):
        # Extract language from various sources
        language = await self._detect_language(request)

        # Set up translations for this request
        setup_translations(language)

        # Store language in request state for use in endpoints
        request.state.language = language

        # Add language header to response
        response = await call_next(request)
        response.headers['X-API-Language'] = language

        return response

    async def _detect_language(self, request: Request) -> str:
        """Detect language from request headers, user preferences, etc."""

        # 1. Check for language in query parameter (highest priority)
        query_lang = request.query_params.get('lang')
        if query_lang and self._is_valid_language(query_lang):
            return query_lang

        # 2. Check for language in custom header
        header_lang = request.headers.get('X-Language')
        if header_lang and self._is_valid_language(header_lang):
            return header_lang

        # 3. Check Accept-Language header
        accept_lang = request.headers.get('accept-language', '')
        if accept_lang:
            detected = self._parse_accept_language(accept_lang)
            if detected:
                return detected

        # 4. Check user preference from database (if authenticated)
        try:
            # This would require authentication middleware to run first
            # For now, we'll skip this and implement it later
            pass
        except Exception as e:
            logger.debug(f"Could not get user language preference: {e}")

        # Default to English
        return 'en'

    def _is_valid_language(self, lang: str) -> bool:
        """Check if language code is valid"""
        supported_langs = ['en', 'es', 'fr', 'de', 'ar', 'zh']
        return lang in supported_langs

    def _parse_accept_language(self, accept_lang: str) -> Optional[str]:
        """Parse Accept-Language header and return best match"""
        # Simple parsing - in production, use a proper library
        langs = []
        for item in accept_lang.split(','):
            item = item.strip()
            if ';' in item:
                lang, q = item.split(';', 1)
                try:
                    q_val = float(q.split('=')[1])
                    langs.append((lang.strip(), q_val))
                except:
                    langs.append((lang.strip(), 1.0))
            else:
                langs.append((item, 1.0))

        # Sort by quality
        langs.sort(key=lambda x: x[1], reverse=True)

        # Return first supported language
        supported_langs = ['en', 'es', 'fr', 'de', 'ar', 'zh']
        for lang, _ in langs:
            # Handle language ranges like en-US -> en
            base_lang = lang.split('-')[0].lower()
            if base_lang in supported_langs:
                return base_lang

        return None