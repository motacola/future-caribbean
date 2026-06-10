import { createAgent, defineTool, Type, type AgentRouteHandler } from '@flue/runtime';
import { listKeyArtifacts, readArtifact } from '../tools/artifacts.ts';
import { generateBrief } from '../tools/briefs.ts';
import { askDispatch, explainLead, readDispatchDeskJson, summarizeDesk } from '../tools/dispatch-query.ts';
import { listAvailableFeedback, recordFeedback } from '../tools/feedback.ts';
import { openNotebookStatus, pushCycleToOpenNotebook } from '../tools/open-notebook.ts';
import { archiveCurrentCycle, listCycleHistory } from '../tools/history.ts';
import { approveDelivery, listApprovals, prepareDelivery, sendApproved } from '../tools/delivery.ts';
import { tryReadDeskSummary } from '../tools/pipeline.ts';

export const route: AgentRouteHandler = async (_c, next) => next();

const askDispatchTool = defineTool({
  name: 'ask_dispatch',
  description: 'Ask the deterministic Caribbean Opportunity Dispatch query layer a grounded question about the current cycle.',
  parameters: Type.Object({
    question: Type.String({ description: 'Question about the current dispatch cycle, country, persona, lead signal, or feedback.' }),
  }),
  execute: async ({ question }) => JSON.stringify(await askDispatch(String(question)), null, 2),
});

const explainLeadTool = defineTool({
  name: 'explain_lead_signal',
  description: 'Return the deterministic explanation of the current lead signal with artifact citations.',
  parameters: Type.Object({}),
  execute: async () => JSON.stringify(await explainLead(), null, 2),
});

const dispatchSummaryTool = defineTool({
  name: 'dispatch_summary',
  description: 'Return machine-readable summary counts and lead metadata for the latest Dispatch Desk artifact.',
  parameters: Type.Object({}),
  execute: async () => JSON.stringify(await tryReadDeskSummary(), null, 2),
});

const rawDeskTool = defineTool({
  name: 'read_dispatch_desk_json',
  description: 'Read the raw outbox/dispatch_desk.json artifact. Use only when summary or ask_dispatch is insufficient.',
  parameters: Type.Object({}),
  execute: async () => JSON.stringify(summarizeDesk(await readDispatchDeskJson()), null, 2),
});

const generateBriefTool = defineTool({
  name: 'generate_brief',
  description: 'Generate an audience-specific memo or short channel brief from the latest Dispatch Desk artifact.',
  parameters: Type.Object({
    audience: Type.Optional(Type.String({ description: 'Audience/persona, e.g. investor, founder, policy, operator.' })),
    channel: Type.Optional(Type.String({ description: 'Output style/channel, e.g. memo, telegram, whatsapp.' })),
    maxClusters: Type.Optional(Type.Number({ description: 'Number of top clusters to include, 1-8.' })),
  }),
  execute: async (input) => JSON.stringify(await generateBrief(input), null, 2),
});

const listArtifactsTool = defineTool({
  name: 'list_artifacts',
  description: 'List key generated artifacts and their modification times.',
  parameters: Type.Object({}),
  execute: async () => JSON.stringify({ ok: true, artifacts: await listKeyArtifacts() }, null, 2),
});

const readArtifactTool = defineTool({
  name: 'read_artifact',
  description: 'Read an allowed generated artifact such as outbox/dispatch_desk.md or outbox/judge_brief.md.',
  parameters: Type.Object({
    path: Type.String({ description: 'Allowed artifact path under outbox/, data/feedback/, data/composite/, domains/, or config/recipients.json.' }),
    maxBytes: Type.Optional(Type.Number({ description: 'Maximum bytes/characters to return.' })),
  }),
  execute: async ({ path, maxBytes }) => JSON.stringify(await readArtifact(String(path), Number(maxBytes || 40_000)), null, 2),
});

const recordFeedbackTool = defineTool({
  name: 'record_feedback',
  description: 'Record operator feedback for a dispatch ID. This appends to data/feedback/available.json for the next cycle.',
  parameters: Type.Object({
    dispatchId: Type.String({ description: 'Dispatch ID such as DSP-20260603-021.' }),
    status: Type.String({ description: 'forwarded, replied, opened, ignored, decision_changed, or delivered.' }),
    note: Type.Optional(Type.String({ description: 'Operator note.' })),
    source: Type.Optional(Type.String({ description: 'Feedback source/channel.' })),
  }),
  execute: async (input) => JSON.stringify(await recordFeedback({
    dispatchId: String(input.dispatchId || ''),
    status: String(input.status || ''),
    note: input.note ? String(input.note) : undefined,
    source: input.source ? String(input.source) : undefined,
  }), null, 2),
});

const listFeedbackTool = defineTool({
  name: 'list_available_feedback',
  description: 'List feedback entries waiting to be incorporated by the feedback loop.',
  parameters: Type.Object({}),
  execute: async () => JSON.stringify(await listAvailableFeedback(), null, 2),
});

const openNotebookStatusTool = defineTool({
  name: 'open_notebook_status',
  description: 'Check local Open Notebook health and authentication state.',
  parameters: Type.Object({}),
  execute: async () => JSON.stringify(await openNotebookStatus(), null, 2),
});

const pushOpenNotebookTool = defineTool({
  name: 'push_cycle_to_open_notebook',
  description: 'Push the current cycle brief/source text into local Open Notebook. Requires OPEN_NOTEBOOK_TOKEN or OPEN_NOTEBOOK_PASSWORD if auth is enabled.',
  parameters: Type.Object({
    notebookName: Type.Optional(Type.String({ description: 'Notebook name to create/use.' })),
    includeRawJson: Type.Optional(Type.Boolean({ description: 'Include clipped raw dispatch_desk.json in the source.' })),
  }),
  execute: async (input) => JSON.stringify(await pushCycleToOpenNotebook(input), null, 2),
});

const prepareDeliveryTool = defineTool({
  name: 'prepare_delivery',
  description: 'Create a pending delivery approval from a channel artifact and return a preview. This never sends live.',
  parameters: Type.Object({
    channel: Type.Optional(Type.String({ description: 'telegram, investor, judge, or another configured channel key.' })),
    file: Type.Optional(Type.String({ description: 'Optional artifact path to send, e.g. outbox/telegram_digest.md.' })),
  }),
  execute: async (input) => JSON.stringify(await prepareDelivery(input), null, 2),
});

const approveDeliveryTool = defineTool({
  name: 'approve_delivery',
  description: 'Approve or reject a prepared delivery approval. Required before send_approved_delivery.',
  parameters: Type.Object({
    approvalId: Type.String({ description: 'Approval ID returned by prepare_delivery.' }),
    approvedBy: Type.Optional(Type.String({ description: 'Operator/user approving the delivery.' })),
    note: Type.Optional(Type.String({ description: 'Approval note.' })),
    reject: Type.Optional(Type.Boolean({ description: 'Set true to reject instead of approve.' })),
  }),
  execute: async (input) => JSON.stringify(await approveDelivery({
    approvalId: String(input.approvalId || ''),
    approvedBy: input.approvedBy ? String(input.approvedBy) : undefined,
    note: input.note ? String(input.note) : undefined,
    reject: Boolean(input.reject),
  }), null, 2),
});

const listApprovalsTool = defineTool({
  name: 'list_delivery_approvals',
  description: 'List recent delivery approvals and send receipts.',
  parameters: Type.Object({
    limit: Type.Optional(Type.Number({ description: 'Maximum approvals to return.' })),
  }),
  execute: async ({ limit }) => JSON.stringify(await listApprovals(Number(limit || 20)), null, 2),
});

const sendApprovedDeliveryTool = defineTool({
  name: 'send_approved_delivery',
  description: 'Send an already-approved delivery. Defaults to dry-run; live sends require dryRun=false and credentials.',
  parameters: Type.Object({
    approvalId: Type.String({ description: 'Approved delivery ID.' }),
    dryRun: Type.Optional(Type.Boolean({ description: 'Defaults true. Set false only for live sending.' })),
  }),
  execute: async (input) => JSON.stringify(await sendApproved({
    approvalId: String(input.approvalId || ''),
    dryRun: input.dryRun === undefined ? true : Boolean(input.dryRun),
  }), null, 2),
});

const archiveCycleTool = defineTool({
  name: 'archive_current_cycle',
  description: 'Archive current cycle artifacts into data/history/cycles and update the history index.',
  parameters: Type.Object({
    cycleId: Type.Optional(Type.String({ description: 'Optional explicit cycle ID.' })),
    overwrite: Type.Optional(Type.Boolean({ description: 'Replace archive files for an existing cycle.' })),
  }),
  execute: async (input) => JSON.stringify(await archiveCurrentCycle({
    cycleId: input.cycleId ? String(input.cycleId) : undefined,
    overwrite: Boolean(input.overwrite),
  }), null, 2),
});

const listCycleHistoryTool = defineTool({
  name: 'list_cycle_history',
  description: 'List archived cycle history entries.',
  parameters: Type.Object({
    limit: Type.Optional(Type.Number({ description: 'Maximum cycles to return.' })),
  }),
  execute: async ({ limit }) => JSON.stringify(await listCycleHistory(Number(limit || 20)), null, 2),
});

export default createAgent(() => ({
  model: process.env.FLUE_MODEL || 'openai/gpt-5.5',
  tools: [
    askDispatchTool,
    explainLeadTool,
    dispatchSummaryTool,
    rawDeskTool,
    generateBriefTool,
    listArtifactsTool,
    readArtifactTool,
    recordFeedbackTool,
    listFeedbackTool,
    openNotebookStatusTool,
    pushOpenNotebookTool,
    prepareDeliveryTool,
    approveDeliveryTool,
    listApprovalsTool,
    sendApprovedDeliveryTool,
    archiveCycleTool,
    listCycleHistoryTool,
  ],
  instructions: `You are the Caribbean Opportunity Dispatch agent.

Answer questions about the current Caribbean signal cycle using the provided tools. Treat local artifacts as the source of truth. Do not invent countries, signals, sources, delivery state, or feedback state. If the tool output says no data is available, say that the pipeline must be run first.

Always preserve the product's positioning: fragmented public regional data becomes evidence-backed, persona-routed decisions. Keep answers concise and decision-oriented. Include artifact/source citations when the tool returns them. State that signals are screening intelligence, not investment advice, when discussing investment implications.

Delivery is approval-gated: prepare_delivery creates a preview and approval ID; approve_delivery must be called before send_approved_delivery; send_approved_delivery defaults to dry-run. Never imply a live send occurred unless the tool returns a sent status with a send result.`,
}));
