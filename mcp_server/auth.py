"""Authentication module with support for local and JWT-based verification."""
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
import httpx

from mcp.server.auth.provider import TokenVerifier, AccessToken
from mcp_server.logging import get_logger

logger = get_logger(__name__)


class LocalNoOpTokenVerifier(TokenVerifier):
    """Development token verifier that accepts any token.
    
    Used in local profile (development). Logs a warning on each verification.
    """

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        """Accept any token and return a basic AccessToken."""
        logger.warning(
            "Using LocalNoOpTokenVerifier: all tokens accepted",
            transport="stdio"
        )
        # Return an AccessToken with the token itself as the subject
        return AccessToken(
            token=token,
            client_id="devops-os-local",
            scopes=["*"],
            resource="devops-os-local",
        )


class JWTTokenVerifier(TokenVerifier):
    """JWT-based token verifier for production use.
    
    Validates:
    - Signature (using JWKS public keys)
    - Issuer (must match configured issuer)
    - Audience (must match configured audience)
    - Expiration (must not be expired)
    """

    def __init__(
        self,
        issuer: str,
        audience: str,
        jwks_url: Optional[str] = None,
        key_cache_ttl_seconds: int = 3600,
    ):
        """Initialize JWT verifier.
        
        Args:
            issuer: Expected JWT issuer (e.g., https://auth.example.com/)
            audience: Expected JWT audience (e.g., devops-os-service)
            jwks_url: URL to fetch public keys from (if None, will construct from issuer)
            key_cache_ttl_seconds: How long to cache JWKS keys
        """
        self.issuer = issuer
        self.audience = audience
        self.jwks_url = jwks_url or self._construct_jwks_url(issuer)
        self.key_cache_ttl_seconds = key_cache_ttl_seconds
        
        # Cache for JWKS keys
        self._jwks_cache: Optional[Dict[str, Any]] = None
        self._cache_expiry: float = 0

    @staticmethod
    def _construct_jwks_url(issuer: str) -> str:
        """Construct JWKS URL from issuer."""
        issuer = issuer.rstrip('/')
        return f"{issuer}/.well-known/jwks.json"

    async def _fetch_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS keys from URL with caching."""
        import time
        
        now = time.time()
        if self._jwks_cache and now < self._cache_expiry:
            return self._jwks_cache

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
                self._jwks_cache = response.json()
                self._cache_expiry = now + self.key_cache_ttl_seconds
                return self._jwks_cache
        except Exception as e:
            logger.error(
                f"Failed to fetch JWKS: {e}",
                error_category="jwks_fetch_failure"
            )
            raise

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        """Verify JWT token.
        
        Returns None if verification fails (will cause FastMCP to reject request).
        """
        try:
            # Try using PyJWT first, fall back to python-jose
            try:
                import jwt
                from jwt import PyJWKClient
                use_jwt = True
            except ImportError:
                try:
                    from jose import jwt
                    use_jwt = False
                except ImportError:
                    logger.error(
                        "JWT validation failed: neither PyJWT nor python-jose installed",
                        error_category="missing_dependency"
                    )
                    return None

            # Decode and validate token with proper signature verification
            if use_jwt:
                # Using PyJWT with JWKS
                try:
                    # Create JWKS client for signature verification
                    jwks_client = PyJWKClient(self.jwks_url, cache_keys=True, max_cached_keys=16)
                    
                    # Decode with full validation
                    decoded = jwt.decode(
                        token,
                        jwks_client.get_signing_key_from_jwt(token).key,
                        algorithms=["RS256", "RS384", "RS512"],
                        audience=self.audience,
                        issuer=self.issuer,
                        options={"verify_signature": True},
                    )
                except Exception as e:
                    logger.log_auth_failure(
                        f"JWT signature verification failed: {str(e)}",
                        transport="http"
                    )
                    return None
            else:
                # Using python-jose
                try:
                    # Fetch and use JWKS
                    jwks = await self._fetch_jwks()
                    decoded = jwt.get_unverified_claims(token)
                    
                    # Get key ID from token header
                    header = jwt.get_unverified_header(token)
                    kid = header.get("kid")
                    
                    # Find matching key in JWKS
                    key = None
                    for k in jwks.get("keys", []):
                        if k.get("kid") == kid or kid is None:
                            key = k
                            break
                    
                    if not key:
                        logger.log_auth_failure(
                            "No matching key in JWKS",
                            transport="http"
                        )
                        return None
                    
                    # Verify token with the key
                    decoded = jwt.decode(
                        token,
                        key,
                        algorithms=["RS256", "RS384", "RS512"],
                        audience=self.audience,
                        issuer=self.issuer,
                    )
                except Exception as e:
                    logger.log_auth_failure(
                        f"JWT validation failed: {str(e)}",
                        transport="http"
                    )
                    return None
            
            # Return AccessToken
            return AccessToken(
                token=token,
                client_id=decoded.get("sub", "unknown"),
                scopes=decoded.get("scope", "").split() if decoded.get("scope") else [],
                resource=self.audience,
            )

        except Exception as e:
            logger.log_auth_failure(
                f"Token validation error: {type(e).__name__}",
                transport="http"
            )
            return None


def create_token_verifier(
    profile: str,
    jwt_issuer: Optional[str] = None,
    jwt_audience: Optional[str] = None,
    jwt_jwks_url: Optional[str] = None,
) -> TokenVerifier:
    """Factory function to create appropriate token verifier.
    
    Args:
        profile: "local" (no-op) or "remote" (JWT)
        jwt_issuer: Required for "remote" profile
        jwt_audience: Required for "remote" profile
        jwt_jwks_url: Optional JWKS URL for "remote" profile
        
    Returns:
        TokenVerifier instance
        
    Raises:
        ValueError: If remote profile is missing required JWT config
    """
    if profile == "local":
        return LocalNoOpTokenVerifier()
    elif profile == "remote":
        if not jwt_issuer:
            raise ValueError("DEVOPS_OS_JWT_ISSUER required for remote profile")
        if not jwt_audience:
            raise ValueError("DEVOPS_OS_JWT_AUDIENCE required for remote profile")
        return JWTTokenVerifier(
            issuer=jwt_issuer,
            audience=jwt_audience,
            jwks_url=jwt_jwks_url,
        )
    else:
        raise ValueError(f"Unknown profile: {profile}")
