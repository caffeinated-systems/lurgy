/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
	plugins: [react()],
	// Into api/: Laravel Cloud ships only the app's root directory (#34).
	build: { outDir: "../api/static", emptyOutDir: true },
	server: {
		proxy: { "/api": "http://localhost:8000" },
		// Test output, rewritten on every run: watching it reloads the open page.
		watch: {
			ignored: [
				"**/coverage/**",
				"**/test-results/**",
				"**/playwright-report/**",
			],
		},
	},
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
