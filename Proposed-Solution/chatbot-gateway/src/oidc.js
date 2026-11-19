
import { createHash, randomBytes } from 'node:crypto';

const issuer = process.env.OIDC_ISSUER;
const clientId = process.env.OIDC_CLIENT_ID;
const redirectUri = process.env.OIDC_REDIRECT_URI;

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
