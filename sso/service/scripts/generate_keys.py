from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

folder = Path('keys')
folder.mkdir(exist_ok=True)
if (folder/'private.pem').exists() or (folder/'public.pem').exists():
    raise SystemExit('Key already exists. Refusing to overwrite it.')
key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
(folder/'private.pem').write_bytes(key.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption()
))
(folder/'public.pem').write_bytes(key.public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
))
print('Keys created. Protect keys/private.pem; do not commit to source control.')
