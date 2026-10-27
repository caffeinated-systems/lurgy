import { defineConfig } from "@playwright/test";

export default defineConfig({
	testDir: "e2e",
	forbidOnly: !!process.env.CI,
	use: { baseURL: "http://localhost:8123", trace: "retain-on-failure" },
	webServer: {
		command:
			"npm run build && uv run --directory ../api uvicorn tests.e2e:app --port 8123",
		url: "http://localhost:8123/api/health",
		env: { PUZZLES_DIR: "tests/fixtures/puzzles" },
		reuseExistingServer: !process.env.CI,
	},
});
