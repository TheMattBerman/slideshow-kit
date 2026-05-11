# Telegram Setup

Telegram check-ins are optional. The daily loop falls through to autopilot mode if Telegram isn't configured. Use Telegram if you want to send the daily trends to your phone, reply with hot takes, and have the kit splice them into the brand's perspective for that day.

## 1. Create a bot

1. Open Telegram and message `@BotFather`.
2. Send `/newbot`.
3. Give it a name (e.g. `Slideshow Kit (matt)`) and a username ending in `bot` (e.g. `slideshow_matt_bot`).
4. BotFather replies with the **bot token** — looks like `1234567890:AABBccDDeeFFggHHiiJJkk`.

Save the token. The kit reads it from `$TELEGRAM_BOT_TOKEN`.

```bash
echo 'export TELEGRAM_BOT_TOKEN="1234567890:AABBcc..."' >> ~/.zshrc
source ~/.zshrc
```

## 2. Get your chat_id

1. Send any message to your new bot from the Telegram account that should receive check-ins (DM is fine; for agency teams, add the bot to a private group).
2. Hit the `getUpdates` endpoint:

```bash
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getUpdates" | python3 -m json.tool
```

3. Look for the `"chat":{"id": ...}` field in the response. That's your chat_id.
   - DMs have positive ids (e.g. `123456789`).
   - Private groups have negative ids (e.g. `-1001234567890`).

## 3. Wire it to a brand

Edit `<brands_root>/<slug>/config.json`:

```json
{
  "checkin": {
    "channel": "telegram",
    "timeout_minutes": 30,
    "telegram_chat_id": "-1001234567890"
  }
}
```

Set `channel` to `"telegram"` (or leave as `"agent"` to use the in-session agent prompt instead). `timeout_minutes` controls how long the daily loop waits for your reply before falling through to autopilot.

## 4. Test

```bash
./scripts/send_telegram.sh --chat-id "-1001234567890" --text "kit setup ok"
```

Expected: prints a numeric `message_id`, exits 0, message lands in Telegram.

## 5. Multi-brand

Each brand has its own `chat_id`. Agencies typically:
- One bot, multiple groups (one per client) — same `TELEGRAM_BOT_TOKEN`, different `telegram_chat_id`.
- Multiple bots — set `TELEGRAM_BOT_TOKEN_<SLUG>` per brand in your shell, then export the right one before invoking the daily loop. (The kit reads `TELEGRAM_BOT_TOKEN`; a wrapper cron line can re-export based on which brand is running.)

## Failure mode

If Telegram is down or the token is wrong, `send_telegram.sh` exits non-zero. The daily loop catches this and falls through to autopilot mode for that day — postiz publishing is **not** blocked by Telegram failures (per spec §7.3, decoupling rule).
