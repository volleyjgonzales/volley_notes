// Package dist/ as a claude.ai artifact: the hosted page supplies its own <!doctype>/<html>/<head>/<body>
// skeleton, so strip ours and keep the head's <title>, <meta>, <link> and <style> at the top of the file.
// Output: dist-artifact/index.html plus dist-artifact/figures/.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = fs.readFileSync(path.join(root, 'dist/index.html'), 'utf8');
const head = /<head>([\s\S]*?)<\/head>/.exec(html)[1];
const body = /<body[^>]*>([\s\S]*)<\/body>/.exec(html)[1];
const keepHead = head
  .replace(/<meta charset="utf-8"\s*\/?>/i, '')
  .replace(/<meta name="viewport"[^>]*>/i, '');
const out = path.join(root, 'dist-artifact');
fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out, { recursive: true });
fs.writeFileSync(path.join(out, 'index.html'), keepHead.trim() + '\n' + body.trim() + '\n');
fs.cpSync(path.join(root, 'dist/figures'), path.join(out, 'figures'), { recursive: true });
console.log('make-artifact: dist-artifact/index.html', (fs.statSync(path.join(out, 'index.html')).size / 1024).toFixed(0), 'KB');
