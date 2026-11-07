/**
 * compact-rewrite — deterministic rewrite compaction for Pi.
 *
 * Registers a `session_before_compact` handler. When Pi is about to compact a
 * long session, this handler generates a fresh, self-contained summary with the
 * session model (or PI_SUMMARY_MODEL) and returns it as the compaction, so each
 * summary REPLACES the previous one: the prior summary is folded in (only what
 * is still relevant survives) rather than appended to.
 *
 * Return contract (verified against pi-coding-agent 1.4.0)
 *   The `session_before_compact` hook consumer reads `result?.compaction` and
 *   `result?.cancel`. This handler therefore returns:
 *     - success  -> { compaction: { summary, firstKeptEntryId, tokensBefore,
 *                                usage, details } }
 *     - cancel   -> { cancel: true }      (keep the current context)
 *     - fallback -> undefined             (defer to Pi's default compaction)
 *   A bare CompactionResult is NOT consumed and is never returned. `estimatedTokensAfter`
 *   is also omitted: the consumer recomputes it, and the built-in compact() does not
 *   set it either. All errors are caught and routed through the failure policy so a
 *   model/provider failure can never surface as a thrown handler error (which the
 *   extension runner would swallow and silently fall through to default compaction,
 *   defeating PI_SUMMARY_FAIL=cancel).
 *
 * Split turns
 *   When compaction fires mid-turn, preparation carries the dropped history
 *   (messagesToSummarize) plus the earlier part of the in-progress turn
 *   (turnPrefixMessages) and isSplitTurn. Both are folded into the summary via a
 *   clearly-labelled split-turn prefix section so no work shown in the
 *   interrupted turn is lost.
 *
 * Manual compaction instructions
 *   A manual /compact may carry custom instructions (event.customInstructions,
 *   e.g. "Preserve the rollback steps"). They are not part of the dropped messages,
 *   so they are threaded into both the generation and the rewrite prompts and
 *   restated in the summary; without this they would be silently lost.
 *
 * Length model
 *   - Hard ceiling: PI_SUMMARY_MAX words (integer in [300, 20000], default 1500,
 *     clamped). The first attempt targets ~70% of the ceiling. If it exceeds the
 *     ceiling, exactly ONE rewrite is requested at ~85% of the ceiling. The rewrite
 *     call receives ONLY the oversized draft (plus the preservation requirements and
 *     any custom instructions) — never the full conversation again — because near the
 *     context limit Pi clamps the output allowance to the remaining context space, so
 *     resending the conversation would shrink the budget the rewrite must fit into.
 *     Targets are derived from the ceiling so prompts are never negative or impossible.
 *   - Word ceiling vs token allowance: the ceiling is enforced on the SUMMARY text
 *     (word count), not on the model output. The model is granted its FULL
 *     configured output allowance (model.maxTokens) for the generation call so a
 *     long, code-heavy summary is not truncated before the word check can run.
 *
 * Thinking policy (explicit)
 *   - When the model is a reasoning model, the summary call pins thinking to
 *     "minimal": summarization is mechanical, and hidden reasoning would burn
 *     output tokens and risk truncation. Non-reasoning models are left untouched.
 *
 * Failure handling (never silently truncates)
 *   - A generation is rejected as invalid if: it aborts, errors, hits the output
 *     cap (stopReason "length"), is empty, or contains any tool-call block. An
 *     invalid or over-ceiling summary is never returned.
 *   - On any failure: PI_SUMMARY_FAIL=cancel (default) keeps Pi's existing
 *     context; PI_SUMMARY_FAIL=fallback defers to Pi's default compaction, which
 *     has NO word limit — the word ceiling is forfeited in fallback mode.
 *
 * Usage accounting
 *   - Tokens/cost from every generation call are accumulated (mirroring Pi's
 *     internal combineUsage) and stored in CompactionResult.usage.
 *
 * Environment
 *   PI_SUMMARY_MODEL   "provider/modelId" override (default: current session model)
 *   PI_SUMMARY_MAX     word ceiling; integer in [300, 20000], default 1500 (clamped)
 *   PI_SUMMARY_FAIL    "cancel" (default) | "fallback"
 *   PI_SUMMARY_REWRITE 0|off|disabled|false → disable this extension entirely
 *
 * Verified against Pi 1.4.0 (@earendil-works/pi-coding-agent):
 * session_before_compact, SessionBeforeCompactResult, modelRegistry.streamSimple,
 * convertToLlm, serializeConversation, CompactionResult, FileOperations.
 */
import {
	convertToLlm,
	serializeConversation,
	type CompactionResult,
	type ExtensionAPI,
	type ExtensionContext,
	type FileOperations,
	type SessionBeforeCompactResult,
} from "@earendil-works/pi-coding-agent";

// --- configuration ----------------------------------------------------------

const DEFAULT_CEILING = 1500;
const MIN_CEILING = 300;
const MAX_CEILING = 20000;
const INITIAL_FRACTION = 0.7; // first-attempt target, comfortably under the ceiling
const REWRITE_FRACTION = 0.85; // retry target, also under the ceiling

const SYSTEM_PROMPT =
	"You compress coding-agent conversations into faithful, self-contained state " +
	"summaries. Output Markdown only. Never call tools, never continue the " +
	"conversation, never add commentary, preamble, or a code fence around the " +
	"whole summary.";

/** Word ceiling from PI_SUMMARY_MAX: integer clamped to [MIN, MAX]; default 1500. */
function wordCeiling(): number {
	const raw = process.env.PI_SUMMARY_MAX?.trim();
	if (!raw) return DEFAULT_CEILING;
	const n = Number(raw);
	if (!Number.isFinite(n)) return DEFAULT_CEILING;
	return Math.max(MIN_CEILING, Math.min(MAX_CEILING, Math.round(n)));
}

/** Derive first-attempt and retry targets from the ceiling (never negative, always < ceiling). */
function targets(ceiling: number): { initial: number; rewrite: number } {
	const initial = Math.max(1, Math.round(ceiling * INITIAL_FRACTION));
	const rewrite = Math.max(initial + 1, Math.min(ceiling - 1, Math.round(ceiling * REWRITE_FRACTION)));
	return { initial, rewrite };
}

function failMode(): "cancel" | "fallback" {
	return process.env.PI_SUMMARY_FAIL?.trim().toLowerCase() === "fallback" ? "fallback" : "cancel";
}

function disabled(): boolean {
	const v = process.env.PI_SUMMARY_REWRITE?.trim().toLowerCase();
	return v === "0" || v === "off" || v === "disabled" || v === "false";
}

// --- types & small helpers --------------------------------------------------

/** Usage shape as consumed from a model result (CompactionResult.usage). */
type Usage = NonNullable<CompactionResult["usage"]>;

/**
 * Structural type for the model result we consume. `AssistantMessage` is not
 * re-exported from the pi-coding-agent root, so we type only the fields we read
 * (a real AssistantMessage is assignable to this).
 */
type SummaryMsg = {
	stopReason: string;
	errorMessage?: string;
	content: { type: string }[];
	usage?: Usage;
};

function countWords(text: string): number {
	return text.trim().split(/\s+/).filter(Boolean).length;
}

/** Concatenate the text blocks of a result (skips thinking and tool-call blocks). */
function extractText(msg: SummaryMsg): string {
	return msg.content
		.filter((b): b is { type: "text"; text: string } => b.type === "text")
		.map((b) => b.text)
		.join("\n");
}

/** A summary must be plain text; any tool-call block makes it invalid. */
function hasToolCall(msg: SummaryMsg): boolean {
	return msg.content.some((b) => b.type === "toolCall");
}

/**
 * Combine two Usage objects field-by-field, mirroring Pi's internal combineUsage
 * (which is not re-exported from the root). Used to accumulate tokens/cost across
 * the summary generation calls so CompactionResult.usage reflects all work here.
 */
function combineUsage(a: Usage, b: Usage): Usage {
	return {
		input: a.input + b.input,
		output: a.output + b.output,
		cacheRead: a.cacheRead + b.cacheRead,
		cacheWrite: a.cacheWrite + b.cacheWrite,
		...(a.cacheWrite1h !== undefined || b.cacheWrite1h !== undefined
			? { cacheWrite1h: (a.cacheWrite1h ?? 0) + (b.cacheWrite1h ?? 0) }
			: {}),
		...(a.reasoning !== undefined || b.reasoning !== undefined
			? { reasoning: (a.reasoning ?? 0) + (b.reasoning ?? 0) }
			: {}),
		totalTokens: a.totalTokens + b.totalTokens,
		cost: {
			input: a.cost.input + b.cost.input,
			output: a.cost.output + b.cost.output,
			cacheRead: a.cost.cacheRead + b.cost.cacheRead,
			cacheWrite: a.cost.cacheWrite + b.cost.cacheWrite,
			total: a.cost.total + b.cost.total,
		},
	};
}

/**
 * Rebuild the file-tracking lists the way Pi's compaction does (readFiles = read
 * but not modified). `computeFileLists` is not re-exported from the root, so we
 * compute from the preparation's fileOps metadata.
 */
function fileDetails(fileOps: FileOperations): { readFiles: string[]; modifiedFiles: string[] } {
	const modified = new Set<string>([...fileOps.edited, ...fileOps.written]);
	const readFiles = [...fileOps.read].filter((f) => !modified.has(f)).sort();
	const modifiedFiles = [...modified].sort();
	return { readFiles, modifiedFiles };
}

/** True for a result that must not be used: aborted, errored, or truncated. */
function isBadResult(msg: SummaryMsg): boolean {
	return msg.stopReason === "aborted" || msg.stopReason === "error" || msg.stopReason === "length";
}

/** Human-readable reason for a bad/empty result (for the failure notification). */
function badReason(msg: SummaryMsg, fallback: string): string {
	if (msg.stopReason === "aborted") return "generation aborted";
	if (msg.stopReason === "length") return `summary hit the model output cap (truncated, stopReason=${msg.stopReason})`;
	if (msg.stopReason === "error") return `summary generation failed${msg.errorMessage ? `: ${msg.errorMessage}` : ""}`;
	return fallback;
}

/** Resolve the model: PI_SUMMARY_MODEL "provider/modelId" override, else the session model. */
function resolveModel(ctx: ExtensionContext) {
	const override = process.env.PI_SUMMARY_MODEL?.trim();
	if (override) {
		const slash = override.indexOf("/");
		if (slash > 0) {
			return ctx.modelRegistry.find(override.slice(0, slash), override.slice(slash + 1));
		}
	}
	return ctx.model;
}

/**
 * Generate one summary. Returns the raw model result, or undefined if the model
 * could not be resolved. The prompt is sent as a single serialized user message
 * (Pi's own compaction pattern) so the model cannot continue the conversation.
 */
async function generateSummary(
	ctx: ExtensionContext,
	event: { signal: AbortSignal },
	promptText: string,
): Promise<SummaryMsg | undefined> {
	const model = resolveModel(ctx);
	if (!model) return undefined;

	const context = {
		systemPrompt: SYSTEM_PROMPT,
		messages: [{ role: "user" as const, content: promptText, timestamp: Date.now() }],
	};
	const options = {
		signal: event.signal,
		cacheRetention: "none" as const,
		// Grant the model's FULL configured output allowance (not a fixed 4096),
		// so a long, code-heavy summary is not truncated before the word check runs.
		...(model.maxTokens > 0 ? { maxTokens: model.maxTokens } : {}),
		// Explicit thinking policy: pin reasoning models to minimal for the summary.
		...(model.reasoning ? { reasoning: "minimal" as const } : {}),
	};

	const stream = ctx.modelRegistry.streamSimple(model, context, options);
	const result = await stream.result();
	return result as SummaryMsg;
}

// --- main handler -----------------------------------------------------------

export default function (pi: ExtensionAPI) {
	pi.on("session_before_compact", async (event, ctx) => {
		if (disabled()) return undefined; // opt out: defer to Pi's default compaction

		const ceiling = wordCeiling();
		const { initial, rewrite } = targets(ceiling);
		const mode = failMode();
		const preparation = event.preparation;

		// Failure policy. Exception-safe: even if the UI notify throws, the correct
		// sentinel is still returned so PI_SUMMARY_FAIL=cancel really keeps context
		// and fallback really defers to default compaction.
		const onFail = (reason: string): SessionBeforeCompactResult | undefined => {
			try {
				ctx.ui.notify(
					mode === "fallback"
						? `compact-rewrite: ${reason}; using default compaction (no word limit).`
						: `compact-rewrite: ${reason}; kept existing context.`,
					"warning",
				);
			} catch {
				/* ignore notification failures */
			}
			return mode === "fallback" ? undefined : { cancel: true };
		};

		// Wrap the whole generation in try/catch: a thrown error would be swallowed by
		// the extension runner and fall through to (unrestricted) default compaction.
		// Catching and returning the failure sentinel keeps the policy honest.
		try {
			// Assemble the conversation to summarize: the dropped history, plus the
			// interrupted turn's prefix when a split turn is in progress, plus the
			// previous summary (to fold in).
			const history = serializeConversation(convertToLlm(preparation.messagesToSummarize));
			const isSplit = preparation.isSplitTurn && preparation.turnPrefixMessages.length > 0;
			const prefix = isSplit
				? "\n\n# Split-turn prefix\n" +
					"The messages below are the earlier part of the turn currently in progress; " +
					"the later part of this same turn is retained in context and needs no " +
					"reconstruction. Capture the request and the progress shown below so the " +
					"work can continue.\n" +
					serializeConversation(convertToLlm(preparation.turnPrefixMessages))
				: "";
			const prior = preparation.previousSummary
				? `\n<previous-summary>\n${preparation.previousSummary}\n</previous-summary>\n`
				: "";
			const conversationBlock = `<conversation>\n${history}${prefix}\n</conversation>\n${prior}\n`;

			// Accumulate usage across every generation call (history + optional
			// split-turn prefix + optional rewrite) so CompactionResult.usage
			// reflects all model work done here.
			let totalUsage: Usage | undefined;
			const acc = (u: Usage | undefined) => {
				if (u !== undefined) totalUsage = totalUsage === undefined ? u : combineUsage(totalUsage, u);
			};

			// Manual /compact may carry user instructions (e.g. "Preserve the rollback steps").
			// They are not part of the dropped messages, so they must be threaded into every
			// prompt or they are silently lost; they also restate the preservation requirements
			// on the rewrite call.
			const customInstructions = event.customInstructions?.trim();
			const customLine = customInstructions
				? `User instructions for THIS summary — follow them and restate them in the summary: ${customInstructions}`
				: "";

			const firstInstruction =
				`Produce a self-contained session summary of the conversation above, in Markdown, ` +
				`targeting about ${initial} words and never more than ${ceiling} words. ` +
				`It must let a fresh agent continue seamlessly. Cover: ` +
				`(1) Goal and constraints, (2) Progress: done / in progress / blocked, ` +
				`(3) Key decisions and rationale, (4) Next steps, ` +
				`(5) Key paths & identifiers (files, branches, remotes, models, env vars, commands). ` +
				`Be factual and mark hypotheses as hypotheses. Keep exact file paths, commands, ` +
				`and identifiers. ` +
				(customLine ? `${customLine} ` : "") +
				`Output the summary only.`;

			const result = await generateSummary(ctx, event, conversationBlock + firstInstruction);
			acc(result?.usage);
			if (!result) return onFail("summary model unavailable");
			if (event.signal.aborted || isBadResult(result)) return onFail(badReason(result, "summary generation failed"));
			if (hasToolCall(result)) return onFail("summary contained a tool call; rejected");

			const text = extractText(result).trim();
			if (!text) return onFail("summary was empty");

			// Build the replacement compaction for a summary that fits the ceiling.
			const mkResult = (summaryText: string): SessionBeforeCompactResult => ({
				compaction: {
					summary: summaryText,
					firstKeptEntryId: preparation.firstKeptEntryId,
					tokensBefore: preparation.tokensBefore,
					usage: totalUsage,
					details: fileDetails(preparation.fileOps),
				},
			});

			if (countWords(text) <= ceiling) return mkResult(text);

			// Over the ceiling: exactly one rewrite. Rewrite FROM THE DRAFT ONLY — do NOT resend the
			// whole conversation. Near the context limit Pi clamps the generation's output allowance
			// to the remaining context space, so a bigger request (conversation + draft) would shrink
			// the very budget we are trying to fit within, recreating the truncation during recovery.
			// The draft already carries the summarized content; the model just compresses it under
			// the ceiling, with the preservation requirements (and any custom instructions) restated.
			const overWords = countWords(text);
			const rewriteInstruction =
				`Your previous answer was ${overWords} words, over the ${ceiling}-word limit. ` +
				`Rewrite it to at most ${rewrite} words. Keep every load-bearing fact ` +
				`(open questions, decisions, exact file paths, commands, TODOs, in-progress state, constraints) ` +
				`but cut examples, duplication, and filler. ` +
				(customLine ? `${customLine} ` : "") +
				`Output the new summary only. ` +
				`\n<previous-draft>\n${text}\n</previous-draft>`;

			const retry = await generateSummary(ctx, event, rewriteInstruction);
			acc(retry?.usage);
			if (retry && !event.signal.aborted && !isBadResult(retry) && !hasToolCall(retry)) {
				const retryText = extractText(retry).trim();
				if (retryText && countWords(retryText) <= ceiling) {
					return mkResult(retryText);
				}
			}

			return onFail(`summary exceeded ${ceiling} words and the rewrite did not fit (was ${overWords} words)`);
		} catch (err) {
			const msg = err instanceof Error ? err.message : String(err);
			return onFail(`unexpected error: ${msg}`);
		}
	});
}
