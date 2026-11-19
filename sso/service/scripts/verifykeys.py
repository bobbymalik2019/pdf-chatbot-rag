import base64
import json
import urllib.request

from cryptography.hazmat.primitives import serialization

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_KEY_FILE = PROJECT_ROOT / "keys" / "public.pem"

# Read the local RSA public key
with open("keys/public.pem", "rb") as f:
    public_key = serialization.load_pem_public_key(f.read())

local_numbers = public_key.public_numbers()

# Extract modulus from local PEM
local_n = public_key.public_numbers().n
# Encode it exactly as JWKS does
local_n_bytes = local_n.to_bytes(
    (local_n.bit_length() + 7) // 8,
    byteorder="big"
)

local_n_base64url = base64.urlsafe_b64encode(
    local_n_bytes
).rstrip(b"=").decode("ascii")




# Retrieve the JWKS document
url = "http://ssotest.charter26.com:3100/.well-known/jwks.json"

with urllib.request.urlopen(url) as response:
    jwks = json.load(response)

jwk = next(
    key for key in jwks["keys"]
    if key["kid"] == "sso-dev-key-1"
)

# Value published by Charter26
remote_n_base64url = jwk["n"]

# Decode Base64URL into an integer
def decode_base64url_integer(value):
    padded = value + "=" * (-len(value) % 4)
    raw = base64.urlsafe_b64decode(padded)
    return int.from_bytes(raw, byteorder="big")

remote_n = decode_base64url_integer(jwk["n"])
remote_e = decode_base64url_integer(jwk["e"])

print("Local modulus (hex):", format(local_numbers.n, "X"))
print("JWKS modulus  (hex):", format(remote_n, "X"))

print("Modulus matches:", local_numbers.n == remote_n)
print("Exponent matches:", local_numbers.e == remote_e)


print("Local PEM n:", local_n_base64url)
print("JWKS      n:", remote_n_base64url)

print(
    "Exact Base64URL match:",
    local_n_base64url == remote_n_base64url
)