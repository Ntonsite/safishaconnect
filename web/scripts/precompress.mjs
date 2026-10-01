// Precompress text assets after `vite build` so nginx can serve them with `gzip_static`
// (maximum compression, zero per-request CPU). Images and fonts are already compressed.
import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { constants, gzipSync } from "node:zlib";

const root = process.argv[2] ?? "dist";
const TEXT = /\.(js|css|html|svg|json|txt|map)$/;
let saved = 0;
function walk(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) walk(path);
    else if (TEXT.test(name) && statSync(path).size > 1024) {
      const raw = readFileSync(path);
      const gz = gzipSync(raw, { level: constants.Z_BEST_COMPRESSION });
      writeFileSync(`${path}.gz`, gz);
      saved += raw.length - gz.length;
    }
  }
}
walk(root);
console.log(`precompressed text assets in ${root} (saves ${(saved / 1024).toFixed(0)} KB per cold visit set)`);
