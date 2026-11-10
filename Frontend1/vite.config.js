import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import process from "node:process";
import path from "node:path";

export default defineConfig(({ mode }) => {
  const envDir = path.resolve(process.cwd(), "..");
  const env = loadEnv(mode, envDir, "");
  const port = Number(env.VITE_PORT || 5173);

  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error("VITE_PORT must be a valid TCP port");
  }

  return {
    envDir,
    server: {
      host: "0.0.0.0",
      port,
      strictPort: true,
      allowedHosts: [".trycloudflare.com"],
    },
    plugins: [
      react(),
      tailwindcss(),
    ],
  };
});
