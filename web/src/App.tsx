import { useEffect, useState } from "react";
import type { components } from "./api/schema";

type Health = components["schemas"]["Health"];

export function App() {
	const [status, setStatus] = useState<Health["status"]>();

	useEffect(() => {
		fetch("/api/health")
			.then((response) => response.json() as Promise<Health>)
			.then((health) => setStatus(health.status));
	}, []);

	return <h1>Office bug: {status ?? "…"}</h1>;
}
