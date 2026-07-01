import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const readWorkspaceFile = (filePath: string) => readFileSync(join(process.cwd(), filePath), 'utf-8');

describe('deployment config', () => {
  it('configures Vercel for the Vite static app', () => {
    const config = JSON.parse(readWorkspaceFile('vercel.json'));

    expect(config.framework).toBe('vite');
    expect(config.buildCommand).toBe('npm run build');
    expect(config.outputDirectory).toBe('dist');
    expect(config.rewrites[0].destination).toBe('/index.html');
  });

  it('configures Netlify build output and redirects', () => {
    const config = readWorkspaceFile('netlify.toml');
    const redirects = readWorkspaceFile('public/_redirects');

    expect(config).toContain('command = "npm ci && npm run build"');
    expect(config).toContain('publish = "dist"');
    expect(config).toContain('https://www.equibets.app/*');
    expect(redirects).toContain('https://www.equibets.app/* https://equibets.app/:splat 301!');
    expect(redirects).toContain('/* /index.html 200');
  });
});
