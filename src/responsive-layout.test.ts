import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const readStyles = () => readFileSync(join(process.cwd(), 'src/styles.css'), 'utf-8');

describe('responsive layout contract', () => {
  it('allows workspace grid children to shrink below their intrinsic width', () => {
    expect(readStyles()).toMatch(/\.workspace-grid\s*>\s*\*\s*{[^}]*min-width:\s*0\s*;/s);
  });

  it('allows the live-score date window to wrap on narrow screens', () => {
    expect(readStyles()).toMatch(
      /@media\s*\(max-width:\s*620px\)[\s\S]*\.freshness-pill\s*{[^}]*white-space:\s*normal\s*;/,
    );
  });

  it('allows live-event source text to shrink and wrap on narrow screens', () => {
    expect(readStyles()).toMatch(
      /@media\s*\(max-width:\s*620px\)[\s\S]*\.live-event header p\s*{[^}]*max-width:\s*100%\s*;[^}]*min-width:\s*0\s*;[^}]*overflow-wrap:\s*anywhere\s*;[^}]*white-space:\s*normal\s*;/,
    );
  });

  it('removes the desktop breakdown width from mobile leaderboard rows', () => {
    expect(readStyles()).toMatch(
      /@media\s*\(max-width:\s*620px\)[\s\S]*\.live-event tbody td:nth-child\(4\)\s*{[^}]*width:\s*auto\s*;/,
    );
    expect(readStyles()).toMatch(
      /@media\s*\(max-width:\s*620px\)[\s\S]*\.live-breakdown-cell\s*{[^}]*column-gap:\s*0\.2rem\s*;/,
    );
  });
});
