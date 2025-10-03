"""
OAuth service for Google and GitHub authentication
"""
import secrets
import hashlib
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import httpx
from .logging_config import logger
from .database import OAuthAccount, User, get_db
from .auth import create_access_token, create_user
from sqlalchemy.orm import Session


class OAuthService:
    """OAuth service for handling Google and GitHub authentication"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.providers = {
            'google': {
                'client_id': config.get('client_id'),
                'client_secret': config.get('client_secret'),
                'redirect_uri': config.get('redirect_uri'),
                'authorization_url': config.get('authorization_url'),
                'token_url': config.get('token_url'),
                'userinfo_url': config.get('userinfo_url'),
                'scopes': config.get('scopes', [])
            },
            'github': {
                'client_id': config.get('client_id'),
                'client_secret': config.get('client_secret'),
                'redirect_uri': config.get('redirect_uri'),
                'authorization_url': config.get('authorization_url'),
                'token_url': config.get('token_url'),
                'userinfo_url': config.get('userinfo_url'),
                'scopes': config.get('scopes', [])
            }
        }

    def get_authorization_url(self, provider: str, state: Optional[str] = None) -> Dict[str, str]:
        """Generate OAuth authorization URL"""
        if provider not in self.providers:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        config = self.providers[provider]
        if not config['client_id']:
            raise ValueError(f"OAuth client ID not configured for {provider}")

        # Generate state if not provided
        if not state:
            state = secrets.token_urlsafe(32)

        params = {
            'client_id': config['client_id'],
            'redirect_uri': config['redirect_uri'],
            'scope': ' '.join(config['scopes']),
            'response_type': 'code',
            'state': state
        }

        # GitHub uses comma-separated scopes
        if provider == 'github':
            params['scope'] = ','.join(config['scopes'])

        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        authorization_url = f"{config['authorization_url']}?{query_string}"

        return {
            'authorization_url': authorization_url,
            'state': state
        }

    async def exchange_code_for_token(self, provider: str, code: str, state: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        if provider not in self.providers:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        config = self.providers[provider]

        data = {
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': config['redirect_uri']
        }

        headers = {'Accept': 'application/json'}

        # GitHub requires different content type
        if provider == 'github':
            headers['Accept'] = 'application/json'

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    config['token_url'],
                    data=data,
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()
                token_data = response.json()

                if 'error' in token_data:
                    raise ValueError(f"OAuth error: {token_data['error_description']}")

                return token_data

            except httpx.HTTPError as e:
                logger.error(f"OAuth token exchange failed for {provider}: {e}")
                raise ValueError(f"Failed to exchange code for token: {str(e)}")

    async def get_user_info(self, provider: str, access_token: str) -> Dict[str, Any]:
        """Get user information from OAuth provider"""
        if provider not in self.providers:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        config = self.providers[provider]

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }

        # GitHub uses token in headers differently
        if provider == 'github':
            headers['Authorization'] = f'token {access_token}'

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    config['userinfo_url'],
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()
                user_info = response.json()

                # Normalize user info across providers
                normalized_info = self._normalize_user_info(provider, user_info)
                return normalized_info

            except httpx.HTTPError as e:
                logger.error(f"Failed to get user info from {provider}: {e}")
                raise ValueError(f"Failed to get user information: {str(e)}")

    def _normalize_user_info(self, provider: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize user info to common format"""
        if provider == 'google':
            return {
                'provider_user_id': user_info.get('sub'),
                'email': user_info.get('email'),
                'email_verified': user_info.get('email_verified', False),
                'name': user_info.get('name'),
                'given_name': user_info.get('given_name'),
                'family_name': user_info.get('family_name'),
                'picture': user_info.get('picture'),
                'locale': user_info.get('locale'),
                'username': None  # Google doesn't provide username
            }
        elif provider == 'github':
            return {
                'provider_user_id': str(user_info.get('id')),
                'email': user_info.get('email'),
                'email_verified': True,  # GitHub emails are verified
                'name': user_info.get('name'),
                'given_name': None,
                'family_name': None,
                'picture': user_info.get('avatar_url'),
                'locale': None,
                'username': user_info.get('login')
            }
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def authenticate_or_create_user(self, db: Session, provider: str, user_info: Dict[str, Any], token_data: Dict[str, Any]) -> User:
        """Authenticate existing user or create new one"""
        # Check if OAuth account already exists
        oauth_account = db.query(OAuthAccount).filter(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == user_info['provider_user_id']
        ).first()

        if oauth_account:
            # Update existing OAuth account
            oauth_account.access_token = self._encrypt_token(token_data.get('access_token'))
            oauth_account.refresh_token = self._encrypt_token(token_data.get('refresh_token'))
            oauth_account.token_expires_at = self._calculate_token_expiry(token_data)
            oauth_account.profile_data = user_info
            oauth_account.updated_at = datetime.now(timezone.utc)
            db.commit()

            user = oauth_account.user
            logger.info(f"Existing user authenticated via {provider}: {user.username}")
            return user

        # Check if user with this email already exists
        existing_user = None
        if user_info.get('email'):
            existing_user = db.query(User).filter(User.email == user_info['email']).first()

        if existing_user:
            # Link OAuth account to existing user
            oauth_account = OAuthAccount(
                user_id=existing_user.id,
                provider=provider,
                provider_user_id=user_info['provider_user_id'],
                provider_username=user_info.get('username'),
                provider_email=user_info.get('email'),
                access_token=self._encrypt_token(token_data.get('access_token')),
                refresh_token=self._encrypt_token(token_data.get('refresh_token')),
                token_expires_at=self._calculate_token_expiry(token_data),
                scopes=token_data.get('scope', '').split(),
                profile_data=user_info
            )
            db.add(oauth_account)
            db.commit()

            logger.info(f"OAuth account linked to existing user via {provider}: {existing_user.username}")
            return existing_user

        # Create new user
        username = self._generate_unique_username(db, user_info)
        full_name = user_info.get('name') or f"{user_info.get('given_name', '')} {user_info.get('family_name', '')}".strip()

        user = create_user(
            db=db,
            username=username,
            email=user_info.get('email'),
            password=secrets.token_urlsafe(32),  # Random password, user can change later
            full_name=full_name
        )

        if user:
            # Create OAuth account
            oauth_account = OAuthAccount(
                user_id=user.id,
                provider=provider,
                provider_user_id=user_info['provider_user_id'],
                provider_username=user_info.get('username'),
                provider_email=user_info.get('email'),
                access_token=self._encrypt_token(token_data.get('access_token')),
                refresh_token=self._encrypt_token(token_data.get('refresh_token')),
                token_expires_at=self._calculate_token_expiry(token_data),
                scopes=token_data.get('scope', '').split(),
                profile_data=user_info
            )
            db.add(oauth_account)

            # Mark email as verified if OAuth provider verified it
            if user_info.get('email_verified'):
                user.email_verified = True

            db.commit()

            logger.info(f"New user created via {provider} OAuth: {user.username}")
            return user

        raise ValueError("Failed to create user")

    def _generate_unique_username(self, db: Session, user_info: Dict[str, Any]) -> str:
        """Generate a unique username"""
        base_username = user_info.get('username') or user_info.get('email', '').split('@')[0] or 'user'

        # Clean username
        import re
        base_username = re.sub(r'[^\w.-]', '', base_username).lower()

        username = base_username
        counter = 1

        while db.query(User).filter(User.username == username).first():
            username = f"{base_username}{counter}"
            counter += 1

        return username

    def _encrypt_token(self, token: Optional[str]) -> Optional[str]:
        """Encrypt sensitive tokens (placeholder - implement proper encryption)"""
        if not token:
            return None
        # TODO: Implement proper encryption using Fernet or similar
        # For now, return as-is (not recommended for production)
        return token

    def _calculate_token_expiry(self, token_data: Dict[str, Any]) -> Optional[datetime]:
        """Calculate token expiry datetime"""
        expires_in = token_data.get('expires_in')
        if expires_in:
            return datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        return None


# Global OAuth service instance
_oauth_service = None

def get_oauth_service() -> OAuthService:
    """Get OAuth service instance"""
    global _oauth_service
    if _oauth_service is None:
        from .config import config
        oauth_config = config.get('security', {}).get('oauth', {})
        _oauth_service = OAuthService(oauth_config)
    return _oauth_service