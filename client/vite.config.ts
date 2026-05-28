import { sveltekit } from "@sveltejs/kit/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig, loadEnv } from "vite";

async function loadPwaPlugin() {
  try {
    const { VitePWA } = await import("vite-plugin-pwa");
    return VitePWA({
      injectRegister: false,
      registerType: "autoUpdate",
      // Keep SvelteKit's existing /service-worker.js as the active worker.
      manifest: false,
      filename: "pwa-sw.js",
      devOptions: {
        enabled: false,
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,ico,png,svg,webmanifest}"],
      },
    });
  } catch {
    return null;
  }
}

export default defineConfig(async ({ mode }) => {
  const env = loadEnv(mode, ".", "");
  const backendTarget = env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000";
  const pwa = await loadPwaPlugin();

  return {
    plugins: [tailwindcss(), sveltekit(), ...(pwa ? [pwa] : [])],
    server: {
      port: 5176,
      proxy: {
        "/api": {
          target: backendTarget,
          changeOrigin: true,
        },
        "/media": {
          target: backendTarget,
          changeOrigin: true,
        },
        "/ws": {
          target: backendTarget,
          changeOrigin: true,
          ws: true,
        },
      },
    },
  };
});
