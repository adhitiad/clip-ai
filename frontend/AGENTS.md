<!-- intent-skills:start -->

## Skill Loading

Use the repository’s installed Intent. If it is unavailable, report the missing dependency instead of downloading a replacement.
Before editing files for a substantial task:

- Run `bunx --no-install --package @tanstack/intent intent list` from the workspace root to see available local skills.
- If a listed skill matches the task, run `bunx --no-install --package @tanstack/intent intent load <package>#<skill>` before changing files.
- Use the loaded `SKILL.md` guidance while making the change.
- Monorepos: when working across packages, run the skill check from the workspace root and prefer the local skill for the package being changed.
- Multiple matches: prefer the most specific local skill for the package or concern you are changing; load additional skills only when the task spans multiple packages or concerns.

<!-- intent-skills:end -->

## Frontend Gate

Run all from `frontend/` with `bun`:

| Task                 | Command                                                   |
| -------------------- | --------------------------------------------------------- |
| Typecheck            | `bun --bun run typecheck` (`tsc --noEmit`)                |
| Lint                 | `bun --bun run lint` (eslint)                             |
| Format check / write | `bun --bun run check` / `bun --bun run format` (prettier) |
| Unit tests           | `bun --bun run test` (vitest)                             |
| E2E tests            | `bun --bun run test:e2e` (playwright)                     |
| Build                | `bun --bun run build` (vite)                              |

Directory layout:

- `src/type/` — TypeScript types and interfaces.
- `src/validation/` — Zod validation schemas.
- `tests/` — Vitest unit/component tests; config `vitest.config.ts`, setup `tests/setup.ts`.
- `e2e/` — Playwright end-to-end tests; config `playwright.config.ts`.
- `patches/` — Bun patches for `@inlang/paraglide-js` and `@inlang/sdk` (README `bunx` normalization).
- `scripts/normalize-i18n-docs.mjs` — safety net run on `postinstall`, `predev`, `prebuild`, `pregenerate-routes`.

## Style

Use arrow function expressions for every function in `src/`, `tests/`, `e2e/`, and config files. No `function` declarations or `export function`. For a named default export, write `const Name = () => ...` then `export default Name`. Exempt: `src/components/ui/**` (shadcn scaffold keeps `function` declarations) and generated files (`src/paraglide/**`, `src/routeTree.gen.ts`).

Use axios for backend HTTP calls inside server functions. Keep one configured instance with `baseURL`, `timeout`, and `paramsSerializer`. Send the backend JWT with `Authorization: Bearer <token>` per request. Native `fetch` is only for non-backend platform APIs.

Backend responses are the only source of truth for displayed data. Never hardcode domain data such as providers, models, prices, status, or counts in `src/`. UI-only constants like labels, dials, and nav labels are allowed. If data is missing, add a backend endpoint and update `docs/API.md` and the `README.md` API table before consuming it.

<!-- antislop:start -->

## antislop

For UI, copy, people, mobile layout, or code comments work, read the installed skills first:

- Core: `C:/Users/humas/.config/opencode/skills/antislop/SKILL.md`
- UI / visual: `C:/Users/humas/.config/opencode/skills/antislop-ui/SKILL.md`
- Copy & text: `C:/Users/humas/.config/opencode/skills/antislop-copywriting/SKILL.md`
- People: `C:/Users/humas/.config/opencode/skills/antislop-human/SKILL.md`
- Mobile / responsive: `C:/Users/humas/.config/opencode/skills/antislop-layoutmobile/SKILL.md`
- Code comments: `C:/Users/humas/.config/opencode/skills/antislop-code/SKILL.md`

Before starting, ask the user when antislop applies: during the work, or after it is done.
<!-- antislop:end -->
