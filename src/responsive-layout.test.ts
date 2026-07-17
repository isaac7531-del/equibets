import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const readStyles = () => readFileSync(join(process.cwd(), 'src/styles.css'), 'utf-8');

describe('responsive layout contract', () => {
  it('allows workspace grid children to shrink below their intrinsic width', () => {
    expect(readStyles()).toMatch(/\.workspace-grid\s*>\s*\*\s*{[^}]*min-width:\s*0\s*;/s);
  });
});
