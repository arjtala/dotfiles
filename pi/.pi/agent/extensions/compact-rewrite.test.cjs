"use strict";
// Test harness for compact-rewrite.ts.
//
// Loads the REAL extension (this directory) with its bare
// `@earendil-works/pi-coding-agent` import aliased to Pi's installed entry, so
// the actual convertToLlm/serializeConversation are exercised — no copying, no
// /tmp directory replacement. Only the model (modelRegistry.streamSimple) is
// mocked, since that is the external LLM.
//
// Run:  ~/.local/share/pi-node/current/bin/node compact-rewrite.test.cjs
//   (optionally set PI_NODE_MODULES to override where Pi's node_modules lives)

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const mod = require("node:module");

function findPiNodeModules() {
	if (process.env.PI_NODE_MODULES) return process.env.PI_NODE_MODULES;
	// Primary: the exact version Pi is running (install root + current-version file), so this
	// test always exercises the same Pi as the live harness after an upgrade or rollback —
	// not whichever release happens to sort last.
	const installRoot = process.env.PI_MANAGED_INSTALL_ROOT || path.join(os.homedir(), ".pi", "agent", "install");
	const base = path.join(installRoot, "releases");
	const hasPkg = (v) => fs.existsSync(path.join(base, v, "node_modules", "@earendil-works", "pi-coding-agent"));
	try {
		const cur = fs.readFileSync(path.join(installRoot, "current-version"), "utf8").trim();
		if (cur && hasPkg(cur)) return path.join(base, cur, "node_modules");
	} catch { /* no current-version file; fall through to newest release */ }
	// Fallback: newest installed release, in numeric (semver) order, not lexicographic.
	if (fs.existsSync(base)) {
		const vs = fs
			.readdirSync(base)
			.filter(hasPkg)
			.sort((a, b) => {
				const pa = a.split(".").map(Number);
				const pb = b.split(".").map(Number);
				for (let i = 0; i < 3; i++) if (pa[i] !== pb[i]) return pa[i] - pb[i];
				return 0;
			});
		if (vs.length) return path.join(base, vs[vs.length - 1], "node_modules");
	}
	throw new Error("Cannot locate Pi's node_modules. Set PI_NODE_MODULES to a node_modules dir containing @earendil-works/pi-coding-agent.");
}

const NM = findPiNodeModules();
const requireFromNM = mod.createRequire(path.join(NM, "noop.js"));
const createJiti = requireFromNM("jiti");
const PI_ENTRY = path.join(NM, "@earendil-works", "pi-coding-agent", "dist", "index.js");

const jiti = createJiti(__filename, {
	alias: { "@earendil-works/pi-coding-agent": PI_ENTRY },
	nativeModules: ["pi-coding-agent", "pi-ai"],
	tryNative: true,
	transformOptions: {},
});
const ext = jiti(path.join(__dirname, "compact-rewrite.ts")).default;
if (typeof ext !== "function") throw new Error("extension default export is not a function");

// --- tiny harness -----------------------------------------------------------

let passed = 0, failed = 0;
const failures = [];
function section(name) { console.log("\n" + name); }
function check(name, cond, detail) {
	if (cond) { passed++; console.log("  ok   " + name); }
	else { failed++; const m = name + (detail ? "  [" + detail + "]" : ""); failures.push(m); console.log("  FAIL " + m); }
}

const U = (n = 7) => ({
	input: 100, output: n, cacheRead: 0, cacheWrite: 0, totalTokens: 100 + n,
	cost: { input: 0.001, output: 0.0002, cacheRead: 0, cacheWrite: 0, total: 0.0012 },
});
const mkMsg = (text, over = 2000) => Array(over).fill(text).join(" ");
const comp = (r) => (r && r.compaction) || null;
const isCancel = (r) => !!(r && r.cancel === true);

let NOTIFIES = [];
function mkStream(responder) {
	const calls = [];
	const streamSimple = (model, context, options) => {
		const userText = context.messages[0].content;
		const r = responder
			? responder(userText, calls.length + 1, model, options)
			: { role: "assistant", content: [{ type: "text", text: "goal done" }], stopReason: "stop" };
		calls.push({ model, userText, options, context });
		return { result: async () => r, then: (res, rej) => Promise.resolve(r).then(res, rej) };
	};
	return { streamSimple, calls };
}
function mkCtx(stream, o = {}) {
	return {
		model: o.model,
		modelRegistry: { streamSimple: stream.streamSimple, find: o.find || (() => undefined) },
		ui: { notify: (m) => NOTIFIES.push(m) },
		log: () => {},
		sessionFile: "/tmp/s.jsonl", sessionId: "s", sessionStart: Date.now(),
	};
}
function mkEvent(prep) {
	// customInstructions lives on the event, not on preparation — pull it out so it is not
	// accidentally spread into preparation, and surface it at the top level like the real hook.
	const { customInstructions, ...rest } = prep;
	return {
		type: "session_before_compact", reason: "threshold", trigger: "auto",
		preparation: {
			...rest,
			turnPrefixMessages: rest.turnPrefixMessages ?? [],
			firstKeptEntryId: rest.firstKeptEntryId ?? "kept-1",
			tokensBefore: rest.tokensBefore ?? 50000,
			fileOps: rest.fileOps ?? { read: new Set(), written: new Set(), edited: new Set() },
		},
		customInstructions,
		signal: rest.signal ?? new AbortController().signal,
	};
}
async function run(ctx, event) {
	NOTIFIES = [];
	let handler;
	ext({ on: (name, h) => { if (name === "session_before_compact") handler = h; }, registerTool: () => {}, registerCommand: () => {} });
	return await handler(event, ctx);
}
const MODEL = { id: "m", provider: "p", api: "openai-completions", reasoning: false, maxTokens: 8192, contextWindow: 100000 };
const env = (k, v) => { if (v === undefined) delete process.env[k]; else process.env[k] = String(v); };
const clearEnv = () => ["PI_SUMMARY_MAX", "PI_SUMMARY_FAIL", "PI_SUMMARY_MODEL", "PI_SUMMARY_REWRITE"].forEach((k) => delete process.env[k]);

(async () => {
	// ---- success path + return contract (Fix #1) ----
	section("success path & return contract");
	{
		clearEnv();
		const stream = mkStream();
		const ctx = mkCtx(stream, { model: MODEL });
		const fileOps = {
			read: new Set(["a.md", "b.ts", "c.ts", "z.ts"]),
			written: new Set(["c.ts"]), edited: new Set(["b.ts"]),
		};
		const r = await run(ctx, mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }], fileOps }));
		check("returns a compaction wrapper (not a bare CompactionResult)", comp(r) !== null);
		check("summary preserved", comp(r) && comp(r).summary === "goal done");
		check("firstKeptEntryId preserved", comp(r) && comp(r).firstKeptEntryId === "kept-1");
		check("tokensBefore preserved", comp(r) && comp(r).tokensBefore === 50000);
		check("no estimatedTokensAfter (consumer recomputes)", comp(r) && !("estimatedTokensAfter" in comp(r)));
		check("no cancel flag on success", r.cancel === undefined);
		check("details.readFiles excludes modified files", comp(r) && JSON.stringify(comp(r).details.readFiles) === JSON.stringify(["a.md", "z.ts"]));
		check("details.modifiedFiles = edited ∪ written, sorted", comp(r) && JSON.stringify(comp(r).details.modifiedFiles) === JSON.stringify(["b.ts", "c.ts"]));
	}

	// ---- streaming/options policy ----
	section("stream & options policy");
	{
		clearEnv();
		const stream = mkStream();
		await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }));
		const c = stream.calls[0];
		check("maxTokens tracks the model's full allowance", c.options.maxTokens === 8192);
		check("cacheRetention is none", c.options.cacheRetention === "none");
		check("signal passed through", c.options.signal instanceof AbortSignal);
		check("non-reasoning model: no reasoning override", c.options.reasoning === undefined);
		check("single user message", c.context.messages.length === 1 && c.context.messages[0].role === "user");
		check("system prompt set (markdown-only summarizer)", typeof c.context.systemPrompt === "string" && c.context.systemPrompt.includes("Markdown"));
	}
	{
		clearEnv();
		const stream = mkStream();
		const reasoningModel = { ...MODEL, reasoning: true };
		await run(mkCtx(stream, { model: reasoningModel }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }));
		check("reasoning model: thinking pinned to minimal", stream.calls[0].options.reasoning === "minimal");
	}
	{
		clearEnv();
		const stream = mkStream();
		await run(mkCtx(stream, { model: { ...MODEL, maxTokens: 0 } }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }));
		check("maxTokens=0 → no maxTokens override", stream.calls[0].options.maxTokens === undefined);
	}

	// ---- over-ceiling rewrite (Fix #4: rewrite sees the draft) ----
	section("over-ceiling rewrite");
	{
		clearEnv();
		const draft = mkMsg("draft", 4000); // > 1500
		const final = mkMsg("tight", 900); // < 1500
		const stream = mkStream((t, i) => ({ role: "assistant", content: [{ type: "text", text: i === 1 ? draft : final }], stopReason: "stop" }));
		const ctx = mkCtx(stream, { model: MODEL });
		const r = await run(ctx, mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }));
		check("rewrite used when first is over ceiling", stream.calls.length === 2);
		check("final summary is the rewrite text", comp(r) && comp(r).summary === final);
		check("rewrite prompt includes the oversized draft (Fix #4)", stream.calls[1].userText.includes(draft.slice(0, 60)));
		check("rewrite prompt names the overage", stream.calls[1].userText.includes("over the 1500-word limit"));
	}
	{
		clearEnv();
		const over = mkMsg("still-over", 5000);
		const stream = mkStream(() => ({ role: "assistant", content: [{ type: "text", text: over }], stopReason: "stop" }));
		const r = await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }));
		check("still over after rewrite → cancel (default)", isCancel(r));
	}
	{
		clearEnv(); env("PI_SUMMARY_FAIL", "fallback");
		const over = mkMsg("still-over", 5000);
		const stream = mkStream(() => ({ role: "assistant", content: [{ type: "text", text: over }], stopReason: "stop" }));
		const r = await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }));
		check("still over after rewrite → undefined (fallback)", r === undefined);
		clearEnv();
	}
	{
		clearEnv();
		const draft = mkMsg("draft", 4000);
		const stream = mkStream((t, i) => i === 1
			? { role: "assistant", content: [{ type: "text", text: draft }], stopReason: "stop" }
			: { role: "assistant", content: [], stopReason: "stop" }); // empty rewrite
		const r = await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }));
		check("empty rewrite → cancel", isCancel(r));
	}

	// ---- rewrite is draft-only: it does NOT resend the conversation (context-pressure guard) ----
	section("rewrite does not resend the conversation");
	{
		clearEnv();
		const draft = mkMsg("draft", 4000);
		const final = mkMsg("tight", 900);
		const stream = mkStream((t, i) => ({ role: "assistant", content: [{ type: "text", text: i === 1 ? draft : final }], stopReason: "stop" }));
		await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "CONV-FACT-XYZ" }] }));
		check("two calls (draft over ceiling → rewrite)", stream.calls.length === 2);
		check("generation call DOES include the conversation", stream.calls[0].userText.includes("CONV-FACT-XYZ"));
		check("rewrite call does NOT resend the conversation", !stream.calls[1].userText.includes("CONV-FACT-XYZ"));
		check("rewrite call still carries the oversized draft", stream.calls[1].userText.includes(draft.slice(0, 60)));
	}

	// ---- manual compaction instructions (event.customInstructions) ----
	section("manual compaction instructions");
	{
		clearEnv();
		const draft = mkMsg("draft", 4000);
		const final = mkMsg("tight", 900);
		const stream = mkStream((t, i) => ({ role: "assistant", content: [{ type: "text", text: i === 1 ? draft : final }], stopReason: "stop" }));
		await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }], customInstructions: "KEEP-ROLLBACK-STEPS" }));
		check("custom instructions reach the generation prompt", stream.calls[0].userText.includes("KEEP-ROLLBACK-STEPS"));
		check("custom instructions reach the rewrite prompt", stream.calls.length === 2 && stream.calls[1].userText.includes("KEEP-ROLLBACK-STEPS"));
	}
	{
		clearEnv();
		const stream = mkStream();
		await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }));
		check("no customInstructions → no instruction text in prompt", !stream.calls[0].userText.includes("User instructions for THIS summary"));
	}

	// ---- invalid-summary rejection ----
	section("invalid summary rejection");
	{
		clearEnv();
		const stream = mkStream(() => ({ role: "assistant", content: [{ type: "text", text: "ok" }, { type: "toolCall", name: "bash", arguments: {} }], stopReason: "stop" }));
		check("tool call in summary → cancel", isCancel(await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }))));
	}
	{
		clearEnv();
		const stream = mkStream(() => ({ role: "assistant", content: [{ type: "text", text: mkMsg("x", 500) }], stopReason: "length" }));
		check("output cap (length) → cancel", isCancel(await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }))));
	}
	{
		clearEnv();
		const stream = mkStream(() => ({ role: "assistant", content: [], stopReason: "error", errorMessage: "boom" }));
		const ctx = mkCtx(stream, { model: MODEL });
		await run(ctx, mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }));
		check("error stopReason → cancel", NOTIFIES.length === 1 && NOTIFIES[0].includes("boom"));
	}
	{
		clearEnv();
		const stream = mkStream(() => ({ role: "assistant", content: [{ type: "text", text: "   " }], stopReason: "stop" }));
		check("empty/whitespace summary → cancel", isCancel(await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }))));
	}
	{
		clearEnv();
		const stream = mkStream(() => ({ role: "assistant", content: [{ type: "text", text: "ok" }], stopReason: "stop" }));
		const ctrl = new AbortController(); ctrl.abort();
		check("aborted signal → cancel", isCancel(await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }], signal: ctrl.signal }))));
	}

	// ---- model resolution ----
	section("model resolution");
	{
		clearEnv();
		const stream = mkStream();
		const M2 = { ...MODEL, id: "override-model" };
		const ctx = mkCtx(stream, { model: MODEL, find: (p, i) => (i === "override-model" ? M2 : undefined) });
		env("PI_SUMMARY_MODEL", "prov/override-model");
		await run(ctx, mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }));
		clearEnv();
		check("model override (hit) uses the found model", stream.calls[0].model === M2);
	}
	{
		clearEnv();
		const stream = mkStream();
		const ctx = mkCtx(stream, { model: MODEL, find: () => undefined });
		env("PI_SUMMARY_MODEL", "prov/bad");
		const r = await run(ctx, mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }));
		clearEnv();
		check("model override (miss) → cancel", isCancel(r));
	}
	{
		clearEnv();
		const stream = mkStream();
		env("PI_SUMMARY_MODEL", "no-slash");
		await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }));
		clearEnv();
		check("override without '/' falls back to session model", stream.calls[0].model === MODEL);
	}
	{
		clearEnv();
		const stream = mkStream();
		const r = await run(mkCtx(stream, {}), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }));
		check("no session model & no override → cancel (model unavailable)", isCancel(r) && NOTIFIES[0].includes("unavailable"));
	}

	// ---- failure modes: cancel vs fallback ----
	section("failure modes");
	{
		clearEnv();
		const stream = mkStream(() => ({ role: "assistant", content: [], stopReason: "stop" }));
		env("PI_SUMMARY_FAIL", "fallback");
		const r = await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }));
		clearEnv();
		check("fallback mode on failure → undefined (default compaction)", r === undefined && NOTIFIES[0].includes("default compaction"));
	}
	{
		clearEnv();
		const stream = mkStream(() => ({ role: "assistant", content: [], stopReason: "stop" }));
		const r = await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }));
		check("cancel mode on failure → { cancel: true } + warning", isCancel(r) && NOTIFIES[0].includes("kept existing context"));
	}

	// ---- ceiling clamping ----
	section("ceiling clamping");
	const ceilingProbe = async (val) => {
		clearEnv(); env("PI_SUMMARY_MAX", val);
		const stream = mkStream();
		await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }));
		clearEnv();
		return stream.calls[0].userText;
	};
	{
		check("clamp down (10 → 300)", (await ceilingProbe(10)).includes("never more than 300"));
		check("clamp up (999999 → 20000)", (await ceilingProbe(999999)).includes("never more than 20000"));
		check("invalid (abc → 1500)", (await ceilingProbe("abc")).includes("never more than 1500"));
		check("exact default (unset → 1500)", (await ceilingProbe(undefined)).includes("never more than 1500"));
	}

	// ---- disabled opt-out ----
	section("disabled opt-out");
	{
		for (const v of ["off", "0", "disabled", "false"]) {
			clearEnv(); env("PI_SUMMARY_REWRITE", v);
			const stream = mkStream();
			const r = await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }));
			clearEnv();
			check(`PI_SUMMARY_REWRITE=${v} → no-op, no model call`, r === undefined && stream.calls.length === 0);
		}
	}

	// ---- previous summary folding ----
	section("previous summary folding");
	{
		clearEnv();
		const stream = mkStream();
		await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }], previousSummary: "PRIOR-SUMMARY-TOKEN-9" }));
		check("previous summary folded into prompt", stream.calls[0].userText.includes("PRIOR-SUMMARY-TOKEN-9") && stream.calls[0].userText.includes("<previous-summary>"));
	}

	// ---- split-turn prefix (Fix #2) ----
	section("split-turn prefix");
	{
		clearEnv();
		const stream = mkStream();
		const ev = mkEvent({
			messagesToSummarize: [{ role: "user", content: "HISTORY-FACT-AAA" }],
			isSplitTurn: true,
			turnPrefixMessages: [{ role: "assistant", content: [{ type: "text", text: "PREFIX-FACT-ZULU" }] }],
		});
		await run(mkCtx(stream, { model: MODEL }), ev);
		check("split-turn prefix fact is serialized into the prompt", stream.calls[0].userText.includes("PREFIX-FACT-ZULU"));
		check("prefix is labelled for the model", stream.calls[0].userText.includes("Split-turn prefix"));
		check("history still present alongside the prefix", stream.calls[0].userText.includes("HISTORY-FACT-AAA"));
	}
	{
		clearEnv();
		const stream = mkStream();
		await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "H" }], isSplitTurn: false }));
		check("no split turn → no prefix section", !stream.calls[0].userText.includes("Split-turn prefix"));
	}
	{
		clearEnv();
		const stream = mkStream();
		await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "H" }], isSplitTurn: true, turnPrefixMessages: [] }));
		check("split turn with empty prefix → no prefix section", !stream.calls[0].userText.includes("Split-turn prefix"));
	}

	// ---- usage accumulation (Fix #5) ----
	section("usage accumulation");
	{
		clearEnv();
		const single = mkStream(() => ({ role: "assistant", content: [{ type: "text", text: "goal done" }], stopReason: "stop", usage: U(10) }));
		const r = await run(mkCtx(single, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }));
		check("single call → usage is that call's usage (not doubled)", comp(r) && comp(r).usage.totalTokens === 110);
	}
	{
		clearEnv();
		const draft = mkMsg("draft", 4000);
		const final = mkMsg("tight", 900);
		const stream = mkStream((t, i) => ({ role: "assistant", content: [{ type: "text", text: i === 1 ? draft : final }], stopReason: "stop", usage: i === 1 ? U(10) : U(20) }));
		const r = await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] }));
		// first totalTokens 110 + second 120 = 230; cost totals 0.0012 + 0.0012
		check("two calls → usage accumulated across both", comp(r) && comp(r).usage.totalTokens === 230);
		check("two calls → cost accumulated", comp(r) && Math.abs(comp(r).usage.cost.total - 0.0024) < 1e-9);
	}

	// ---- error safety: throw → policy, never a rejection (Fix #3) ----
	section("error safety (handler never throws)");
	{
		clearEnv();
		const stream = mkStream(() => { throw new Error("provider boom"); });
		let threw = false, r;
		try { r = await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] })); }
		catch { threw = true; }
		check("model rejection in cancel mode → { cancel: true } (no throw)", !threw && isCancel(r) && NOTIFIES[0].includes("provider boom"));
	}
	{
		clearEnv(); env("PI_SUMMARY_FAIL", "fallback");
		const stream = mkStream(() => { throw new Error("provider boom"); });
		let threw = false, r;
		try { r = await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] })); }
		catch { threw = true; }
		clearEnv();
		check("model rejection in fallback mode → undefined (no throw)", !threw && r === undefined);
	}
	{
		// An ASYNC rejection of result() (a rejected promise, not a synchronous throw) is caught too.
		clearEnv();
		const stream = mkStream(() => Promise.reject(new Error("async boom")));
		let threw = false, r;
		try { r = await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] })); }
		catch { threw = true; }
		check("async-rejected result() in cancel mode → { cancel: true } (no throw)", !threw && isCancel(r) && NOTIFIES[0].includes("async boom"));
	}
	{
		clearEnv(); env("PI_SUMMARY_FAIL", "fallback");
		const stream = mkStream(() => Promise.reject(new Error("async boom")));
		let threw = false, r;
		try { r = await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] })); }
		catch { threw = true; }
		clearEnv();
		check("async-rejected result() in fallback mode → undefined (no throw)", !threw && r === undefined);
	}
	{
		// A failure on the SECOND (rewrite) call is caught; no partial is returned.
		clearEnv();
		const draft = mkMsg("draft", 4000);
		const stream = mkStream((t, i) => i === 1
			? { role: "assistant", content: [{ type: "text", text: draft }], stopReason: "stop" }
			: Promise.reject(new Error("rewrite boom")));
		let threw = false, r;
		try { r = await run(mkCtx(stream, { model: MODEL }), mkEvent({ messagesToSummarize: [{ role: "user", content: "hi" }] })); }
		catch { threw = true; }
		check("second-call failure → { cancel: true }, no partial (no throw)", !threw && isCancel(r) && stream.calls.length === 2);
	}

	// ---- summary ----
	console.log(`\n${passed} passed, ${failed} failed`);
	if (failed) { console.log("Failures:"); failures.forEach((f) => console.log("  - " + f)); process.exit(1); }
})().catch((e) => { console.error("harness error:", e); process.exit(2); });
