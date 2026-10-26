#!/bin/sh
# Laravel Cloud's build command (environment Settings > Deployments): sh bin/cloud-build.sh
# It runs from api/, the app's root, and only api/ ships, so everything lands inside it.
set -eu

# Built Weeks hold solutions, so they come from the private repo, never this one
# (ADR 0002). Cloud's build has git but no ssh: HTTPS with a read-only token.
rm -rf puzzles
git clone --quiet --depth 1 \
	"https://x-access-token:${PUZZLES_TOKEN}@github.com/caffeinated-systems/lurgy-puzzles.git" \
	puzzles
# The clone's .git/config holds the token; nothing needs it after this.
rm -rf puzzles/.git
# The clone is quiet; this shows in the build log which Weeks shipped.
ls puzzles

cd ../web
# vite and typescript are devDependencies, needed even if NODE_ENV=production.
npm ci --include=dev
npm run build
