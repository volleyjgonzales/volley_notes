// @ts-check
import { defineConfig } from 'astro/config';

// One static page (index.html) that holds all three documents as tabs.
// Figures are copied from ../figures into public/figures by scripts/sync-figures.mjs.
export default defineConfig({
  output: 'static',
  build: { inlineStylesheets: 'always', format: 'file' },
  devToolbar: { enabled: false },
});
