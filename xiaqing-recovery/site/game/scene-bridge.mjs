// Adapt the original character lab only when it is embedded in the game.
export function createGameBridge() {
  const enabled = new URLSearchParams(location.search).get('gamePreview') === '1' && parent !== window;
  const state = {timeScale: 1, moveMultiplier: 1, allowRun: true, blocked: false};
  const pending = {run: 0, walk: 0};
  let elapsed = 0, actionHandler = () => {};
  if (enabled) {
    document.documentElement.classList.add('game-preview');
    window.addEventListener('message', event => {
      if (event.origin !== location.origin || event.source !== parent || event.data?.type !== 'hero13-state') return;
      const data = event.data;
      if (Number.isFinite(data.timeScale)) state.timeScale = Math.max(0, Math.min(1, data.timeScale));
      if (Number.isFinite(data.moveMultiplier)) state.moveMultiplier = Math.max(0, Math.min(3, data.moveMultiplier));
      state.allowRun = data.allowRun !== false;
      state.blocked = data.blocked === true;
      if (state.blocked) actionHandler('Idle');
      else if (['Idle', 'Walk', 'Run'].includes(data.action)) actionHandler(data.action);
    });
    parent.postMessage({type: 'hero13-scene-ready'}, location.origin);
  }
  return {
    enabled, state,
    onAction(handler) { actionHandler = handler; },
    allows(name) { return !enabled || (!state.blocked && (name !== 'Run' || state.allowRun)); },
    moved(action, distance) { if (enabled && distance > 0 && action in pending) pending[action] += distance; },
    update(dt) {
      if (!enabled || (elapsed += dt) < .2) return;
      elapsed = 0;
      for (const action of ['run', 'walk']) {
        if (pending[action] > 0) parent.postMessage({type: 'hero13-motion', action, distance: pending[action]}, location.origin);
        pending[action] = 0;
      }
    }
  };
}
