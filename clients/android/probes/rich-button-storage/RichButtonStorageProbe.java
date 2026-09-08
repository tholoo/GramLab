// SPDX-License-Identifier: GPL-2.0-or-later
package org.telegram.gramlab;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import java.io.File;
import java.io.FileOutputStream;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.IdentityHashMap;
import org.json.JSONArray;
import org.json.JSONObject;
import org.telegram.SQLite.SQLiteCursor;
import org.telegram.SQLite.SQLiteDatabase;
import org.telegram.SQLite.SQLitePreparedStatement;
import org.telegram.messenger.ApplicationLoader;
import org.telegram.messenger.MessageCustomParamsHelper;
import org.telegram.tgnet.ConnectionsManager;
import org.telegram.tgnet.NativeByteBuffer;
import org.telegram.tgnet.SerializedData;
import org.telegram.tgnet.TLRPC;
import org.telegram.tgnet.tl.TL_iv;

/** Original diagnostic: real Android, original JNI buffers and original SQLite wrapper.
 * Never starts ApplicationLoader.onCreate, an account, native_init, or an input action.
 */
public final class RichButtonStorageProbe {
    private static final int LIMIT = 1048576;
    private static File directory;
    private static SQLiteDatabase database;
    private static String currentCase;
    private static JSONObject outcome;
    private static int passed;
    private static int failed;
    private static String initializationPhase = "arguments";
    private static Method capture;
    private static TLRPC.Message lastLoaded;
    private static final class ParamsRejected extends Exception {
        private static final long serialVersionUID = 1L;
        ParamsRejected(RuntimeException cause) { super(cause); }
    }
    private static Field revisionField;
    private static Field provenanceField;

    private RichButtonStorageProbe() {}
    private interface Case { void run() throws Exception; }

    private static void require(boolean value, String code) {
        if (!value) throw new AssertionError(code);
    }

    private static void write(String name, byte[] bytes) throws Exception {
        try (FileOutputStream output = new FileOutputStream(new File(directory, name))) {
            output.write(bytes);
        }
    }

    private static void phase(String name) throws Exception {
        initializationPhase = name;
        System.out.println(new JSONObject().put("schema", 1).put("phase", name));
    }

    private static void run(String name, Case test) throws Exception {
        currentCase = name;
        outcome = new JSONObject().put("schema", 1).put("case", name);
        try {
            test.run();
            outcome.put("passed", true);
            passed++;
        } catch (Exception | AssertionError error) {
            outcome.put("passed", false).put("failure_class", error.getClass().getSimpleName());
            if (error instanceof AssertionError) outcome.put("assertion", error.getMessage());
            failed++;
        }
        write(name + ".json", outcome.toString(2).getBytes(StandardCharsets.UTF_8));
        System.out.println(new JSONObject().put("case", name).put("passed", outcome.get("passed")));
    }

    private static JSONObject button(String action) throws Exception {
        return new JSONObject().put("text", "Same / یکسان").put("callback_data", action);
    }

    private static JSONObject inline(String action) throws Exception {
        return new JSONObject().put("type", "button").put("button", button(action));
    }

    // Expected paths below are authored independently of production traversal.
    private static JSONObject fixture(String action) throws Exception {
        return new JSONObject().put("blocks", new JSONArray()
                .put(new JSONObject().put("type", "buttons").put("buttons", new JSONArray()
                        .put(button(action)).put(button(action))))
                .put(new JSONObject().put("type", "paragraph").put("text", new JSONArray()
                        .put("prefix ").put(new JSONObject().put("type", "bold")
                                .put("text", inline(action)))))
                .put(new JSONObject().put("type", "details").put("summary", inline(action))
                        .put("blocks", new JSONArray().put(new JSONObject().put("type", "blockquote")
                                .put("blocks", new JSONArray().put(new JSONObject()
                                        .put("type", "paragraph").put("text", inline(action))))
                                .put("credit", inline(action))))));
    }

    private static JSONArray expected(String action) throws Exception {
        String[] paths = {
            "[\"blocks\",0,\"buttons\",0]", "[\"blocks\",0,\"buttons\",1]",
            "[\"blocks\",1,\"text\",1,\"text\",\"button\"]",
            "[\"blocks\",2,\"summary\",\"button\"]",
            "[\"blocks\",2,\"blocks\",0,\"blocks\",0,\"text\",\"button\"]",
            "[\"blocks\",2,\"blocks\",0,\"credit\",\"button\"]"
        };
        JSONArray result = new JSONArray();
        for (String path : paths) result.put(new JSONObject().put("path", new JSONArray(path))
                .put("button", button(action)));
        return result;
    }

    private static Object[] objects(TLRPC.Message message) {
        TL_iv.RichMessage rich = message.rich_message;
        TL_iv.pageBlockButtonRow row = (TL_iv.pageBlockButtonRow) rich.blocks.get(0);
        TL_iv.pageBlockDetails details = (TL_iv.pageBlockDetails) rich.blocks.get(2);
        TL_iv.pageBlockBlockquoteBlocks quote = (TL_iv.pageBlockBlockquoteBlocks) details.blocks.get(0);
        return new Object[] { row.buttons.get(0), row.buttons.get(1),
            rich.blocks.get(1).text.texts.get(1).text, details.title,
            quote.blocks.get(0).text, quote.caption };
    }

    @SuppressWarnings("unchecked")
    private static IdentityHashMap<Object, Object> bindings() throws Exception {
        Field field = GramLabButtonObserver.class.getDeclaredField("bindings");
        field.setAccessible(true);
        return (IdentityHashMap<Object, Object>) field.get(null);
    }

    private static Object field(Object instance, String name) throws Exception {
        Field field = instance.getClass().getDeclaredField(name);
        field.setAccessible(true);
        return field.get(instance);
    }

    private static JSONArray mapped(TLRPC.Message message) throws Exception {
        JSONArray values = new JSONArray();
        for (Object object : objects(message)) {
            Object binding = bindings().get(object);
            JSONObject value = new JSONObject().put("class", object.getClass().getName())
                    .put("identity", System.identityHashCode(object)).put("mapped", binding != null);
            if (binding != null) value.put("revision", field(binding, "revision"))
                    .put("path", field(binding, "path")).put("button", field(binding, "button"))
                    .put("final_identity_matches", field(binding, "finalObject") == object)
                    .put("bound", field(binding, "bound")).put("ambiguous", field(binding, "ambiguous"));
            values.put(value);
        }
        return values;
    }

    private static void assertMapped(TLRPC.Message message, long revision, String action)
            throws Exception {
        JSONArray actual = mapped(message);
        outcome.put("actual", actual).put("expected", expected(action)).put("revision", revision);
        JSONArray wanted = expected(action);
        for (int i = 0; i < wanted.length(); i++) {
            JSONObject got = actual.getJSONObject(i);
            require(got.getBoolean("mapped"), "loaded_object_unbound_" + i);
            require(got.getLong("revision") == revision, "wrong_applied_revision_" + i);
            require(got.getBoolean("final_identity_matches"), "wrong_final_object_" + i);
            require(got.getBoolean("bound") && !got.getBoolean("ambiguous"), "unusable_binding_" + i);
            require(got.getJSONArray("path").toString().equals(
                    wanted.getJSONObject(i).getJSONArray("path").toString()), "wrong_path_" + i);
            JSONObject actualButton = got.getJSONObject("button");
            require(actualButton.length() == 2
                    && actualButton.getString("text").equals("Same / یکسان")
                    && actualButton.getString("callback_data").equals(action), "wrong_button_" + i);
        }
    }

    private static TLRPC.TL_message message(long revision, String action, boolean attach)
            throws Exception {
        TLRPC.TL_message message = bare();
        JSONObject canonical = new JSONObject().put("id", 91).put("chat_id", 7)
                .put("sender_id", 13).put("date", 1).put("text", "")
                .put("rich_message", fixture(action));
        message.rich_message = GramLabRichMessage.decode(canonical.getJSONObject("rich_message"), null, revision);
        message.flags2 |= 1 << 13;
        if (attach) invoke(capture, message, canonical, revision);
        return message;
    }

    private static TLRPC.TL_message bare() {
        TLRPC.TL_message message = new TLRPC.TL_message();
        message.id = 91;
        message.date = 1;
        message.message = "";
        message.peer_id = new TLRPC.TL_peerUser();
        message.peer_id.user_id = 17;
        message.from_id = new TLRPC.TL_peerUser();
        message.from_id.user_id = 13;
        message.dialog_id = 13;
        message.flags |= 1 << 8;
        return message;
    }

    private static Object invoke(Method method, Object... arguments) throws Exception {
        try {
            return method.invoke(null, arguments);
        } catch (InvocationTargetException error) {
            Throwable cause = error.getCause();
            if (cause instanceof Exception) throw (Exception) cause;
            if (cause instanceof Error) throw (Error) cause;
            throw error;
        }
    }

    private static byte[] bytes(NativeByteBuffer buffer) {
        if (buffer == null) return null;
        int length = buffer.length();
        buffer.position(0);
        return buffer.readData(length, true);
    }

    private static NativeByteBuffer buffer(byte[] bytes) throws Exception {
        if (bytes == null) return null;
        NativeByteBuffer result = new NativeByteBuffer(bytes.length);
        result.writeBytes(bytes);
        result.position(0);
        return result;
    }

    private static byte[] serialized(TLRPC.Message message) throws Exception {
        NativeByteBuffer output = new NativeByteBuffer(message.getObjectSize());
        try {
            message.serializeToStream(output);
            return bytes(output);
        } finally {
            output.reuse();
        }
    }

    private static TLRPC.Message decoded(byte[] bytes) throws Exception {
        NativeByteBuffer input = buffer(bytes);
        try {
            TLRPC.Message value = TLRPC.Message.TLdeserialize(input, input.readInt32(true), true);
            require(value != null, "null_original_message_decode");
            value.readAttachPath(input, 17);
            value.dialog_id = 13;
            return value;
        } finally {
            input.reuse();
        }
    }

    private static byte[] params(TLRPC.Message message) {
        NativeByteBuffer value = MessageCustomParamsHelper.writeLocalParams(message);
        try {
            return bytes(value);
        } finally {
            if (value != null) value.reuse();
        }
    }

    private static void readParams(TLRPC.Message message, byte[] bytes) throws Exception {
        NativeByteBuffer input = buffer(bytes);
        try {
            MessageCustomParamsHelper.readLocalParams(message, input);
        } finally {
            if (input != null) input.reuse();
        }
    }

    private static void store(byte[] data, byte[] custom) throws Exception {
        NativeByteBuffer a = buffer(data);
        NativeByteBuffer b = buffer(custom);
        SQLitePreparedStatement statement = database.executeFast(
                "REPLACE INTO messages_v2(mid,uid,data,custom_params) VALUES(91,13,?,?)");
        try {
            statement.bindByteBuffer(1, a);
            if (b == null) statement.bindNull(2); else statement.bindByteBuffer(2, b);
            statement.stepThis();
        } finally {
            statement.dispose();
            a.reuse();
            if (b != null) b.reuse();
        }
    }

    private static TLRPC.Message load(String suffix) throws Exception {
        SQLiteCursor cursor = database.queryFinalized(
                "SELECT data,custom_params FROM messages_v2 WHERE mid=91 AND uid=13");
        try {
            require(cursor.next(), "missing_sqlite_row");
            byte[] data = cursor.byteArrayValue(0);
            byte[] custom = cursor.isNull(1) ? null : cursor.byteArrayValue(1);
            write(currentCase + suffix + "-data.bin", data);
            if (custom != null) write(currentCase + suffix + "-params.bin", custom);
            TLRPC.Message message = decoded(data);
            lastLoaded = message;
            try {
                readParams(message, custom);
            } catch (RuntimeException rejected) {
                throw new ParamsRejected(rejected);
            }
            byte[] reconstructed = serialized(message);
            write(currentCase + suffix + "-reconstructed.bin", reconstructed);
            require(Arrays.equals(data, reconstructed), "original_tl_bytes_changed");
            return message;
        } finally {
            cursor.dispose();
        }
    }

    private static void reopen() throws Exception {
        database.close();
        database = new SQLiteDatabase(new File(directory, "probe.db").getPath());
    }

    private static byte[] metadata(long revision, JSONArray occurrences) throws Exception {
        return new JSONObject().put("schema", 1).put("revision", revision)
                .put("occurrences", occurrences).toString().getBytes(StandardCharsets.UTF_8);
    }

    private static void setMetadata(TLRPC.Message message, long revision, byte[] value) throws Exception {
        revisionField.setLong(message, revision);
        provenanceField.set(message, value);
    }

    private static void assertMetadata(TLRPC.Message message, long revision, JSONArray expected)
            throws Exception {
        require(revisionField.getLong(message) == revision, "metadata_revision_changed");
        byte[] raw = (byte[]) provenanceField.get(message);
        require(raw != null, "metadata_missing");
        JSONObject actual = new JSONObject(new String(raw, StandardCharsets.UTF_8));
        require(actual.length() == 3 && actual.getInt("schema") == 1
                && actual.getLong("revision") == revision, "metadata_envelope_changed");
        JSONArray occurrences = actual.getJSONArray("occurrences");
        require(occurrences.length() == expected.length(), "metadata_occurrence_count_changed");
        for (int i = 0; i < expected.length(); i++) {
            JSONObject a = occurrences.getJSONObject(i);
            JSONObject e = expected.getJSONObject(i);
            require(a.length() == 2 && a.getJSONArray("path").toString().equals(
                    e.getJSONArray("path").toString()), "metadata_path_changed");
            JSONObject got = a.getJSONObject("button");
            JSONObject wanted = e.getJSONObject("button");
            require(got.length() == wanted.length()
                    && got.getString("text").equals(wanted.getString("text"))
                    && got.getString("callback_data").equals(wanted.getString("callback_data")),
                    "metadata_button_changed");
        }
        outcome.put("metadata", actual);
    }

    private static void baseline(boolean attach) throws Exception {
        TLRPC.Message original = message(5, "same", attach);
        original.originalLanguage = "fa"; // Forces genuine stock custom-params serialization on normal25.
        assertMapped(original, 5, "same");
        outcome.put("original_bindings", mapped(original));
        Object[] old = objects(original);
        store(serialized(original), params(original));
        reopen();
        TLRPC.Message loaded = load("-reopened");
        JSONArray identities = new JSONArray();
        Object[] fresh = objects(loaded);
        for (int i = 0; i < old.length; i++) {
            identities.put(old[i] != fresh[i]);
            require(old[i] != fresh[i], "sqlite_did_not_reconstruct_object_" + i);
        }
        outcome.put("identities_changed", identities);
        require("fa".equals(loaded.originalLanguage), "stock_field_lost");
        assertMapped(loaded, 5, "same");
    }

    private static void invalid(String name, byte[] custom) throws Exception {
        run(name, () -> {
            TLRPC.Message original = message(31, "same", false);
            store(serialized(original), custom);
            TLRPC.Message loaded;
            try {
                loaded = load("-invalid");
            } catch (ParamsRejected rejection) {
                outcome.put("binary_rejection", rejection.getCause().getClass().getSimpleName());
                outcome.put("actual", mapped(lastLoaded));
                for (Object object : objects(lastLoaded))
                    require(!bindings().containsKey(object), "invalid_metadata_published_partial_mapping");
                throw new AssertionError("private_extension_discarded_original_message");
            }
            require("fa".equals(loaded.originalLanguage), "private_extension_lost_stock_field");
            JSONArray actual = mapped(loaded);
            outcome.put("actual", actual);
            for (int i = 0; i < actual.length(); i++)
                require(!actual.getJSONObject(i).getBoolean("mapped"), "invalid_metadata_published_partial_mapping");
        });
    }

    // Independent Params_v1 wire writer: stock originalLanguage="fa", then FLAG_14 tail.
    private static byte[] wire(long revision, byte[] payload) {
        SerializedData stream = new SerializedData();
        stream.writeInt32(1);
        stream.writeInt32((1 << 14) | 4);
        stream.writeBool(false);
        stream.writeBool(false);
        stream.writeBool(false);
        stream.writeInt64(0);
        stream.writeBool(false);
        stream.writeString("fa");
        stream.writeInt64(revision);
        stream.writeByteArray(payload);
        byte[] result = stream.toByteArray();
        stream.cleanup();
        return result;
    }

    private static void suite() throws Exception {
        run("metadata_only_roundtrip", () -> {
            TLRPC.Message original = message(6, "same", true);
            require(!MessageCustomParamsHelper.isEmpty(original), "provenance_omitted_by_isEmpty");
            byte[] custom = params(original);
            require(custom != null, "provenance_not_serialized");
            store(serialized(original), custom);
            assertMapped(load(""), 6, "same");
        });
        run("a_b_a_reopen", () -> {
            long[] revisions = {10, 11, 12};
            String[] actions = {"A", "B", "A"};
            JSONArray generations = new JSONArray();
            for (int i = 0; i < revisions.length; i++) {
                TLRPC.Message message = message(revisions[i], actions[i], true);
                store(serialized(message), params(message));
                reopen();
                TLRPC.Message loaded = load("-" + revisions[i]);
                assertMapped(loaded, revisions[i], actions[i]);
                generations.put(new JSONObject().put("revision", revisions[i]).put("actual", mapped(loaded)));
            }
            outcome.put("generations", generations);
        });
        run("incoming_provenance_wins_old_params", () -> {
            byte[] old = params(message(10, "A", true));
            TLRPC.Message incoming = message(11, "B", true);
            readParams(incoming, old);
            assertMetadata(incoming, 11, expected("B"));
            store(serialized(incoming), params(incoming));
            assertMapped(load(""), 11, "B");
        });
        run("stale_custom_only_update_preserves_row", () -> {
            TLRPC.Message stale = message(10, "A", true);
            TLRPC.Message current = message(11, "B", true);
            TLRPC.Message shell = new TLRPC.TL_message();
            readParams(shell, params(current));
            assertMetadata(shell, 11, expected("B"));
            MessageCustomParamsHelper.copyParams(stale, shell);
            assertMetadata(shell, 11, expected("B"));
            store(serialized(current), params(shell));
            assertMapped(load(""), 11, "B");
        });
        run("incoming_provenance_survives_legacy_params", () -> {
            TLRPC.Message old = bare();
            old.originalLanguage = "fa";
            TLRPC.Message incoming = message(16, "same", true);
            readParams(incoming, params(old));
            assertMetadata(incoming, 16, expected("same"));
            store(serialized(incoming), params(incoming));
            assertMapped(load(""), 16, "same");
        });
        run("empty_shell_restore_has_no_mapping_side_effect", () -> {
            byte[] metadata = params(message(17, "same", true));
            int before = bindings().size();
            TLRPC.Message shell = new TLRPC.TL_message();
            readParams(shell, metadata);
            assertMetadata(shell, 17, expected("same"));
            require(bindings().size() == before, "empty_shell_invented_object_binding");
        });
        run("legacy_absence", () -> {
            TLRPC.Message original = message(8, "same", false);
            original.originalLanguage = "fa";
            store(serialized(original), params(original));
            TLRPC.Message loaded = load("");
            require("fa".equals(loaded.originalLanguage), "legacy_stock_field_lost");
            for (Object object : objects(loaded)) require(!bindings().containsKey(object), "legacy_invented_binding");
        });
        run("ordinary_replacement_empty_is_authoritative", () -> {
            TLRPC.Message ordinary = bare();
            ordinary.message = "ordinary replacement";
            JSONObject canonical = new JSONObject().put("id", 91).put("chat_id", 7)
                    .put("sender_id", 13).put("date", 1).put("text", ordinary.message);
            invoke(capture, ordinary, canonical, 20L);
            readParams(ordinary, params(message(19, "same", true)));
            assertMetadata(ordinary, 20, new JSONArray());
            store(serialized(ordinary), params(ordinary));
            TLRPC.Message loaded = load("");
            require(loaded.rich_message == null && loaded.message.equals(ordinary.message), "ordinary_data_changed");
            assertMetadata(loaded, 20, new JSONArray());
        });
        run("button_free_replacement_empty_is_authoritative", () -> {
            TLRPC.Message clean = bare();
            JSONObject rich = new JSONObject().put("blocks", new JSONArray().put(
                    new JSONObject().put("type", "paragraph").put("text", "no actions")));
            clean.rich_message = GramLabRichMessage.decode(rich, null, 21);
            clean.flags2 |= 1 << 13;
            JSONObject canonical = new JSONObject().put("id", 91).put("chat_id", 7)
                    .put("sender_id", 13).put("date", 1).put("text", "").put("rich_message", rich);
            invoke(capture, clean, canonical, 21L);
            readParams(clean, params(message(19, "same", true)));
            assertMetadata(clean, 21, new JSONArray());
            store(serialized(clean), params(clean));
            assertMetadata(load(""), 21, new JSONArray());
        });
        run("topology_extra_row_object", () -> {
            TLRPC.Message original = message(31, "same", true);
            TL_iv.pageBlockButtonRow row = (TL_iv.pageBlockButtonRow) original.rich_message.blocks.get(0);
            row.buttons.add(row.buttons.get(0));
            store(serialized(original), params(original));
            TLRPC.Message loaded = load("");
            JSONArray actual = mapped(loaded);
            outcome.put("actual", actual);
            for (Object object : objects(loaded))
                require(!bindings().containsKey(object), "extra_topology_published_partial_mapping");
        });
        run("existing_fields_and_metadata", () -> {
            TLRPC.Message message = message(22, "same", true);
            message.voiceTranscription = "voice";
            message.voiceTranscriptionId = 29;
            message.voiceTranscriptionOpen = true;
            message.voiceTranscriptionFinal = true;
            message.voiceTranscriptionRated = true;
            message.voiceTranscriptionForce = true;
            message.premiumEffectWasPlayed = true;
            message.originalLanguage = "fa";
            message.translatedToLanguage = "en";
            message.errorAllowedPriceStars = 23;
            message.errorNewPriceStars = 24;
            message.summarizedOpen = true;
            message.translatedSummaryLanguage = "fa";
            message.translatedRichMessage = GramLabRichMessage.decode(new JSONObject().put("blocks", new JSONArray()
                    .put(new JSONObject().put("type", "paragraph").put("text", "translated"))), null, 0);
            store(serialized(message), params(message));
            TLRPC.Message loaded = load("");
            require("voice".equals(loaded.voiceTranscription) && loaded.voiceTranscriptionId == 29
                    && loaded.voiceTranscriptionOpen && loaded.voiceTranscriptionFinal
                    && loaded.voiceTranscriptionRated && loaded.voiceTranscriptionForce
                    && loaded.premiumEffectWasPlayed && "fa".equals(loaded.originalLanguage)
                    && "en".equals(loaded.translatedToLanguage) && loaded.errorAllowedPriceStars == 23
                    && loaded.errorNewPriceStars == 24 && loaded.summarizedOpen
                    && "fa".equals(loaded.translatedSummaryLanguage)
                    && loaded.translatedRichMessage != null, "existing_params_changed");
            assertMapped(loaded, 22, "same");
        });
        byte[] valid = metadata(31, expected("same"));
        run("independent_valid_wire_template", () -> {
            TLRPC.Message original = message(31, "same", false);
            store(serialized(original), wire(31, valid));
            assertMapped(load(""), 31, "same");
        });
        run("reordered_button_members", () -> {
            JSONArray entries = expected("same");
            for (int i = 0; i < entries.length(); i++) entries.getJSONObject(i).put("button",
                    new JSONObject().put("callback_data", "same").put("text", "Same / یکسان"));
            TLRPC.Message original = message(31, "same", false);
            store(serialized(original), wire(31, metadata(31, entries)));
            assertMapped(load(""), 31, "same");
        });
        invalid("invalid_utf8", wire(31, new byte[] {(byte) 0xc3, 0x28}));
        invalid("invalid_json", wire(31, "{".getBytes(StandardCharsets.UTF_8)));
        invalid("duplicate_json_member", wire(31, ("{\"schema\":1,\"schema\":1,\"revision\":31,\"occurrences\":"
                + expected("same") + "}").getBytes(StandardCharsets.UTF_8)));
        invalid("extension_over_limit", wire(31, new byte[LIMIT + 1]));
        byte[] good = wire(31, valid);
        invalid("truncated_extension", Arrays.copyOf(good, good.length - 7));
        invalid("trailing_binary", Arrays.copyOf(good, good.length + 4));
        invalid("trailing_json", wire(31, (new String(valid, StandardCharsets.UTF_8) + " {}")
                .getBytes(StandardCharsets.UTF_8)));
        invalid("revision_mismatch", wire(32, valid));
        JSONArray wrongCount = expected("same");
        wrongCount.remove(wrongCount.length() - 1);
        invalid("occurrence_count_mismatch", wire(31, metadata(31, wrongCount)));
        JSONArray wrongPath = expected("same");
        wrongPath.getJSONObject(5).put("path", new JSONArray("[\"blocks\",99,\"credit\",\"button\"]"));
        invalid("last_occurrence_path_mismatch", wire(31, metadata(31, wrongPath)));
        JSONArray wrongAction = expected("same");
        wrongAction.getJSONObject(5).getJSONObject("button").put("callback_data", "unrelated");
        invalid("last_occurrence_action_mismatch", wire(31, metadata(31, wrongAction)));
    }

    @SuppressWarnings("deprecation") // app_process requires the real main looper without Application.onCreate.
    public static void main(String[] args) {
        int status = 2;
        try {
            require(args.length == 3 && (args[2].equals("baseline") || args[2].equals("suite")), "arguments");
            phase("android_context");
            if (Looper.getMainLooper() == null) Looper.prepareMainLooper();
            Class<?> activityThread = Class.forName("android.app.ActivityThread");
            Object thread = activityThread.getMethod("systemMain").invoke(null);
            Context system = (Context) activityThread.getMethod("getSystemContext").invoke(thread);
            Context context = system.createPackageContext("org.gramlab.android", Context.CONTEXT_IGNORE_SECURITY);
            ApplicationLoader loader = new ApplicationLoader();
            Method attach = ApplicationLoader.class.getDeclaredMethod("attachBaseContext", Context.class);
            attach.setAccessible(true);
            attach.invoke(loader, context);
            ApplicationLoader.applicationLoaderInstance = loader;
            ApplicationLoader.applicationContext = context;
            ApplicationLoader.applicationHandler = new Handler(Looper.getMainLooper());
            directory = new File(args[1]).getCanonicalFile();
            require(directory.getParentFile().equals(context.getFilesDir().getCanonicalFile())
                    && directory.getName().startsWith("rich-button-storage-"), "dedicated_private_directory_required");
            require(directory.mkdir(), "fresh_directory_required");
            phase("native_library");
            System.load(args[0]);
            ConnectionsManager.native_setJava(false);
            NativeByteBuffer check = new NativeByteBuffer(4);
            check.writeInt32(0x12345678);
            check.position(0);
            require(check.readInt32(true) == 0x12345678, "native_buffer_initialization");
            check.reuse();
            phase("sqlite_open");
            database = new SQLiteDatabase(new File(directory, "probe.db").getPath());
            database.executeFast("CREATE TABLE messages_v2(mid INTEGER, uid INTEGER, data BLOB, custom_params BLOB, PRIMARY KEY(mid,uid))")
                    .stepThis().dispose();
            phase("behavioral_cases");
            boolean full = args[2].equals("suite");
            if (full) {
                capture = GramLabButtonObserver.class.getMethod("capture", TLRPC.Message.class, JSONObject.class, long.class);
                GramLabButtonObserver.class.getMethod("restore", TLRPC.Message.class);
                revisionField = TLRPC.Message.class.getField("gramLabRichButtonRevision");
                provenanceField = TLRPC.Message.class.getField("gramLabRichButtonProvenance");
            }
            run("sqlite_identity_roundtrip", () -> baseline(full));
            if (full) suite();
            JSONObject summary = new JSONObject().put("schema", 1).put("phase", "complete")
                    .put("passed", passed).put("failed", failed).put("mode", args[2]);
            write("summary.json", summary.toString(2).getBytes(StandardCharsets.UTF_8));
            System.out.println(summary);
            status = failed == 0 ? 0 : 1;
        } catch (Throwable error) {
            Throwable cause = error.getCause();
            System.out.println("{\"schema\":1,\"phase\":\"prerequisite_failure\",\"during\":\""
                    + initializationPhase + "\",\"class\":\"" + error.getClass().getSimpleName()
                    + "\",\"cause_class\":\"" + (cause == null ? "none" : cause.getClass().getSimpleName()) + "\"}");
        } finally {
            if (database != null) database.close();
        }
        System.exit(status);
    }
}
