/**
 * agent-muster registry for Pi.
 *
 * Publishes this Pi process's live state so agent-muster (Emacs) can list
 * Pi sessions that run outside Emacs, the way it lists Claude Code
 * terminal sessions from ~/.claude/sessions.
 *
 * One file per Pi process, <agent-dir>/registry/<pid>.json, written on
 * every state change and removed when the session shuts down.  The agent
 * dir is Pi's own (`PI_CODING_AGENT_DIR`, default ~/.pi/agent).
 *
 * Status uses Claude's words, so agent-muster maps both the same way:
 *   "busy"     the agent is running (agent_start .. agent_settled)
 *   "waiting"  a blocking extension dialog is open -- select, confirm,
 *              input, editor or custom, from *any* extension: Pi wraps
 *              the one UI context every extension's `ctx.ui` returns and
 *              emits ui_prompt_start/ui_prompt_end around each dialog
 *   "idle"     neither
 * `waitingFor` names the open dialog, "<kind>: <title>", which agent-muster
 * shows in its Turn column.
 *
 * Each entry holds the session's cwd and the head of its first prompt, so
 * the directory is private to its owner (0700) and so is each file (0600).
 *
 * A crash skips session_shutdown and leaves the file behind, so readers
 * must check the pid is alive and that its start time matches
 * `procStart` (epoch milliseconds, accurate to about a second) before
 * trusting an entry.
 *
 * Install: copy or symlink this file into <agent-dir>/extensions/, then
 * start Pi or run /reload in a running session.
 */

import { chmodSync, mkdirSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { getAgentDir, VERSION } from "@earendil-works/pi-coding-agent";

/** Bump when a field changes meaning, so readers can refuse what they do not know. */
const SCHEMA_VERSION = 1;
/** Characters of the first prompt kept as a fallback title. */
const TITLE_LENGTH = 80;

type Status = "idle" | "busy" | "waiting";

interface Session {
	sessionId: string;
	sessionFile: string | undefined;
	cwd: string;
	mode: string;
	name: string | undefined;
	title: string | undefined;
}

/** First user prompt on the current branch, flattened to one line, or undefined. */
function firstPrompt(ctx: ExtensionContext): string | undefined {
	for (const entry of ctx.sessionManager.getBranch()) {
		if (entry.type !== "message" || entry.message.role !== "user") continue;
		const content = entry.message.content;
		const text =
			typeof content === "string"
				? content
				: content
						.filter((part) => part.type === "text")
						.map((part) => (part as { text: string }).text)
						.join(" ");
		const line = text.replace(/\s+/g, " ").trim();
		if (line) return line.length > TITLE_LENGTH ? `${line.slice(0, TITLE_LENGTH - 1)}…` : line;
	}
	return undefined;
}

export default function agentMusterRegistry(pi: ExtensionAPI) {
	const directory = join(getAgentDir(), "registry");
	const file = join(directory, `${process.pid}.json`);
	// When this process started, so a reader can tell it from a later
	// process that reuses the pid.
	const procStart = Math.round(Date.now() - process.uptime() * 1000);

	let session: Session | undefined;
	let running = false;
	let waitingFor: string | undefined;
	// Whether this process has made the directory private.  Once is enough:
	// mkdirSync applies its mode only to a directory it creates, so the
	// chmod is for one an earlier version of this file made world-readable.
	let secured = false;

	const status = (): Status => (waitingFor ? "waiting" : running ? "busy" : "idle");

	// Best effort throughout: a registry that cannot be written must never
	// break the session it describes.
	const write = () => {
		if (!session) return;
		try {
			mkdirSync(directory, { recursive: true, mode: 0o700 });
			if (!secured) {
				chmodSync(directory, 0o700);
				secured = true;
			}
			const temporary = `${file}.tmp`;
			// writeFileSync applies its mode only to a file it creates, and a
			// crash mid-write can leave this one behind with any mode at all.
			rmSync(temporary, { force: true });
			writeFileSync(
				temporary,
				JSON.stringify({
					version: SCHEMA_VERSION,
					pid: process.pid,
					procStart,
					...session,
					status: status(),
					waitingFor: waitingFor ?? null,
					piVersion: VERSION,
					updatedAt: Date.now(),
				}),
				{ mode: 0o600 },
			);
			// Atomic, so a reader never sees half a file.
			renameSync(temporary, file);
		} catch {
			// Ignored; see above.
		}
	};

	const remove = () => {
		try {
			rmSync(file, { force: true });
		} catch {
			// Ignored.
		}
	};

	const capture = (ctx: ExtensionContext) => {
		const manager = ctx.sessionManager;
		session = {
			sessionId: manager.getSessionId(),
			sessionFile: manager.getSessionFile(),
			cwd: ctx.cwd,
			mode: ctx.mode,
			name: manager.getSessionName(),
			title: firstPrompt(ctx),
		};
	};

	pi.on("session_start", (_event, ctx) => {
		capture(ctx);
		// Registered here rather than in the factory, which Pi also runs
		// without a session.  The flag keeps /reload from stacking handlers.
		const flag = Symbol.for("agent-muster-registry.exit-hook");
		const registry = globalThis as Record<symbol, boolean>;
		if (!registry[flag]) {
			registry[flag] = true;
			process.once("exit", remove);
		}
		write();
	});

	pi.on("session_info_changed", (event) => {
		if (!session) return;
		session.name = event.name;
		write();
	});

	pi.on("agent_start", (_event, ctx) => {
		running = true;
		if (session && !session.title) session.title = firstPrompt(ctx);
		write();
	});

	// agent_settled rather than agent_end: Pi can continue after agent_end
	// (retries, compaction, queued work), and only settled is final.
	pi.on("agent_settled", (_event, ctx) => {
		running = false;
		if (session && !session.title) session.title = firstPrompt(ctx);
		write();
	});

	pi.on("ui_prompt_start", (event) => {
		waitingFor = event.title ? `${event.kind}: ${event.title}` : event.kind;
		write();
	});

	pi.on("ui_prompt_end", () => {
		waitingFor = undefined;
		write();
	});

	pi.on("session_shutdown", () => {
		session = undefined;
		running = false;
		waitingFor = undefined;
		remove();
	});
}
