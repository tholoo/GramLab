-- GramLab schema 3 from 1f9cb3d, with synthetic capabilities and an answered callback.
PRAGMA user_version=3;
CREATE TABLE configuration (seed INTEGER NOT NULL, now INTEGER NOT NULL, world_id TEXT NOT NULL);
CREATE TABLE users (id INTEGER PRIMARY KEY, body TEXT NOT NULL);
CREATE TABLE bots (id INTEGER PRIMARY KEY REFERENCES users(id), next_update INTEGER NOT NULL);
CREATE TABLE bot_tokens (digest TEXT PRIMARY KEY, bot_id INTEGER NOT NULL REFERENCES bots(id));
CREATE TABLE chats (
    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
    bot_id INTEGER NOT NULL REFERENCES users(id), UNIQUE(user_id, bot_id)
);
CREATE TABLE messages (
    chat_id INTEGER NOT NULL REFERENCES chats(id), id INTEGER NOT NULL,
    body TEXT NOT NULL, PRIMARY KEY(chat_id, id)
);
CREATE TABLE updates (
    bot_id INTEGER NOT NULL REFERENCES bots(id), id INTEGER NOT NULL,
    body TEXT NOT NULL, PRIMARY KEY(bot_id, id)
);
CREATE TABLE events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL, body TEXT NOT NULL
);
INSERT INTO configuration VALUES (7, 100, '11111111-2222-4333-8444-555555555555');
INSERT INTO users VALUES (1, '{"is_bot":false,"first_name":"Alice"}');
INSERT INTO users VALUES (2, '{"is_bot":true,"first_name":"Echo"}');
INSERT INTO bots VALUES (2, 2);
INSERT INTO chats VALUES (1, 1, 2);
INSERT INTO messages VALUES (1, 1, '{"id":1,"chat_id":1,"sender_id":1,"date":100,"text":"before upgrade"}');
INSERT INTO updates VALUES (2, 1, '{"update_id":1,"message":{"id":1,"chat_id":1,"sender_id":1,"date":100,"text":"before upgrade"}}');
INSERT INTO events VALUES (1, 'user.created', '{"id":1,"is_bot":false,"first_name":"Alice"}');
INSERT INTO events VALUES (2, 'user.created', '{"id":2,"is_bot":true,"first_name":"Echo"}');
INSERT INTO events VALUES (3, 'chat.created', '{"id":1,"type":"private","user_id":1,"bot_id":2}');
INSERT INTO events VALUES (4, 'message.created', '{"id":1,"chat_id":1,"sender_id":1,"date":100,"text":"before upgrade"}');
CREATE TABLE client_tokens (digest TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id));
INSERT INTO messages VALUES (1, 2, '{"id":2,"chat_id":1,"sender_id":2,"date":100,"text":"Legacy bot reply"}');
INSERT INTO events VALUES (5, 'message.created', '{"id":2,"chat_id":1,"sender_id":2,"date":100,"text":"Legacy bot reply"}');

CREATE TABLE callbacks (
    id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
    bot_id INTEGER NOT NULL REFERENCES bots(id), request_id TEXT NOT NULL,
    request_body TEXT NOT NULL, body TEXT NOT NULL, answer TEXT, UNIQUE(user_id, request_id)
);
UPDATE bots SET next_update=3 WHERE id=2;
INSERT INTO callbacks VALUES ('legacy-callback',1,2,'legacy-tap','{"chat_id": 1, "message_id": 2, "data": "legacy"}','{"id": "legacy-callback", "user_id": 1, "chat_id": 1, "message": {"id": 2, "chat_id": 1, "sender_id": 2, "date": 100, "text": "Legacy bot reply"}, "data": "legacy", "chat_instance": "synthetic-chat-instance"}','{"text": "retained", "show_alert": false, "cache_time": 0}');
INSERT INTO events VALUES (6, 'callback.created', '{"id": "legacy-callback", "user_id": 1, "chat_id": 1, "message": {"id": 2, "chat_id": 1, "sender_id": 2, "date": 100, "text": "Legacy bot reply"}, "data": "legacy", "chat_instance": "synthetic-chat-instance"}');
INSERT INTO events VALUES (7, 'callback.answered', '{"id": "legacy-callback", "user_id": 1, "answer": {"text": "retained", "show_alert": false, "cache_time": 0}}');
INSERT INTO updates VALUES (2,2,'{"update_id": 2, "callback_query": {"id": "legacy-callback", "user_id": 1, "chat_id": 1, "message": {"id": 2, "chat_id": 1, "sender_id": 2, "date": 100, "text": "Legacy bot reply"}, "data": "legacy", "chat_instance": "synthetic-chat-instance"}}');
INSERT INTO bot_tokens VALUES ('c7906cb19ca1ce73a79f39e944a4d5a8eadc60a1f59ef842523c8d6a0acd3a07',2);
INSERT INTO client_tokens VALUES ('cd6f2bbed51c238ca3cadf6fcdd5ea3bf17761404c6cdb570bb1b808f3d63639',1);
