# Self-hosting Abeng

The production instance runs on Vercel. This is for running your own.

There is not much to it: `server.py` is pure standard library — no gunicorn,
no uvicorn, no application server to configure — so a host needs Python and a
TLS terminator, and that is all.

## What you need

| | |
|---|---|
| **Python 3.10+** | The codebase uses PEP 604 unions (`float \| None`). |
| **`requests`** | The only third-party dependency, and only the watchers use it. |
| **Node 20+ and pnpm** | **Optional.** Needed only to build the site from source. |

Without Node, `run_pipeline.sh` skips the Astro build and leaves whatever is
in `dist/` alone — fine if you build the site elsewhere and copy it in. The
data half of the pipeline runs either way.

## Install

```bash
sudo useradd --system --home /opt/abeng --shell /usr/sbin/nologin abeng
sudo git clone https://github.com/motacola/future-caribbean /opt/abeng
cd /opt/abeng

sudo -u abeng pip install --user -r requirements.txt
sudo -u abeng pnpm install && sudo -u abeng pnpm build   # skip if you ship a prebuilt dist/
sudo -u abeng bash run_pipeline.sh                       # first cycle, so the desk has data

sudo install -m 600 deploy/abeng.env.example /etc/abeng.env
sudo "${EDITOR:-vi}" /etc/abeng.env                      # at minimum set ABENG_CORS_ORIGINS

sudo cp deploy/abeng.service deploy/abeng-pipeline.service deploy/abeng-pipeline.timer \
        /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now abeng.service abeng-pipeline.timer
```

Checked out somewhere other than `/opt/abeng`? Change `WorkingDirectory` and
`ReadWritePaths` in both service units to match.

## The one thing that will catch you out

Bound to loopback — the default, and correct behind a proxy — the server
refuses any request whose `Host` header is neither loopback nor listed in
`ABENG_CORS_ORIGINS`. It is a DNS-rebinding guard: binding to `127.0.0.1`
stops other machines reaching the port, but it does not stop a page you visit
from pointing its own domain at `127.0.0.1` and reading the server
same-origin.

So a proxy passing through `Host: abeng.example.org` gets

```json
{"ok": false, "error": "Host is not allowed"}
```

with a 403 until that domain is in `ABENG_CORS_ORIGINS`. Set it and the guard
steps aside for you but not for anyone else.

## TLS in front

Caddy, which gets you a certificate without further ceremony:

```
abeng.example.org {
    reverse_proxy 127.0.0.1:8080
}
```

nginx, if you already run it:

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

    # The cycle theater streams over SSE and must not be buffered.
    proxy_buffering off;
    proxy_read_timeout 1h;
}
```

That `proxy_buffering off` matters: without it the "watch the desk work"
panel sits empty, because nginx holds the event stream instead of passing it
through.

## Cycles

`abeng-pipeline.timer` runs a cycle every four hours, catches up after a
reboot, and jitters by up to five minutes so several hosts do not hit the
public sources on the same second.

The server has its own four-hour loop, and the service unit turns it off with
`DISABLE_PIPELINE_LOOP=1` — two schedulers would run cycles on top of each
other. If you would rather use the built-in loop, drop that line and do not
enable the timer.

```bash
systemctl list-timers abeng-pipeline.timer   # when the next cycle runs
systemctl start abeng-pipeline.service       # run one now
journalctl -u abeng-pipeline.service -f      # watch it
```

A cycle that cannot reach its sources still publishes, flagged, and exits
non-zero — so a failed unit in the journal means "some sources were
unreachable", not "nothing was published".

## Checking it works

```bash
curl -s localhost:8080/api/status | python3 -m json.tool | head
python3 cli/abengctl.py status
```

`/api/status` reports each source's age against its own refresh cadence, so a
collector that has gone quiet shows up as stale rather than as healthy.
