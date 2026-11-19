from sso_service.security import hash_password, verify_password, pkce_challenge, digest

def test_argon2():
    pw = 'A very long & unique demo password!'
    a,b = hash_password(pw), hash_password(pw)
    assert a != b
    assert a.startswith('$argon2id$')
    assert verify_password(pw,a)
    assert not verify_password('wrong',a)

def test_pkce_vector():
    verifier = 'dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk'
    assert pkce_challenge(verifier) == 'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM'
