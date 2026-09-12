BEGIN TRANSACTION;
CREATE TABLE asset_grants (
                    user_id INTEGER NOT NULL REFERENCES users(id), asset_id INTEGER NOT NULL
                    REFERENCES assets(id), PRIMARY KEY(user_id, asset_id)
                );
INSERT INTO "asset_grants" VALUES(1,1);
CREATE TABLE assets (id INTEGER PRIMARY KEY, sha256 TEXT NOT NULL UNIQUE REFERENCES media_blobs(sha256), mime_type TEXT NOT NULL, extension TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL);
INSERT INTO "assets" VALUES(1,'f4a96a9199d874b45d4c71b0a59ba3dd39abb8639f4022e8b8ada40680f2be82','image/png','png',16,16);
CREATE TABLE bot_document_files (bot_id INTEGER NOT NULL REFERENCES bots(id), file_id TEXT NOT NULL UNIQUE, document_id INTEGER NOT NULL REFERENCES documents(id), PRIMARY KEY(bot_id, document_id));
INSERT INTO "bot_document_files" VALUES(2,'gramlab_document_aXV8o2ViokVfxiocIAr0CjcHm7D-Ev4e',1);
CREATE TABLE bot_files (
                    bot_id INTEGER NOT NULL REFERENCES bots(id), file_id TEXT NOT NULL UNIQUE,
                    asset_id INTEGER NOT NULL REFERENCES assets(id), PRIMARY KEY(bot_id, asset_id)
                );
INSERT INTO "bot_files" VALUES(2,'gramlab_vj79DzHCm-DBIDth_c7hzzOTwbH2lcXS',1);
CREATE TABLE bot_tokens (
                    digest TEXT PRIMARY KEY, bot_id INTEGER NOT NULL REFERENCES bots(id)
                );
CREATE TABLE bots (
                    id INTEGER PRIMARY KEY REFERENCES users(id), next_update INTEGER NOT NULL,
                    allowed_updates TEXT NOT NULL DEFAULT '[]'
                );
INSERT INTO "bots" VALUES(2,1,'[]');
CREATE TABLE callback_revisions (
                    callback_id TEXT PRIMARY KEY REFERENCES callbacks(id),
                    message_revision INTEGER NOT NULL
                );
CREATE TABLE callbacks (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        bot_id INTEGER NOT NULL REFERENCES bots(id),
        request_id TEXT NOT NULL, request_body TEXT NOT NULL,
        body TEXT NOT NULL, answer TEXT,
        UNIQUE(user_id, request_id)
    );
CREATE TABLE chats (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    bot_id INTEGER NOT NULL REFERENCES users(id),
                    UNIQUE(user_id, bot_id)
                );
INSERT INTO "chats" VALUES(1,1,2);
CREATE TABLE client_changes (
        user_id INTEGER NOT NULL REFERENCES users(id), position INTEGER NOT NULL,
        event_sequence INTEGER NOT NULL UNIQUE REFERENCES events(sequence),
        PRIMARY KEY(user_id, position)
    );
INSERT INTO "client_changes" VALUES(1,1,4);
INSERT INTO "client_changes" VALUES(1,2,5);
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
CREATE TABLE configuration (
                    seed INTEGER NOT NULL, now INTEGER NOT NULL, world_id TEXT NOT NULL
                );
INSERT INTO "configuration" VALUES(910,91,'6105631b-e7c8-46d9-ba5f-f4dd4c5bd434');
CREATE TABLE custom_emoji (
                    id INTEGER PRIMARY KEY, fallback TEXT NOT NULL, free INTEGER NOT NULL,
                    needs_repainting INTEGER NOT NULL, main_asset_id INTEGER NOT NULL
                    REFERENCES assets(id),
                    thumbnail_asset_id INTEGER NOT NULL REFERENCES assets(id),
                    duration_ms INTEGER NOT NULL
                );
CREATE TABLE custom_emoji_counter (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1), next_id INTEGER NOT NULL
                );
INSERT INTO "custom_emoji_counter" VALUES(1,1);
CREATE TABLE custom_emoji_grants (
                    user_id INTEGER NOT NULL REFERENCES users(id), custom_emoji_id INTEGER NOT NULL
                    REFERENCES custom_emoji(id), PRIMARY KEY(user_id, custom_emoji_id)
                );
CREATE TABLE custom_emoji_registrations (
                    request_id TEXT PRIMARY KEY, request_body TEXT NOT NULL,
                    custom_emoji_id INTEGER NOT NULL REFERENCES custom_emoji(id)
                );
CREATE TABLE document_grants (user_id INTEGER NOT NULL REFERENCES users(id), document_id INTEGER NOT NULL REFERENCES documents(id), PRIMARY KEY(user_id, document_id));
INSERT INTO "document_grants" VALUES(1,1);
CREATE TABLE documents (id INTEGER PRIMARY KEY, sha256 TEXT NOT NULL REFERENCES media_blobs(sha256), file_name TEXT NOT NULL, mime_type TEXT NOT NULL, file_unique_id TEXT NOT NULL UNIQUE, UNIQUE(sha256, file_name, mime_type));
INSERT INTO "documents" VALUES(1,'943f739f4c7f5b39abd4d1eff28ccf006b1825ff22250670c55685f5e2a45d3d','v9.txt','text/plain','gramlab_document_unique_bba517e07cb49815303163ec4bcb86a2687dca479cc569b0937ce8967b4f2f7f');
CREATE TABLE events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL, body TEXT NOT NULL
                );
INSERT INTO "events" VALUES(1,'user.created','{"is_bot": false, "first_name": "Ada", "id": 1}');
INSERT INTO "events" VALUES(2,'user.created','{"is_bot": true, "first_name": "Albums", "id": 2}');
INSERT INTO "events" VALUES(3,'chat.created','{"id": 1, "type": "private", "user_id": 1, "bot_id": 2}');
INSERT INTO "events" VALUES(4,'message.created','{"id": 1, "chat_id": 1, "sender_id": 2, "date": 91, "text": "", "photo": {"asset_id": 1}}');
INSERT INTO "events" VALUES(5,'message.created','{"id": 2, "chat_id": 1, "sender_id": 2, "date": 91, "text": "", "document": {"document_id": "1"}}');
CREATE TABLE media_blobs (sha256 TEXT PRIMARY KEY, body BLOB NOT NULL);
INSERT INTO "media_blobs" VALUES('f4a96a9199d874b45d4c71b0a59ba3dd39abb8639f4022e8b8ada40680f2be82',X'89504E470D0A1A0A0000000D49484452000000100000001008060000001FF3FF61000002FC4944415478DA2DD30D53CC511CC5F1FF4B598A103AC446149B4294C728A22842145188301445142153881045188AA21445469429A2D8F0127EEFE038ECDE1770E7DECF9CAF43978B3153C0CC70B07C91B139011CD90C46661BD30F832525E0C3CBC6C15B60D8637043BBF1F807F0EE37D0E59D4F277829F8EFE46D3556EF053B8F8181678DB15560F65DF06293B1F53538DA0746FD306E0B02CFCE009F788CDF96818E7B3F985C68FF2FA9BB0EF6DE3786B480096FC1FC0163CD2FB03B189C30CB181F03EE5D055E4935B6EF02C7E4EB024FAD31E31158DAE67BC9D010183E164C0D3116CD051B62C1FEB5C6D07430690F78E488F1D619F0FD1570F21DA313F709CC19012BC71BDB427D97C4C41B33D7CB641BD89C6B1C392E933230FDAAB1A45E26CFC0C12E63D867BD20310C2C8836D6AE047B52C0E09DBEEFE49D04AB2B8C9D3764D208C6BE3066F7C8E40BD8EA328E0A3E4AF04E5A9AB17837D858000E9C36BA2B6572DBF792BA5732E90543BE1B130265320DAC8934760B7E4212182F7827EB1C58510DB6DC337A9B41CF1B30A3DF58FAD36F32D3181E2593E560D10663C30E99083E54F049E7F58283ADE0F577C6AE4130E8371837D998335B260BC1B6D5BEEFC4646927878CE5C532B9A49D083E52F0E982770A038CF500FB22C0E94B8C898932D902D6E6187B8ECAA4D4BF933A993CD54E3A8D81828F157CB6E09D328DA129191CDE6E8CC803D34E80C5E5C6C66B326900DDCF8DC9DD7E935163EF2499083E41F0F98277AA34868E53C6808BE0E29B60D64363C54B99BC07BD5F8D9E313299AA9DCCF17D67688D7622F854C11709DEB9A3317C78024EED00577F341E1C96C938B06BBA31689E4CE2B49375C6CA0C99ECF3EF44F099822F17BCF35863F8EA05674F34A6B8C1C20560FD0A63DF4699648289078C054532B9A09DD418831FF84D045F2D78E7A5C6F05B1546ABC21DAAB04C1536A9C2615518A10AD35461B12A6C548503AAD0AD0A9303FCED08DE716D2227A9C2E5AA30571556A9C20E5518A00A17ABC22C5558A10A5B54A157157A546186E04B05CF3F2EFE051779833630C10CD60000000049454E44AE426082');
INSERT INTO "media_blobs" VALUES('943f739f4c7f5b39abd4d1eff28ccf006b1825ff22250670c55685f5e2a45d3d',X'763920646F63756D656E74');
CREATE TABLE message_revisions (
                    chat_id INTEGER NOT NULL, message_id INTEGER NOT NULL,
                    revision INTEGER NOT NULL,
                    PRIMARY KEY(chat_id, message_id), FOREIGN KEY(chat_id, message_id)
                    REFERENCES messages(chat_id, id)
                );
INSERT INTO "message_revisions" VALUES(1,1,4);
INSERT INTO "message_revisions" VALUES(1,2,5);
CREATE TABLE messages (
                    chat_id INTEGER NOT NULL REFERENCES chats(id),
                    id INTEGER NOT NULL, body TEXT NOT NULL, PRIMARY KEY(chat_id, id)
                );
INSERT INTO "messages" VALUES(1,1,'{"id": 1, "chat_id": 1, "sender_id": 2, "date": 91, "text": "", "photo": {"asset_id": 1}}');
INSERT INTO "messages" VALUES(1,2,'{"id": 2, "chat_id": 1, "sender_id": 2, "date": 91, "text": "", "document": {"document_id": "1"}}');
CREATE TABLE updates (
                    bot_id INTEGER NOT NULL REFERENCES bots(id),
                    id INTEGER NOT NULL, body TEXT NOT NULL, PRIMARY KEY(bot_id, id)
                );
CREATE TABLE users (id INTEGER PRIMARY KEY, body TEXT NOT NULL);
INSERT INTO "users" VALUES(1,'{"is_bot": false, "first_name": "Ada"}');
INSERT INTO "users" VALUES(2,'{"is_bot": true, "first_name": "Albums"}');
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('events',5);
COMMIT;
PRAGMA user_version=9;
