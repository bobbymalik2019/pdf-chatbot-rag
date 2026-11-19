
import { createHash, randomBytes, timingSafeEqual } from 'node:crypto';
import { createRemoteJWKSet, jwtVerify } from 'jose';

const issuer = process.env.OIDC_ISSUER;
const clientId = process.env.OIDC_CLIENT_ID;
const redirectUri = process.env.OIDC_REDIRECT_URI;
const clientSecret = process.env.OIDC_CLIENT_SECRET;
const accessAudience = process.env.OIDC_ACCESS_AUDIENCE;
const TRANSACTION_MAX_AGE_MS = 3 * 60 * 1000;

if (!issuer || !clientId || !redirectUri) {
  throw new Error('OIDC configuration is incomplete');
}

const issuerUrl = new URL(issuer);
const callbackUrl = new URL(redirectUri);

if (
  issuerUrl.protocol !== 'https:' ||
  issuerUrl.pathname !== '/' ||
  issuerUrl.search ||
  issuerUrl.hash ||
  callbackUrl.protocol !== 'https:'
) {
  throw new Error('Invalid OIDC issuer or redirect URI');
}

const normalizedIssuer = issuerUrl.origin;

function randomValue() {
  return randomBytes(32).toString('base64url');
}

function generatePkceChallenge(verifier) {
  return createHash('sha256')
    .update(verifier, 'ascii')
    .digest('base64url');
}

async function discoverProvider() {
  const response = await fetch(
    `${normalizedIssuer}/.well-known/openid-configuration`,
    {
      signal: AbortSignal.timeout(10000),
      headers: {
        Accept: 'application/json',
      },
    }
  );

  if (!response.ok) {
    throw new Error('OIDC discovery failed');
  }

  const metadata = await response.json();

  if (metadata.issuer !== normalizedIssuer) {
    throw new Error('OIDC issuer mismatch');
  }

  const authorizationUrl = new URL(
    metadata.authorization_endpoint
  );

  if (
    authorizationUrl.protocol !== 'https:' ||
    authorizationUrl.origin !== normalizedIssuer
  ) {
    throw new Error('Invalid OIDC authorization endpoint');
  }

  if (
    !metadata.response_types_supported?.includes('code') ||
    !metadata.code_challenge_methods_supported?.includes('S256')
  ) {
    throw new Error('Required OIDC capabilities unavailable');
  }

  return metadata;
}

export async function oidcCallback(req, res, next) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Referrer-Policy', 'no-referrer');

  let stage = 'callback_started';
  try {
    if (!req.secure) {
      return callbackError(res, 400, 'HTTPS required');
    }

    // Before reading the session transaction
    stage = 'read_transaction';
    const transaction = req.session.oidcTransaction;
    if (!transaction) {
      return callbackError(res, 400, 'Missing or already used login transaction');
    }

    // Consume and persist the transaction before any network request. An
    // authorization callback cannot deliberately reuse the same transaction.
    // Before the first session save
    stage = 'consume_transaction';
    delete req.session.oidcTransaction;
    await saveSession(req);

    // Before calling discoverProvider()
    
    const { code, state, error: providerError } = req.query;
    const age = Date.now() - transaction.createdAt;
    if (!Number.isFinite(age) || age < 0 || age > TRANSACTION_MAX_AGE_MS ||
        !constantTimeEqual(state, transaction.state)) {
      return callbackError(res, 400, 'Invalid or expired login transaction');
    }

    if (providerError !== undefined) {
      return callbackError(res, 400, 'Login was not completed at Charter26');
    }
    if (typeof code !== 'string' || code.length < 1 || code.length > 256 ||
        typeof transaction.codeVerifier !== 'string' ||
        !/^[A-Za-z0-9_-]{43}$/.test(transaction.codeVerifier) ||
        typeof transaction.nonce !== 'string') {
      return callbackError(res, 400, 'Invalid authorization response');
    }

    stage = 'validate_callback_configuration';  
    if (!clientSecret || !accessAudience) {
      throw new Error('Missing OIDC callback configuration');
    }

    // Before validating token endpoint metadata
  
    // Before fetching the token endpoint
    stage = 'oidc_discovery';
    const metadata = await discoverProvider();
    // Strictly trust only the configured SSO origin for token exchange/JWKS.

    for (const field of ['token_endpoint', 'jwks_uri']) {
      const endpoint = new URL(metadata[field]);
      if (endpoint.protocol !== 'https:' || endpoint.origin !== normalizedIssuer ||
          endpoint.username || endpoint.password || endpoint.hash) {
        throw new Error(`Invalid OIDC ${field}`);
      }
    }


    if (!metadata.token_endpoint_auth_methods_supported?.includes('client_secret_basic') ||
        !metadata.id_token_signing_alg_values_supported?.includes('RS256')) {
      throw new Error('Required OIDC token capabilities unavailable');
    }


    const form = new URLSearchParams({
      grant_type: 'authorization_code',
      code,
      redirect_uri: redirectUri,
      code_verifier: transaction.codeVerifier,
    });

    // Charter26 implements client_secret_basic per its discovery metadata.
    // Percent encoding protects client IDs/secrets containing ':' or special chars.
    const credentials = Buffer.from(
      `${encodeURIComponent(clientId)}:${encodeURIComponent(clientSecret)}`,
      'utf8',
    ).toString('base64');

    stage = 'token_exchange';
    const response = await fetch(metadata.token_endpoint, {
      method: 'POST',
      signal: AbortSignal.timeout(10000),
      headers: {
        Authorization: `Basic ${credentials}`,
        'Content-Type': 'application/x-www-form-urlencoded',
        Accept: 'application/json',
      },
      body: form,
    });

    if (!response.ok) {
      // Do not log the token endpoint response; it may contain sensitive data.
      console.warn(JSON.stringify({ event: 'oidc_token_exchange_failed',
        requestId: req.requestId, status: response.status }));
      return callbackError(res, 401, 'Authorization code exchange failed');
    }

    // Before retrieving JWKS and verifying JWTs
    stage = 'parse_token_response';
    const tokens = await response.json();
    if (typeof tokens.id_token !== 'string' ||
        typeof tokens.access_token !== 'string' ||
        typeof tokens.refresh_token !== 'string' ||
        tokens.token_type?.toLowerCase() !== 'bearer' ||
        !Number.isFinite(tokens.expires_in) || tokens.expires_in <= 0) {
      throw new Error('Invalid OIDC token response');
    }

    stage = 'jwt_validation';  
    const jwks = createRemoteJWKSet(new URL(metadata.jwks_uri), {
      timeoutDuration: 10000,
      cooldownDuration: 30000,
    });
    const options = {
      issuer: normalizedIssuer,
      algorithms: ['RS256'],
      clockTolerance: 15,
      requiredClaims: ['sub', 'iat', 'exp'],
    };
    const { payload: identity } = await jwtVerify(tokens.id_token, jwks, {
      ...options,
      audience: clientId,
      requiredClaims: [...options.requiredClaims, 'nonce'],
    });
    const { payload: access } = await jwtVerify(tokens.access_token, jwks, {
      ...options,
      audience: accessAudience,
    });

    if (!constantTimeEqual(identity.nonce, transaction.nonce) ||
        !identity.sub || identity.sub !== access.sub ||
        access.client_id !== clientId ||
        !String(access.scope || '').split(' ').includes('openid')) {
      return callbackError(res, 401, 'OIDC token validation failed');
    }

    // Before regenerating the session
    stage = 'regenerate_session';
    // Regenerate only after successful token validation (session fixation defense).
    await regenerateSession(req);
    req.session.auth = {
      sub: identity.sub,
      roles: Array.isArray(access.roles) ? access.roles : [],
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      accessTokenExpiresAt: Date.now() + tokens.expires_in * 1000,
      authenticatedAt: Date.now(),
    };
    
    // Before saving the new authenticated session
    stage = 'save_authenticated_session';
    await saveSession(req);
    return res.redirect(302, '/');
  } catch (error) {
    // Send detailed operational errors only to server logs. Never log credentials.
    console.error(JSON.stringify({
      event: 'oidc_callback_error',
      requestId: req.requestId,
      stage: stage,
      errorType: error?.name || 'Error',
      errorCode: error?.code || null,
    }));
    return callbackError(res, 502, 'Unable to complete authentication');
  }

}

export async function oidcLogin(req, res, next) {
  try {
    if (!req.secure) {
      return res.status(400).json({
        message: 'HTTPS required',
      });
    }

    const metadata = await discoverProvider();

    // Generate a fresh authorization transaction.
    const codeVerifier = randomValue();
    const codeChallenge = generatePkceChallenge(codeVerifier);
    const state = randomValue();
    const nonce = randomValue();

    // Keep transaction secrets exclusively on the server.
    req.session.oidcTransaction = {
      state,
      nonce,
      codeVerifier,
      createdAt: Date.now(),
    };

    const authorizationUrl = new URL(
      metadata.authorization_endpoint
    );

    authorizationUrl.searchParams.set(
      'response_type', 'code'
    );
    authorizationUrl.searchParams.set(
      'client_id', clientId
    );
    authorizationUrl.searchParams.set(
      'redirect_uri', redirectUri
    );
    authorizationUrl.searchParams.set(
      'scope', 'openid profile'
    );
    authorizationUrl.searchParams.set(
      'state', state
    );
    authorizationUrl.searchParams.set(
      'nonce', nonce
    );
    authorizationUrl.searchParams.set(
      'code_challenge', codeChallenge
    );
    authorizationUrl.searchParams.set(
      'code_challenge_method', 'S256'
    );

    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('Referrer-Policy', 'no-referrer');

    // Persist before redirecting the browser.
    req.session.save((error) => {
      if (error) {
        return next(error);
      }

      return res.redirect(302, authorizationUrl.toString());
    });

  } catch (error) {
    next(error);
  }
}


// Avoid exposing raw authorization codes, tokens, or session identifiers in errors.
function callbackError(res, status, message) {
  return res.status(status).json({ message });
}

function constantTimeEqual(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string') return false;
  const left = Buffer.from(a, 'utf8');
  const right = Buffer.from(b, 'utf8');
  return left.length === right.length && timingSafeEqual(left, right);
}

function saveSession(req) {
  return new Promise((resolve, reject) => {
    req.session.save((error) => error ? reject(error) : resolve());
  });
}

function regenerateSession(req) {
  return new Promise((resolve, reject) => {
    req.session.regenerate((error) => error ? reject(error) : resolve());
  });
}