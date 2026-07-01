import { describe, expect, it, vi } from 'vitest';
import { registerServiceWorker } from './pwa';

describe('registerServiceWorker', () => {
  it('registers the service worker after window load when supported', () => {
    const loadHandlers: Array<() => void> = [];
    const register = vi.fn().mockResolvedValue(undefined);
    const appWindow = {
      addEventListener: vi.fn((event: string, handler: () => void) => {
        if (event === 'load') {
          loadHandlers.push(handler);
        }
      }),
      navigator: {
        serviceWorker: {
          register,
        },
      },
    } as unknown as Window & typeof globalThis;

    const isSupported = registerServiceWorker(appWindow);
    loadHandlers.forEach((handler) => handler());

    expect(isSupported).toBe(true);
    expect(register).toHaveBeenCalledWith('/sw.js');
  });

  it('does not register when service workers are unsupported', () => {
    const appWindow = {
      addEventListener: vi.fn(),
      navigator: {},
    } as unknown as Window & typeof globalThis;

    expect(registerServiceWorker(appWindow)).toBe(false);
    expect(appWindow.addEventListener).not.toHaveBeenCalled();
  });
});
