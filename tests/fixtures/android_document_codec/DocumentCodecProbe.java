// SPDX-License-Identifier: GPL-2.0-or-later
package org.telegram.gramlab;

import java.io.File;
import java.io.FileOutputStream;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.json.JSONArray;
import org.json.JSONObject;

/** Reflection probe for the actual descriptor codec, TLRPC and NativeByteBuffer classes. */
public final class DocumentCodecProbe {
    private static final String INVALID = "GRAMLAB_BRIDGE_INVALID_DOCUMENT";
    private static final String MAX_ID = "9223372036854775807";
    private static final JSONArray cases = new JSONArray();
    private static final JSONArray documents = new JSONArray();
    private static Method identifier;
    private static Method parse;
    private static Method project;
    private static Method customEmojiIdentifier;
    private static Class<?> documentClass;
    private static Class<?> inputSerializedDataClass;
    private static Class<?> outputSerializedDataClass;
    private static Constructor<?> nativeBufferConstructor;
    private static Method bufferReadInt32;
    private static Method bufferRewind;
    private static Method bufferReuse;
    private static int passed;
    private static int failed;

    private DocumentCodecProbe() {}

    private interface Case {
        void run() throws Exception;
    }

    private static void require(boolean value, String code) {
        if (!value) {
            throw new AssertionError(code);
        }
    }

    private static JSONObject row(String id, String fileName, String mimeType, Object size, String sha256)
            throws Exception {
        return new JSONObject()
                .put("document_id", id)
                .put("file_name", fileName)
                .put("mime_type", mimeType)
                .put("file_size", size)
                .put("sha256", sha256);
    }

    private static JSONObject ordinary(String id) throws Exception {
        return row(id, "report.pdf", "application/pdf", 123, repeat("a", 64));
    }

    private static String repeat(String value, int count) {
        StringBuilder result = new StringBuilder();
        for (int index = 0; index < count; index++) {
            result.append(value);
        }
        return result.toString();
    }

    private static JSONArray rows(Object... values) {
        JSONArray result = new JSONArray();
        for (Object value : values) {
            result.put(value);
        }
        return result;
    }

    private static Map<?, ?> decode(JSONArray value) throws Exception {
        Object decoded = parse.invoke(null, value);
        require(decoded instanceof Map, "parse_not_map");
        return (Map<?, ?>) decoded;
    }

    private static void rejectRows(JSONArray value) throws Exception {
        try {
            parse.invoke(null, value);
            throw new AssertionError("invalid_descriptor_accepted");
        } catch (InvocationTargetException failure) {
            Throwable cause = failure.getCause();
            require(cause instanceof IllegalArgumentException, "wrong_rejection_class");
            require(INVALID.equals(cause.getMessage()), "wrong_rejection_reason");
        }
    }

    private static void rejectIdentifier(Object value) throws Exception {
        try {
            identifier.invoke(null, value);
            throw new AssertionError("invalid_identifier_accepted");
        } catch (InvocationTargetException failure) {
            Throwable cause = failure.getCause();
            require(cause instanceof IllegalArgumentException, "wrong_identifier_rejection_class");
            require(INVALID.equals(cause.getMessage()), "wrong_identifier_rejection_reason");
        }
    }

    private static JSONObject describe(Object value) throws Exception {
        Class<?> tlObjectClass = Class.forName("org.telegram.tgnet.TLObject");
        Method objectSize = tlObjectClass.getMethod("getObjectSize");
        int expectedSize = ((Integer) objectSize.invoke(value)).intValue();
        Object buffer = nativeBufferConstructor.newInstance(Integer.valueOf(expectedSize));
        Object decoded;
        int serializedSize;
        try {
            Method serialize = value.getClass().getMethod("serializeToStream", outputSerializedDataClass);
            serialize.invoke(value, buffer);
            serializedSize = ((Integer) buffer.getClass().getMethod("position").invoke(buffer)).intValue();
            require(serializedSize == expectedSize, "native_buffer_size_mismatch");
            bufferRewind.invoke(buffer);
            int constructor = ((Integer) bufferReadInt32.invoke(buffer, Boolean.TRUE)).intValue();
            Method deserialize = documentClass.getMethod(
                    "TLdeserialize", inputSerializedDataClass, int.class, boolean.class);
            decoded = deserialize.invoke(null, buffer, Integer.valueOf(constructor), Boolean.TRUE);
            require(decoded != null, "native_deserialize_null");
            require(
                    ((Integer) buffer.getClass().getMethod("remaining").invoke(buffer)).intValue() == 0,
                    "native_bytes_remaining");
        } finally {
            bufferReuse.invoke(buffer);
        }

        Class<?> documentAttributeClass = Class.forName("org.telegram.tgnet.TLRPC$DocumentAttribute");
        List<?> attributes = (List<?>) field(decoded, "attributes");
        JSONArray describedAttributes = new JSONArray();
        for (Object attribute : attributes) {
            JSONObject description = new JSONObject()
                    .put("kind", attribute.getClass().getSimpleName());
            if ("TL_documentAttributeFilename".equals(attribute.getClass().getSimpleName())) {
                description.put("file_name", documentAttributeClass.getField("file_name").get(attribute));
            }
            describedAttributes.put(description);
        }

        byte[] fileReference = (byte[]) field(decoded, "file_reference");
        List<?> thumbs = (List<?>) field(decoded, "thumbs");
        List<?> videoThumbs = (List<?>) field(decoded, "video_thumbs");
        Class<?> imageLocationClass = Class.forName("org.telegram.messenger.ImageLocation");
        Object location = imageLocationClass.getMethod("getForDocument", documentClass)
                .invoke(null, decoded);
        String key = (String) imageLocationClass
                .getMethod("getKey", Object.class, Object.class, boolean.class)
                .invoke(location, decoded, null, Boolean.FALSE);
        String attachFileName = (String) Class.forName("org.telegram.messenger.FileLoader")
                .getMethod("getAttachFileName", tlObjectClass)
                .invoke(null, decoded);

        return new JSONObject()
                .put("kind", decoded.getClass().getSimpleName())
                .put("flags", field(decoded, "flags"))
                .put("id", Long.toString(((Long) field(decoded, "id")).longValue()))
                .put("dc_id", field(decoded, "dc_id"))
                .put("access_hash", field(decoded, "access_hash"))
                .put("file_reference_bytes", fileReference.length)
                .put("date", field(decoded, "date"))
                .put("mime_type", field(decoded, "mime_type"))
                .put("size", field(decoded, "size"))
                .put("thumbs", thumbs.size())
                .put("video_thumbs", videoThumbs.size())
                .put("attributes", describedAttributes)
                .put("key", key)
                .put("attach_file_name", attachFileName)
                .put("serialized_bytes", serializedSize);
    }

    private static Object field(Object value, String name) throws Exception {
        return documentClass.getField(name).get(value);
    }

    private static void run(String name, Case test) throws Exception {
        JSONObject record = new JSONObject().put("name", name);
        try {
            test.run();
            record.put("passed", true);
            passed++;
        } catch (Exception | AssertionError failure) {
            record.put("passed", false).put("failure_class", failure.getClass().getSimpleName());
            if (failure instanceof AssertionError) {
                record.put("assertion", failure.getMessage());
            }
            failed++;
        }
        cases.put(record);
    }

    public static void main(String[] arguments) throws Exception {
        if (arguments.length != 2) {
            throw new IllegalArgumentException("OUTPUT_DIRECTORY NATIVE_LIBRARY");
        }
        File output = new File(arguments[0]);
        if (output.exists() || !output.mkdir()) {
            throw new IllegalArgumentException("fresh output required");
        }
        Class<?> codec = Class.forName("org.telegram.gramlab.GramLabDocument");
        Class<?> entry = Class.forName("org.telegram.gramlab.GramLabDocument$Entry");
        identifier = codec.getMethod("identifier", Object.class);
        parse = codec.getMethod("parse", JSONArray.class);
        project = codec.getMethod("project", entry);
        customEmojiIdentifier = Class.forName("org.telegram.gramlab.GramLabCustomEmoji")
                .getMethod("identifier", Object.class);
        documentClass = Class.forName("org.telegram.tgnet.TLRPC$Document");
        inputSerializedDataClass = Class.forName("org.telegram.tgnet.InputSerializedData");
        outputSerializedDataClass = Class.forName("org.telegram.tgnet.OutputSerializedData");
        System.load(new File(arguments[1]).getAbsolutePath());
        Class<?> nativeBuffer = Class.forName("org.telegram.tgnet.NativeByteBuffer");
        nativeBufferConstructor = nativeBuffer.getConstructor(int.class);
        bufferReadInt32 = nativeBuffer.getMethod("readInt32", boolean.class);
        bufferRewind = nativeBuffer.getMethod("rewind");
        bufferReuse = nativeBuffer.getMethod("reuse");

        run("numeric_ordering_and_projection", () -> {
            String eightyOne = repeat("x", 80) + "🙂";
            JSONArray input = rows(
                    row("1", "گزارش🙂.pdf", "application/pdf", 1, repeat("a", 64)),
                    row("2", eightyOne, "", 50_000_000, repeat("b", 64)),
                    row("10", "archive.tar", "application/x-tar", 2, repeat("c", 64)),
                    row("2147483648", "sentinel.bin", "application/octet-stream", Long.valueOf(123), repeat("d", 64)),
                    row(MAX_ID, "maximum", "", 50_000_000, repeat("e", 64)));
            Map<?, ?> entries = decode(input);
            require(entries.size() == 5, "wrong_entry_count");
            List<String> order = new ArrayList<>();
            for (Map.Entry<?, ?> item : entries.entrySet()) {
                order.add(item.getKey().toString());
                documents.put(describe(project.invoke(null, item.getValue())));
            }
            require(
                    order.toString().equals("[1, 2, 10, 2147483648, 9223372036854775807]"),
                    "wrong_numeric_order");
            require(
                    ((Long) customEmojiIdentifier.invoke(null, "2147483648")).longValue()
                            == 2_147_483_648L,
                    "custom_emoji_sentinel_truncated");
            require(
                    ((Long) customEmojiIdentifier.invoke(null, MAX_ID)).longValue() == Long.MAX_VALUE,
                    "custom_emoji_max_truncated");
        });
        run("empty_array", () -> require(decode(new JSONArray()).isEmpty(), "empty_not_empty"));
        run("identifier_boundaries", () -> {
            require(((Long) identifier.invoke(null, "1")).longValue() == 1, "minimum_id");
            require(
                    ((Long) identifier.invoke(null, MAX_ID)).longValue() == Long.MAX_VALUE,
                    "maximum_id");
        });
        run("identifier_rejections", () -> {
            for (Object value : new Object[] {
                    "0", "-1", "+1", "01", " 1", "1 ", "1.0", "9223372036854775808",
                    Integer.valueOf(1), JSONObject.NULL
            }) {
                rejectIdentifier(value);
            }
        });
        run("row_not_object", () -> rejectRows(rows("document")));
        run("missing_fields", () -> {
            for (String name : new String[] {
                    "document_id", "file_name", "mime_type", "file_size", "sha256"
            }) {
                JSONObject value = ordinary("1");
                value.remove(name);
                rejectRows(rows(value));
            }
        });
        run("extra_field", () -> rejectRows(rows(ordinary("1").put("extra", true))));
        run("document_id_wrong_type", () -> rejectRows(rows(ordinary("1").put("document_id", 1))));
        run("duplicate_id", () -> rejectRows(rows(ordinary("1"), ordinary("1"))));
        run("out_of_order_id", () -> rejectRows(rows(ordinary("10"), ordinary("2"))));
        run("file_name_wrong_type", () -> rejectRows(rows(ordinary("1").put("file_name", 1))));
        run("file_name_empty", () -> rejectRows(rows(ordinary("1").put("file_name", ""))));
        run("file_name_too_long", () -> rejectRows(rows(ordinary("1").put("file_name", repeat("x", 82)))));
        run("file_name_slash", () -> rejectRows(rows(ordinary("1").put("file_name", "a/b"))));
        run("file_name_backslash", () -> rejectRows(rows(ordinary("1").put("file_name", "a\\b"))));
        run("file_name_nul", () -> rejectRows(rows(ordinary("1").put("file_name", "a\u0000b"))));
        run("file_name_high_surrogate", () -> rejectRows(rows(ordinary("1").put("file_name", "a\uD800"))));
        run("file_name_low_surrogate", () -> rejectRows(rows(ordinary("1").put("file_name", "a\uDC00"))));
        run("mime_wrong_type", () -> rejectRows(rows(ordinary("1").put("mime_type", 1))));
        run("mime_parameters", () -> rejectRows(rows(ordinary("1").put("mime_type", "text/plain;charset=utf-8"))));
        run("mime_whitespace", () -> rejectRows(rows(ordinary("1").put("mime_type", "text /plain"))));
        run("mime_missing_slash", () -> rejectRows(rows(ordinary("1").put("mime_type", "text"))));
        run("mime_non_ascii", () -> rejectRows(rows(ordinary("1").put("mime_type", "text/پلین"))));
        run("mime_too_long", () -> rejectRows(rows(ordinary("1").put("mime_type", "a/" + repeat("b", 255)))));
        run("size_string", () -> rejectRows(rows(ordinary("1").put("file_size", "1"))));
        run("size_float", () -> rejectRows(rows(ordinary("1").put("file_size", 1.0))));
        run("size_boolean", () -> rejectRows(rows(ordinary("1").put("file_size", true))));
        run("size_negative", () -> rejectRows(rows(ordinary("1").put("file_size", -1))));
        run("size_zero", () -> rejectRows(rows(ordinary("1").put("file_size", 0))));
        run("size_above_limit", () -> rejectRows(rows(ordinary("1").put("file_size", 50_000_001))));
        run("sha_wrong_type", () -> rejectRows(rows(ordinary("1").put("sha256", 1))));
        run("sha_uppercase", () -> rejectRows(rows(ordinary("1").put("sha256", repeat("A", 64)))));
        run("sha_wrong_length", () -> rejectRows(rows(ordinary("1").put("sha256", repeat("a", 63)))));
        run("sha_non_hex", () -> rejectRows(rows(ordinary("1").put("sha256", repeat("g", 64)))));

        JSONObject summary = new JSONObject()
                .put("schema", 1)
                .put("passed", passed)
                .put("failed", failed)
                .put("total", passed + failed)
                .put("custom_emoji_ids", rows("2147483648", MAX_ID))
                .put("documents", documents)
                .put("cases", cases);
        writeRecord(new File(output, "summary.json"), summary);
        System.out.println(summary);
        System.exit(failed == 0 ? 0 : 1);
    }

    private static void writeRecord(File path, JSONObject value) throws Exception {
        byte[] encoded = value.toString(2).getBytes(StandardCharsets.UTF_8);
        require(encoded.length <= 131072, "output_too_large");
        try (FileOutputStream stream = new FileOutputStream(path)) {
            stream.write(encoded);
        }
    }
}
