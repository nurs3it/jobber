# sources/telegram/ — Telegram через Telethon (user session)

**Назначение.** Читать вакансии из личных чатов, групп, супергрупп, каналов и сообществ
пользователя, **включая архив**. Маппить сырые сообщения в модели `core/` и извлекать контакт.

**Ключевые файлы.**
- `client.py` — обёртка над `telethon.TelegramClient`: логин (код + 2FA), задержки, FloodWait.
- `source.py` — `TelegramSource(JobSource)`: `iter_dialogs(include_archived)`, `iter_new_messages`.
- `mapping.py` — Telethon → `Dialog`/`RawMessage`; `extract_contact(text)`.

**Почему user session, а не Bot API.**
- ⚠️ **Bot API не подходит.** Бот не видит личные чаты, подписки, группы и архив.
- User-session клиент (MTProto) видит всё, что видит пользователь. Архив — `folder_id == 1`
  (в Telethon — итерация диалогов с учётом папок).

**Инварианты / подводные камни.**
- 🔒 **Файл сессии (`*.session`) = полный доступ к аккаунту.** Только локально, в `.gitignore`,
  как секрет. Никогда не коммитить и не логировать.
- **Только чтение.** Никаких отправок, вступлений, рассылок.
- Мягкие задержки между запросами (`config.sources.telegram.delay_between_requests`).
- `FloodWaitError` — ждать `e.seconds`, не ретраить агрессивно.
- Первый логин интерактивный (код из Telegram + пароль 2FA при наличии).
- Курсор диалога = `min_id`/`message_id` последнего обработанного сообщения.

**Статус:** ✅ реализовано. `TelethonBackend` — интеграция (без юнит-тестов); логика `TelegramSource`
и `mapping` покрыта на фейках: `tests/test_telegram_source.py`, `test_telegram_mapping.py`,
`test_contact_extraction.py`. Первый логин: `python -m sources.telegram login`.
