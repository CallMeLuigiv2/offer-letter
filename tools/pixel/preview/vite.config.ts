import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Serves the real office code (web/src/office) and assets (web/public) with
// this harness's own phaser/easystarjs/react, so it works before web/ has them.
const here = path.dirname(fileURLToPath(import.meta.url));
const web = path.resolve(here, '../../../web');
const nm = (p: string) => path.join(here, 'node_modules', p);

export default defineConfig({
  root: here,
  plugins: [react()],
  publicDir: path.join(web, 'public'),
  resolve: {
    alias: [
      { find: /^phaser$/, replacement: nm('phaser/dist/phaser.esm.js') },
      { find: /^easystarjs$/, replacement: nm('easystarjs/src/easystar.js') },
      { find: /^react$/, replacement: nm('react') },
      { find: /^react\/(.*)$/, replacement: nm('react') + '/$1' },
      { find: /^react-dom$/, replacement: nm('react-dom') },
      { find: /^react-dom\/(.*)$/, replacement: nm('react-dom') + '/$1' },
      { find: /^@office\/(.*)$/, replacement: path.join(web, 'src/office') + '/$1' },
    ],
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-dom/client', 'react/jsx-runtime', 'react/jsx-dev-runtime', 'easystarjs'],
  },
  server: {
    host: '127.0.0.1',
    port: 5180,
    strictPort: true,
    fs: { allow: [here, path.join(web, 'src', 'office'), path.join(web, 'public')] },
  },
});
