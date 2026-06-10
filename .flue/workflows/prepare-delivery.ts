import { type WorkflowRouteHandler } from '@flue/runtime';
import { prepareDelivery } from '../tools/delivery.ts';

export const route: WorkflowRouteHandler = async (_c, next) => next();

export async function run({ payload }: { payload?: { channel?: string; file?: string } }) {
  return prepareDelivery({ channel: payload?.channel, file: payload?.file });
}
