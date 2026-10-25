/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
	plugins: [react()],
	server: { proxy: { "/api": "http://localhost:8000" } },
	test: {
		environment: "jsdom",
		unstubGlobals: true,
		include: ["src/**/*.test.{ts,tsx}"],
		coverage: {
			include: ["src/**"],
			exclude: ["src/main.tsx", "src/api/schema.d.ts"],
			thresholds: { 100: true },
		},
	},
});
