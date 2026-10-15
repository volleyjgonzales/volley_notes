// Copy the generated figures (../figures) into public/figures so the site can serve them.
// The figures themselves are built by ../scripts/diagrams/build.py and committed there.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.resolve(here, '../../figures');
const dst = path.resolve(here, '../public/figures');
fs.rmSync(dst, { recursive: true, force: true });
fs.mkdirSync(dst, { recursive: true });
let n = 0;
for (const f of fs.readdirSync(src)) {
  if (!/\.(svg|html)$/.test(f)) continue;
  fs.copyFileSync(path.join(src, f), path.join(dst, f));
  n++;
}
console.log(`sync-figures: ${n} files -> public/figures`);
