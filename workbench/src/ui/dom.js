/** Tiny DOM helpers — no framework, no build step. */

/**
 * Escape a value for safe interpolation into HTML.
 * @param {any} value
 * @returns {string}
 */
export function esc(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

/**
 * @param {string} html
 * @returns {HTMLElement}
 */
export function htmlToElement(html) {
  const template = document.createElement("template");
  template.innerHTML = html.trim();
  return template.content.firstElementChild;
}

/**
 * @param {string} selector
 * @param {string} event
 * @param {ParentNode} root
 * @param {(event: Event, target: HTMLElement) => void} handler
 */
export function delegate(root, selector, event, handler) {
  root.addEventListener(event, (evt) => {
    const target = evt.target instanceof Element ? evt.target.closest(selector) : null;
    if (target && root.contains(target)) handler(evt, /** @type {HTMLElement} */ (target));
  });
}

/**
 * @param {number} value
 * @param {number} total
 * @returns {number} 0..100
 */
export function percent(value, total) {
  if (!total) return 0;
  return Math.round((value / total) * 1000) / 10;
}

/**
 * Trigger a client-side file download.
 * @param {string} filename
 * @param {any} payload
 */
export function downloadJson(filename, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
