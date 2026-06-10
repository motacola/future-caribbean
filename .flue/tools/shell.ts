import { spawn } from 'node:child_process';

export type CommandResult = {
  command: string;
  exitCode: number | null;
  stdout: string;
  stderr: string;
  durationMs: number;
};

export function projectPath(...parts: string[]): string {
  const base = process.env.PROJECT_ROOT || new URL('..', import.meta.url).pathname.replace(/\/$/, '');
  return parts.length ? new URL(parts.join('/'), `file://${base}/`).pathname : base;
}

export const PROJECT_ROOT = projectPath();

export function runCommand(command: string, args: string[], timeoutMs = 120_000): Promise<CommandResult> {
  const started = Date.now();
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      cwd: PROJECT_ROOT,
      env: {
        PATH: process.env.PATH ?? '',
        HOME: process.env.HOME ?? '',
        LANG: process.env.LANG ?? 'en_US.UTF-8',
        LC_ALL: process.env.LC_ALL ?? 'en_US.UTF-8',
        PYTHONUNBUFFERED: '1',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    let done = false;

    const finish = (exitCode: number | null) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      resolve({
        command: [command, ...args].join(' '),
        exitCode,
        stdout,
        stderr,
        durationMs: Date.now() - started,
      });
    };

    const timer = setTimeout(() => {
      stderr += `\nTimed out after ${timeoutMs}ms`;
      child.kill('SIGTERM');
      setTimeout(() => child.kill('SIGKILL'), 2_000).unref();
      finish(124);
    }, timeoutMs);
    timer.unref();

    child.stdout.on('data', (chunk) => {
      stdout += String(chunk);
      if (stdout.length > 80_000) stdout = stdout.slice(-80_000);
    });
    child.stderr.on('data', (chunk) => {
      stderr += String(chunk);
      if (stderr.length > 40_000) stderr = stderr.slice(-40_000);
    });
    child.on('error', (error) => {
      stderr += `\n${error.message}`;
      finish(127);
    });
    child.on('close', (code) => finish(code));
  });
}
