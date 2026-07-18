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
});
