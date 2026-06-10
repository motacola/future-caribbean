import { flue } from '@flue/runtime/routing';
import { Hono, type MiddlewareHandler } from 'hono';

const requireToken: MiddlewareHandler = async (c, next) => {
  const configured = process.env.FLUE_API_TOKEN;
  if (!configured) {
    await next();
    return;
  }

  const auth = c.req.header('authorization') ?? '';
  const token = auth.startsWith('Bearer ') ? auth.slice('Bearer '.length) : '';
  if (token !== configured) {
    return c.json({ ok: false, error: 'Unauthorized' }, 401);
  }

  await next();
};

const app = new Hono();

app.get('/health', (c) => c.json({ ok: true, service: 'future-caribbean-flue' }));
app.use('/agents/*', requireToken);
app.use('/workflows/*', requireToken);
app.use('/runs/*', requireToken);
app.route('/', flue());

export default app;
