-- GramLab schema 2 from dc37753, with a stable world identity and pending delivery.
PRAGMA user_version=2;
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
