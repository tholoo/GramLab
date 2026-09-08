BEGIN TRANSACTION;
CREATE TABLE asset_grants (
                    user_id INTEGER NOT NULL REFERENCES users(id), asset_id INTEGER NOT NULL
                    REFERENCES assets(id), PRIMARY KEY(user_id, asset_id)
                );
INSERT INTO "asset_grants" VALUES(1,1);
INSERT INTO "asset_grants" VALUES(3,1);
INSERT INTO "asset_grants" VALUES(1,2);
INSERT INTO "asset_grants" VALUES(1,3);
INSERT INTO "asset_grants" VALUES(1,4);
CREATE TABLE assets (id INTEGER PRIMARY KEY, sha256 TEXT NOT NULL UNIQUE REFERENCES media_blobs(sha256), mime_type TEXT NOT NULL, extension TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL);
INSERT INTO "assets" VALUES(1,'2f9c7d9ce3089854969acaf0d3dec2d9b1ad83b216004d312c8f6bf26759ff01','image/png','png',3,2);
INSERT INTO "assets" VALUES(2,'d491b2d0000ea8d6945e7101d992d2b09706f453720f3f19ae32d0571e896df1','image/png','png',3,2);
INSERT INTO "assets" VALUES(3,'7e1b283fb74b684cfaed135e5ce02ce6a0fc4824e4fb29c493f83fe05ccc0107','image/webp','webp',100,100);
INSERT INTO "assets" VALUES(4,'6d97276da8fc4212d117000d1d0c0c83e86025004fd08257768d547e3527c034','image/webp','webp',16,16);
CREATE TABLE bot_files (
                    bot_id INTEGER NOT NULL REFERENCES bots(id), file_id TEXT NOT NULL UNIQUE,
                    asset_id INTEGER NOT NULL REFERENCES assets(id), PRIMARY KEY(bot_id, asset_id)
                );
INSERT INTO "bot_files" VALUES(2,'gramlab_V_8UBoLpOaxZpHmdTkw_xRYGjmymNi9j',1);
INSERT INTO "bot_files" VALUES(2,'gramlab_zgA8HeNR72M8WIGmJf5zrWNLidqWlhad',2);
INSERT INTO "bot_files" VALUES(2,'gramlab_v5HrJVS9rGxRiiz5U7NHqLaF4OA-aTrM',3);
INSERT INTO "bot_files" VALUES(2,'gramlab_VQeBl_WVFfEA56agPWI1BcmuwBb0i2tV',4);
CREATE TABLE bot_tokens (
                    digest TEXT PRIMARY KEY, bot_id INTEGER NOT NULL REFERENCES bots(id)
                );
INSERT INTO "bot_tokens" VALUES('ea7b1878d215d694ed89faef2e430fc58a96097096319f8e688196fdd77b004b',2);
CREATE TABLE bots (
                    id INTEGER PRIMARY KEY REFERENCES users(id), next_update INTEGER NOT NULL,
                    allowed_updates TEXT NOT NULL DEFAULT '[]'
                );
INSERT INTO "bots" VALUES(2,4,'[]');
INSERT INTO "bots" VALUES(5,1,'[]');
CREATE TABLE callback_revisions (
                    callback_id TEXT PRIMARY KEY REFERENCES callbacks(id),
                    message_revision INTEGER NOT NULL
                );
INSERT INTO "callback_revisions" VALUES('5a62bb8c-75d0-4980-a177-5baec2ddbb91',9);
INSERT INTO "callback_revisions" VALUES('1ba3f606-157b-4bed-b904-ef69a481c284',15);
CREATE TABLE callbacks (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        bot_id INTEGER NOT NULL REFERENCES bots(id),
        request_id TEXT NOT NULL, request_body TEXT NOT NULL,
        body TEXT NOT NULL, answer TEXT,
        UNIQUE(user_id, request_id)
    );
INSERT INTO "callbacks" VALUES('5a62bb8c-75d0-4980-a177-5baec2ddbb91',1,2,'photo','{"chat_id": 1, "data": "tap", "message_id": 1}','{"id": "5a62bb8c-75d0-4980-a177-5baec2ddbb91", "user_id": 1, "chat_id": 1, "message": {"id": 1, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "", "rich_message": {"blocks": [{"type": "photo", "asset_id": 1, "caption": {"text": "A \ud83d\uddbc"}}]}, "reply_markup": {"inline_keyboard": [[{"text": "Tap", "callback_data": "tap"}]]}}, "data": "tap", "chat_instance": "e6a325689a2d9414b0771b7bdede7f317e8961593dff546c72e060406f87695f"}','{"text": "Recorded", "show_alert": false, "cache_time": 0}');
INSERT INTO "callbacks" VALUES('1ba3f606-157b-4bed-b904-ef69a481c284',1,2,'emoji','{"chat_id": 1, "data": "tap", "message_id": 3}','{"id": "1ba3f606-157b-4bed-b904-ef69a481c284", "user_id": 1, "chat_id": 1, "message": {"id": 3, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "\ud83d\ude42\ud83d\ude42", "entities": [{"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": "41"}, {"type": "custom_emoji", "offset": 2, "length": 2, "custom_emoji_id": "42"}]}, "data": "tap", "chat_instance": "e6a325689a2d9414b0771b7bdede7f317e8961593dff546c72e060406f87695f"}',NULL);
CREATE TABLE chats (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    bot_id INTEGER NOT NULL REFERENCES users(id),
                    UNIQUE(user_id, bot_id)
                );
INSERT INTO "chats" VALUES(1,1,2);
INSERT INTO "chats" VALUES(2,3,2);
INSERT INTO "chats" VALUES(3,4,5);
CREATE TABLE client_changes (
        user_id INTEGER NOT NULL REFERENCES users(id), position INTEGER NOT NULL,
        event_sequence INTEGER NOT NULL UNIQUE REFERENCES events(sequence),
        PRIMARY KEY(user_id, position)
    );
INSERT INTO "client_changes" VALUES(1,1,9);
INSERT INTO "client_changes" VALUES(1,2,10);
INSERT INTO "client_changes" VALUES(3,1,11);
INSERT INTO "client_changes" VALUES(1,3,14);
INSERT INTO "client_changes" VALUES(1,4,15);
INSERT INTO "client_changes" VALUES(1,5,17);
INSERT INTO "client_changes" VALUES(1,6,18);
INSERT INTO "client_changes" VALUES(4,1,19);
CREATE TABLE client_sends (
        user_id INTEGER NOT NULL REFERENCES users(id),
        chat_id INTEGER NOT NULL REFERENCES chats(id), request_id TEXT NOT NULL,
        request_body TEXT NOT NULL, body TEXT NOT NULL, position INTEGER NOT NULL,
        PRIMARY KEY(user_id, chat_id, request_id),
        FOREIGN KEY(user_id, position) REFERENCES client_changes(user_id, position)
    );
CREATE TABLE client_tokens (
                    digest TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id)
                );
INSERT INTO "client_tokens" VALUES('c24e392df14707e8fcf332a4f6919a8e441c538c2066df4f10e5f721039b6ef7',1);
CREATE TABLE configuration (
                    seed INTEGER NOT NULL, now INTEGER NOT NULL, world_id TEXT NOT NULL
                );
INSERT INTO "configuration" VALUES(96,1700000000,'92626c7b-51bd-47ab-b226-6ca06335aa8b');
CREATE TABLE custom_emoji (
                    id INTEGER PRIMARY KEY, fallback TEXT NOT NULL, free INTEGER NOT NULL,
                    needs_repainting INTEGER NOT NULL, main_asset_id INTEGER NOT NULL
                    REFERENCES assets(id),
                    thumbnail_asset_id INTEGER NOT NULL REFERENCES assets(id),
                    duration_ms INTEGER NOT NULL
                );
INSERT INTO "custom_emoji" VALUES(41,'🙂',1,0,3,4,0);
INSERT INTO "custom_emoji" VALUES(42,'🙂',1,0,3,4,0);
CREATE TABLE custom_emoji_counter (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1), next_id INTEGER NOT NULL
                );
INSERT INTO "custom_emoji_counter" VALUES(1,1);
CREATE TABLE custom_emoji_grants (
                    user_id INTEGER NOT NULL REFERENCES users(id), custom_emoji_id INTEGER NOT NULL
                    REFERENCES custom_emoji(id), PRIMARY KEY(user_id, custom_emoji_id)
                );
INSERT INTO "custom_emoji_grants" VALUES(1,41);
INSERT INTO "custom_emoji_grants" VALUES(1,42);
CREATE TABLE custom_emoji_registrations (
                    request_id TEXT PRIMARY KEY, request_body TEXT NOT NULL,
                    custom_emoji_id INTEGER NOT NULL REFERENCES custom_emoji(id)
                );
INSERT INTO "custom_emoji_registrations" VALUES('emoji-41','{"custom_emoji_id": "41", "duration_ms": 0, "fallback": "\ud83d\ude42", "free": true, "main": "7e1b283fb74b684cfaed135e5ce02ce6a0fc4824e4fb29c493f83fe05ccc0107", "needs_repainting": false, "thumbnail": "6d97276da8fc4212d117000d1d0c0c83e86025004fd08257768d547e3527c034"}',41);
INSERT INTO "custom_emoji_registrations" VALUES('emoji-42','{"custom_emoji_id": "42", "duration_ms": 0, "fallback": "\ud83d\ude42", "free": true, "main": "7e1b283fb74b684cfaed135e5ce02ce6a0fc4824e4fb29c493f83fe05ccc0107", "needs_repainting": false, "thumbnail": "6d97276da8fc4212d117000d1d0c0c83e86025004fd08257768d547e3527c034"}',42);
CREATE TABLE events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL, body TEXT NOT NULL
                );
INSERT INTO "events" VALUES(1,'user.created','{"is_bot": false, "first_name": "Ada", "id": 1}');
INSERT INTO "events" VALUES(2,'user.created','{"is_bot": true, "first_name": "Media", "id": 2}');
INSERT INTO "events" VALUES(3,'user.created','{"is_bot": false, "first_name": "Photo recipient", "id": 3}');
INSERT INTO "events" VALUES(4,'user.created','{"is_bot": false, "first_name": "Stranger", "id": 4}');
INSERT INTO "events" VALUES(5,'user.created','{"is_bot": true, "first_name": "Other bot", "id": 5}');
INSERT INTO "events" VALUES(6,'chat.created','{"id": 1, "type": "private", "user_id": 1, "bot_id": 2}');
INSERT INTO "events" VALUES(7,'chat.created','{"id": 2, "type": "private", "user_id": 3, "bot_id": 2}');
INSERT INTO "events" VALUES(8,'chat.created','{"id": 3, "type": "private", "user_id": 4, "bot_id": 5}');
INSERT INTO "events" VALUES(9,'message.created','{"id": 1, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "", "rich_message": {"blocks": [{"type": "photo", "asset_id": 1, "caption": {"text": "A \ud83d\uddbc"}}]}, "reply_markup": {"inline_keyboard": [[{"text": "Tap", "callback_data": "tap"}]]}}');
INSERT INTO "events" VALUES(10,'message.created','{"id": 2, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "", "photo": {"asset_id": 1}}');
INSERT INTO "events" VALUES(11,'message.created','{"id": 1, "chat_id": 2, "sender_id": 2, "date": 1700000000, "text": "", "photo": {"asset_id": 1}}');
INSERT INTO "events" VALUES(12,'callback.created','{"id": "5a62bb8c-75d0-4980-a177-5baec2ddbb91", "user_id": 1, "chat_id": 1, "message": {"id": 1, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "", "rich_message": {"blocks": [{"type": "photo", "asset_id": 1, "caption": {"text": "A \ud83d\uddbc"}}]}, "reply_markup": {"inline_keyboard": [[{"text": "Tap", "callback_data": "tap"}]]}}, "data": "tap", "chat_instance": "e6a325689a2d9414b0771b7bdede7f317e8961593dff546c72e060406f87695f"}');
INSERT INTO "events" VALUES(13,'callback.answered','{"id": "5a62bb8c-75d0-4980-a177-5baec2ddbb91", "user_id": 1, "answer": {"text": "Recorded", "show_alert": false, "cache_time": 0}}');
INSERT INTO "events" VALUES(14,'message.edited','{"id": 1, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "", "edit_date": 1700000000, "rich_message": {"blocks": [{"type": "photo", "asset_id": 2}]}}');
INSERT INTO "events" VALUES(15,'message.created','{"id": 3, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "\ud83d\ude42\ud83d\ude42", "entities": [{"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": "41"}, {"type": "custom_emoji", "offset": 2, "length": 2, "custom_emoji_id": "42"}]}');
INSERT INTO "events" VALUES(16,'callback.created','{"id": "1ba3f606-157b-4bed-b904-ef69a481c284", "user_id": 1, "chat_id": 1, "message": {"id": 3, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "\ud83d\ude42\ud83d\ude42", "entities": [{"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": "41"}, {"type": "custom_emoji", "offset": 2, "length": 2, "custom_emoji_id": "42"}]}, "data": "tap", "chat_instance": "e6a325689a2d9414b0771b7bdede7f317e8961593dff546c72e060406f87695f"}');
INSERT INTO "events" VALUES(17,'message.edited','{"id": 3, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "Edited to plain", "edit_date": 1700000000}');
INSERT INTO "events" VALUES(18,'message.created','{"id": 4, "chat_id": 1, "sender_id": 1, "date": 1700000000, "text": "User reply"}');
INSERT INTO "events" VALUES(19,'message.created','{"id": 1, "chat_id": 3, "sender_id": 5, "date": 1700000000, "text": "Isolated"}');
CREATE TABLE media_blobs (sha256 TEXT PRIMARY KEY, body BLOB NOT NULL);
INSERT INTO "media_blobs" VALUES('2f9c7d9ce3089854969acaf0d3dec2d9b1ad83b216004d312c8f6bf26759ff01',X'89504E470D0A1A0A0000000D49484452000000030000000208020000001216F14D0000001549444154789C6314D1B061606060606060628001000884007C707811050000000049454E44AE426082');
INSERT INTO "media_blobs" VALUES('d491b2d0000ea8d6945e7101d992d2b09706f453720f3f19ae32d0571e896df1',X'89504E470D0A1A0A0000000D49484452000000030000000208020000001216F14D0000001549444154789C63740B886260606060606062800100110800F4E02F705B0000000049454E44AE426082');
INSERT INTO "media_blobs" VALUES('7e1b283fb74b684cfaed135e5ce02ce6a0fc4824e4fb29c493f83fe05ccc0107',X'524946464A000000574542505650384C3D0000002F63C0181017201048421A7C60814012D2FE54230804521CC648CF7F40FF02458D24298BFEE8CEE4D83C01F889E8FF04D04602C05D389231577F50BE7F00');
INSERT INTO "media_blobs" VALUES('6d97276da8fc4212d117000d1d0c0c83e86025004fd08257768d547e3527c034',X'524946463E000000574542505650384C310000002F0FC003100F30688335F0F31FF05013D96AF47297488855A421050994B9CA8888E87F022896BCC458F2E692185E2C293F00');
CREATE TABLE message_revisions (
                    chat_id INTEGER NOT NULL, message_id INTEGER NOT NULL,
                    revision INTEGER NOT NULL,
                    PRIMARY KEY(chat_id, message_id), FOREIGN KEY(chat_id, message_id)
                    REFERENCES messages(chat_id, id)
                );
INSERT INTO "message_revisions" VALUES(1,2,10);
INSERT INTO "message_revisions" VALUES(2,1,11);
INSERT INTO "message_revisions" VALUES(1,1,14);
INSERT INTO "message_revisions" VALUES(1,3,17);
INSERT INTO "message_revisions" VALUES(1,4,18);
INSERT INTO "message_revisions" VALUES(3,1,19);
CREATE TABLE messages (
                    chat_id INTEGER NOT NULL REFERENCES chats(id),
                    id INTEGER NOT NULL, body TEXT NOT NULL, PRIMARY KEY(chat_id, id)
                );
INSERT INTO "messages" VALUES(1,1,'{"id": 1, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "", "edit_date": 1700000000, "rich_message": {"blocks": [{"type": "photo", "asset_id": 2}]}}');
INSERT INTO "messages" VALUES(1,2,'{"id": 2, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "", "photo": {"asset_id": 1}}');
INSERT INTO "messages" VALUES(2,1,'{"id": 1, "chat_id": 2, "sender_id": 2, "date": 1700000000, "text": "", "photo": {"asset_id": 1}}');
INSERT INTO "messages" VALUES(1,3,'{"id": 3, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "Edited to plain", "edit_date": 1700000000}');
INSERT INTO "messages" VALUES(1,4,'{"id": 4, "chat_id": 1, "sender_id": 1, "date": 1700000000, "text": "User reply"}');
INSERT INTO "messages" VALUES(3,1,'{"id": 1, "chat_id": 3, "sender_id": 5, "date": 1700000000, "text": "Isolated"}');
CREATE TABLE updates (
                    bot_id INTEGER NOT NULL REFERENCES bots(id),
                    id INTEGER NOT NULL, body TEXT NOT NULL, PRIMARY KEY(bot_id, id)
                );
INSERT INTO "updates" VALUES(2,1,'{"update_id": 1, "callback_query": {"id": "5a62bb8c-75d0-4980-a177-5baec2ddbb91", "user_id": 1, "chat_id": 1, "message": {"id": 1, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "", "rich_message": {"blocks": [{"type": "photo", "asset_id": 1, "caption": {"text": "A \ud83d\uddbc"}}]}, "reply_markup": {"inline_keyboard": [[{"text": "Tap", "callback_data": "tap"}]]}}, "data": "tap", "chat_instance": "e6a325689a2d9414b0771b7bdede7f317e8961593dff546c72e060406f87695f"}}');
INSERT INTO "updates" VALUES(2,2,'{"update_id": 2, "callback_query": {"id": "1ba3f606-157b-4bed-b904-ef69a481c284", "user_id": 1, "chat_id": 1, "message": {"id": 3, "chat_id": 1, "sender_id": 2, "date": 1700000000, "text": "\ud83d\ude42\ud83d\ude42", "entities": [{"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": "41"}, {"type": "custom_emoji", "offset": 2, "length": 2, "custom_emoji_id": "42"}]}, "data": "tap", "chat_instance": "e6a325689a2d9414b0771b7bdede7f317e8961593dff546c72e060406f87695f"}}');
INSERT INTO "updates" VALUES(2,3,'{"update_id": 3, "message": {"id": 4, "chat_id": 1, "sender_id": 1, "date": 1700000000, "text": "User reply"}}');
CREATE TABLE users (id INTEGER PRIMARY KEY, body TEXT NOT NULL);
INSERT INTO "users" VALUES(1,'{"is_bot": false, "first_name": "Ada"}');
INSERT INTO "users" VALUES(2,'{"is_bot": true, "first_name": "Media"}');
INSERT INTO "users" VALUES(3,'{"is_bot": false, "first_name": "Photo recipient"}');
INSERT INTO "users" VALUES(4,'{"is_bot": false, "first_name": "Stranger"}');
INSERT INTO "users" VALUES(5,'{"is_bot": true, "first_name": "Other bot"}');
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('events',19);
COMMIT;
PRAGMA user_version=8;
