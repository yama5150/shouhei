import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { viteSingleFile } from 'vite-plugin-singlefile';

// base: './' で相対パスにし、raw.githack や任意の場所からそのまま開けるようにする。
// viteSingleFile で JS/CSS を 1 つの index.html に丸ごと埋め込む（ビルド不要で配布できる）。
export default defineConfig({
  base: './',
  plugins: [react(), viteSingleFile()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // ソースの入口は app.html（ビルド成果物を root の index.html に置くため衝突を避ける）
    rollupOptions: { input: 'app.html' },
  },
});
