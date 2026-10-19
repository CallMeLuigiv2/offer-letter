import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

const API = process.env.OL_API ?? 'http://127.0.0.1:8765';

export default defineConfig({
  plugins: [react()],
  build: { target: 'es2022' },
  server: {
    port: 5173,
    fs: { allow: ['..'] },
    proxy: {
      '/api': API,
      '/ws': { target: API.replace(/^http/, 'ws'), ws: true },
      ...(process.env.VITE_MOCK === '1' ? {} : { '/portraits': API }),
    },
  },
  test: {
    environment: 'jsdom',
    env: { VITE_MOCK_FAST: '1' },
    globals: true,
    setupFiles: ['src/test-setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
});
