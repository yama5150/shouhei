import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { viteSingleFile } from 'vite-plugin-singlefile';
import tailwindcss from 'tailwindcss';
import autoprefixer from 'autoprefixer';

// 原価出しツール専用のビルド。焼肉ロス管理アプリ(vite.config.js)とは入口も出力も分ける。
// 成果物は genka/index.html 1ファイル。crc/ と同じく raw.githack からそのまま配信できる。
//
// postcss をここで閉じているのは、共有の tailwind.config.js に src/genka を足すと
// 既存アプリ側の CSS にも原価ツールのクラスが混ざるため。走査範囲をビルドごとに分ける。
export default defineConfig({
  base: './',
  plugins: [react(), viteSingleFile()],
  css: {
    postcss: {
      plugins: [
        tailwindcss({
          content: ['./genka-app.html', './src/genka/**/*.{js,jsx}'],
          theme: { extend: {} },
          plugins: [],
        }),
        autoprefixer(),
      ],
    },
  },
  build: {
    outDir: 'dist-genka',
    emptyOutDir: true,
    rollupOptions: { input: 'genka-app.html' },
  },
});
