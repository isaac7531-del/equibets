export const registerServiceWorker = (appWindow: Window & typeof globalThis = window) => {
  if (!('serviceWorker' in appWindow.navigator)) {
    return false;
  }

  appWindow.addEventListener('load', () => {
    appWindow.navigator.serviceWorker.register('/sw.js').catch(() => undefined);
  });
  return true;
};
