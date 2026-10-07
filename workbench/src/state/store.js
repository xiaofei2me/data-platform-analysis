/**
 * Minimal observable store. State is a plain object; listeners run after each
 * patch so the UI can re-render its own section.
 */
export function createStore(initialState) {
  let state = { ...initialState };
  const listeners = new Set();

  return {
    /** @returns {typeof state} */
    getState() {
      return state;
    },

    /**
     * @param {Partial<typeof state>} patch
     * @param {{silent?: boolean}} [options]
     */
    setState(patch, options = {}) {
      state = { ...state, ...patch };
      if (!options.silent) {
        for (const listener of listeners) listener(state, patch);
      }
    },

    /** @param {(state: typeof state, patch: Partial<typeof state>) => void} listener */
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}
