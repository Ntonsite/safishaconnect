/** Route chunks that are worth warming before the user asks for them. */
export const loadAuthPages = () => import("./features/public/AuthPages");

/**
 * Sign-in is the next step for almost every visitor ("Book a cleaning" requires it), so fetch
 * that chunk once the browser is idle — unless the user has asked to save data.
 */
export function prefetchLikelyNextChunks() {
  const connection = (navigator as Navigator & { connection?: { saveData?: boolean } }).connection;
  if (connection?.saveData) return;
  const run = () => void loadAuthPages();
  if ("requestIdleCallback" in window) window.requestIdleCallback(run, { timeout: 4000 });
  else setTimeout(run, 2500);
}
