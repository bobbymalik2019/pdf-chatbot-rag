export async function getAuthenticatedUser() {
  const response = await fetch('/auth/me', {
    credentials: 'same-origin',
    cache: 'no-store',
  });

  if (response.status === 401) return null;
  if (!response.ok) throw new Error('Failed to load authenticated user');

  const body = await response.json();
  return body.user;
}

export async function signOut() {
  const response = await fetch('/auth/logout', {
    method: 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
  });
  if (!response.ok) throw new Error('Failed to sign out');
}
