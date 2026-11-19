
import os
import secrets
import hashlib
import base64
from urllib.parse import urlencode, urlparse, parse_qs

import requests
import jwt

ISSUER = "http://ssotest.charter26.com:3100"
CLIENT_ID = "chatbot-gateway"
CLIENT_SECRET = os.environ["OIDC_CLIENT_SECRET"]
REDIRECT_URI = "http://chatbottest.charter26.com:3000/auth/callback"

# 1. Generate PKCE verifier and S256 challenge
verifier = secrets.token_urlsafe(64)
challenge = base64.urlsafe_b64encode(
    hashlib.sha256(verifier.encode("ascii")).digest()
).rstrip(b"=").decode("ascii")

state = secrets.token_urlsafe(32)
nonce = secrets.token_urlsafe(32)

# 2. Discover provider endpoints
discovery = requests.get(
    f"{ISSUER}/.well-known/openid-configuration",
    timeout=10
).json()

assert discovery["issuer"] == ISSUER
assert "S256" in discovery["code_challenge_methods_supported"]

# 3. Construct authorization request
params = {
    "response_type": "code",
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "scope": "openid profile",
    "state": state,
    "nonce": nonce,
    "code_challenge": challenge,
    "code_challenge_method": "S256",
}

authorization_url = (
    discovery["authorization_endpoint"]
    + "?"
    + urlencode(params)
)

print("\nOpen this URL in your browser:\n")
print(authorization_url)

# 4. Manually capture the callback URL
callback_url = input(
    "\nPaste the complete callback URL from browser: "
).strip()

callback = urlparse(callback_url)
expected = urlparse(REDIRECT_URI)

assert (
    callback.scheme,
    callback.netloc,
    callback.path
) == (
    expected.scheme,
    expected.netloc,
    expected.path
), "Unexpected callback URI"

query = parse_qs(callback.query)

assert query.get("state", [None])[0] == state, "State mismatch"

if "error" in query:
    raise RuntimeError(f"Authorization failed: {query['error'][0]}")

code = query["code"][0]

# 5. Exchange code for tokens
response = requests.post(
    discovery["token_endpoint"],
    auth=(CLIENT_ID, CLIENT_SECRET),
    data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": verifier,
    },
    timeout=15,
)

response.raise_for_status()
tokens = response.json()

assert tokens["token_type"] == "Bearer"

print("\nAuthorization code exchanged successfully.")

# 6. Verify JWTs using published JWKS
jwks_client = jwt.PyJWKClient(discovery["jwks_uri"])

def verify_token(token, audience):
    key = jwks_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        key.key,
        algorithms=["RS256"],
        issuer=ISSUER,
        audience=audience,
        options={"require": ["iss", "sub", "aud", "exp", "iat"]},
    )

access_claims = verify_token(
    tokens["access_token"],
    "pdf-ingestion-service"
)

id_claims = verify_token(
    tokens["id_token"],
    CLIENT_ID
)

assert id_claims["nonce"] == nonce
assert access_claims["sub"] == id_claims["sub"]
assert access_claims["client_id"] == CLIENT_ID

print("Access token signature and claims: VALID")
print("ID token signature and claims: VALID")
print("OIDC nonce: VALID")
print("Authenticated subject:", id_claims["sub"])
print("Access token audience:", access_claims["aud"])
print("\nOIDC authorization-code flow verified!")
