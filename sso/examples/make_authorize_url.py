"""Local manual PKCE smoke-test utility; not an OAuth client application."""
import base64
import hashlib
import secrets
from urllib.parse import urlencode

verifier = secrets.token_urlsafe(48)
challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
query = urlencode({
    'response_type':'code', 'client_id':'pdf-chatbot',
    'redirect_uri':'http://127.0.0.1:3000/auth/callback',
    'scope':'openid profile', 'state':secrets.token_urlsafe(24),
    'code_challenge_method':'S256', 'code_challenge':challenge,
    'nonce':secrets.token_urlsafe(24)
})
print('Browser URL: http://127.0.0.1:3100/oauth/authorize?' + query)
print('PKCE verifier (save privately for code exchange):', verifier)
