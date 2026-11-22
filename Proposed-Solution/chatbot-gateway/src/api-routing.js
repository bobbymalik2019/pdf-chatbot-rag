/**
 * Pure routing decision, independently unit-testable.
 * Only documented Chat History routes go to :8001.
 */
export function selectApiUpstream(originalUrl, ragOrigin, chatHistoryOrigin) {
  const pathname = new URL(originalUrl, 'http://localhost').pathname;
  const isProjectConversation =
    /^\/api\/v1\/projects\/[^/]+\/conversations\/?$/.test(pathname);
  const isConversation =
    /^\/api\/v1\/conversations\/[^/]+(?:\/messages)?\/?$/.test(pathname);
  return isProjectConversation || isConversation ? chatHistoryOrigin : ragOrigin;
}
