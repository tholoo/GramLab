# Album storage schema-9 fixture

`world.sql` is a pinned, token-free populated schema-9 database dump. It contains one synthetic
private chat, one standalone photo and one standalone document produced through the pre-album World
operations. The fixture was constructed before exercising the schema-10 migration by removing only
the three new album tables and restoring `user_version=9`; tests never generate it dynamically.

`tests/test_album_storage_migration.py` compares every legacy row before and after migration,
exercises concurrent openers and interruption at every new statement, checks foreign keys, reopens,
and publishes the first album with rollback-safe IDs. The fixture contains no client/bot tokens or
real identities.
