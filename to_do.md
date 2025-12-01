## TODOs

1. [ ] **Localize every user-facing message**
	- Drive all replies (Telegram + local) through the saved per-user language so menus, validation prompts, and error messages appear in Spanish or English consistently.
2. [ ] **Consolidate per-user settings into a single JSON file**
	- Replace the separate `.lang` and `.system` files with one JSON document (e.g., `SESSIONS/SETTINGS/<user>.json`) and ship migration helpers plus tests.
3. [ ] **Add Telegram inline keyboards for the landing menu**
	- Provide buttons for Play, Historial, Settings, and their sub-options to reduce friction when chatting with the bot.
4. [ ] **Build automated tests for config + session flows**
	- Cover language/system persistence, `/old_games` listing, migration from lowercase `sessions/`, and session CSV save/load helpers.
5. [ ] **Improve diagnostics & logging**
	- Surface migration/config write failures, add a `/status` command summarizing stored settings and recent sessions, and emit structured log lines for troubleshooting.
6. [ ] **Document a secure token-management strategy**
	- Decide whether the Telegram token should live in a central config file under `SESSIONS/SETTINGS/` (not per-user) and write guidance/tests around it.
