import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { App } from "./App.tsx";

test("shows the API health", async () => {
	vi.stubGlobal(
		"fetch",
		vi.fn(() => Promise.resolve(Response.json({ status: "ok" }))),
	);

	render(<App />);

	expect(await screen.findByText("Office bug: ok")).toBeDefined();
	expect(fetch).toHaveBeenCalledWith("/api/health");
});
