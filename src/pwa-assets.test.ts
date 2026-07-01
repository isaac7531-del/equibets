import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const readWorkspaceFile = (filePath: string) => readFileSync(join(process.cwd(), filePath), 'utf-8');

describe('PWA asset contract', () => {
  it('defines an installable standalone manifest', () => {
    const manifest = JSON.parse(readWorkspaceFile('public/manifest.webmanifest'));

    expect(manifest.name).toBe('Equibets Eventing Form Guide');
    expect(manifest.display).toBe('standalone');
    expect(manifest.start_url).toBe('/');
    expect(manifest.icons[0].src).toBe('/app-icon.svg');
  });

  it('links app metadata from the document head', () => {
    const html = readWorkspaceFile('index.html');

    expect(html).toContain('<link rel="manifest" href="/manifest.webmanifest" />');
    expect(html).toContain('<meta name="theme-color" content="#23432d" />');
    expect(html).toContain('<link rel="canonical" href="https://equibets.app/" />');
    expect(html).toContain('<meta property="og:url" content="https://equibets.app/" />');
    expect(html).toContain('<link rel="apple-touch-icon" href="/app-icon.svg" />');
  });

  it('serves the app shell through the service worker', () => {
    const serviceWorker = readWorkspaceFile('public/sw.js');

    expect(serviceWorker).toContain("const CACHE_NAME = 'equibets-app-shell-v1'");
    expect(serviceWorker).toContain("'/manifest.webmanifest'");
    expect(serviceWorker).toContain("caches.match('/index.html')");
  });

  it('publishes crawler metadata for equibets.app', () => {
    const robots = readWorkspaceFile('public/robots.txt');
    const sitemap = readWorkspaceFile('public/sitemap.xml');

    expect(robots).toContain('Sitemap: https://equibets.app/sitemap.xml');
    expect(sitemap).toContain('<loc>https://equibets.app/</loc>');
  });
});
