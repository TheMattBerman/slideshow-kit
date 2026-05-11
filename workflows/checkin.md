# Workflow: Daily Check-in

> **Audience:** the host agent (Claude Code, Codex, OpenClaw, Hermes) walking the daily loop. Not user-invocable. Called from `workflows/daily-loop.md` step 3.

This workflow asks the brand operator for hot takes on today's trends. It branches on the brand's configured channel and degrades gracefully - Telegram failures NEVER block postiz, postiz failures NEVER block the Telegram alert path (per spec §7.3).

## Inputs

- `brand_slug` - the brand the daily loop is running for
- `trends_path` - path to `<brands_root>/<slug>/runs/<date>/trends.json`
- `runs_dir` - `<brands_root>/<slug>/runs/<date>/`

## Reads

- `<brands_root>/<slug>/brand-perspective.md` - pillars, hot-take patterns
- `<brands_root>/<slug>/config.json` - `checkin.channel`, `checkin.timeout_minutes`, `checkin.telegram_chat_id`

## Writes

- `<runs_dir>/checkin-prompt.md` - the question that was asked
- `<runs_dir>/checkin-response.md` - the operator's reply (or an autopilot marker)

## Step 1 - Build the check-in prompt

Read `trends_path` (top 5 trends) and `brand-perspective.md`. Compose this prompt:

```
[brand_slug] - Daily Check-in

Today's trends:
1. <trend 1 title> - <one-line summary>
2. ...
5. ...

Reply with one or more "<n>: your take" lines, or send `skip` for autopilot.
Timing out in <timeout_minutes> minutes.
```

Save to `<runs_dir>/checkin-prompt.md`.

## Step 2 - Branch on channel

Read `config.json` field `checkin.channel`. Branches:

### Branch A - Telegram (`channel == "telegram"`)

1. Verify `$TELEGRAM_BOT_TOKEN` is set and `checkin.telegram_chat_id` is non-null. If either missing, log a `[WARN]` and fall through to Branch B (agent surface).
2. Invoke:

   ```bash
   ./scripts/send_telegram.sh \
     --chat-id "<telegram_chat_id>" \
     --text "$(cat <runs_dir>/checkin-prompt.md)"
   ```

3. Capture the exit code:
   - **0** - message sent. Note the printed `message_id`.
   - **11 (telegram error)** or **12 (network error)** - log and fall through to Branch B (agent surface) for this run only. Do not crash the daily loop.

4. If sent, poll `getUpdates` (or wait on a webhook listener if the host has one) for replies to that `message_id`. Polling pseudo-loop:

   ```
   start = now()
   while now() - start < timeout_minutes:
       updates = curl getUpdates?offset=<last_seen+1>
       for each message:
           if message.reply_to_message.message_id == <our message_id>:
               return message.text
       sleep 30
   return None  # timed out
   ```

   If the host agent does not have a long-lived loop (e.g. one-shot CLI runs), use webhook mode (configured in `references/telegram-setup.md`) or skip polling and accept that Telegram is fire-and-forget for that host.

### Branch B - Agent surface (`channel == "agent"`, or Telegram fell through)

1. Print the contents of `<runs_dir>/checkin-prompt.md` to the agent's surface.
2. Wait for the user's response in their session, up to `timeout_minutes`.
3. If the host has no concept of asynchronous wait (one-shot CLI), treat the next user turn as the response.

## Step 3 - Persist the response

If a response was received:

```
write <runs_dir>/checkin-response.md:
---
brand: <slug>
date: <YYYY-MM-DD>
channel: <telegram|agent>
received_at: <ISO timestamp>
---
<the operator's reply, verbatim>
```

If timeout or `skip` was received:

```
write <runs_dir>/checkin-response.md:
---
brand: <slug>
date: <YYYY-MM-DD>
channel: <telegram|agent>
status: autopilot
reason: <"timeout" | "skip" | "telegram_failed">
---
<empty>
```

## Step 4 - Parse hot takes

If the response is non-empty and not `skip`:

- Look for lines matching `^\s*(\d+):\s+(.+)$` - these are takes keyed to trend numbers.
- For lines not matching, treat as a free-form note appended to all selected trends.
- Return a dict `{trend_index: take_text, ...}` to the daily-loop caller.

If autopilot, return `{}`. The daily loop will use `brand-perspective.md` only as the lens.

## Decoupling guarantees

- Telegram exit codes 11 and 12 NEVER bubble up as fatal - the loop continues.
- This workflow does not call `publish_postiz.sh`. The daily loop owns publishing and runs it after Step 4 unconditionally.
- A timeout returns autopilot and the day still ships.
