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
    private static final int DIAGNOSTIC_TEXT_LIMIT = 256;
    private static final int CAUSE_LIMIT = 8;
    private static final int STACK_FRAME_LIMIT = 4;
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
    private static String stage = "bootstrap";
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
        stage = "describe.tl_object_class";
        Class<?> tlObjectClass = Class.forName("org.telegram.tgnet.TLObject");
        stage = "describe.get_object_size_method";
        Method objectSize = tlObjectClass.getMethod("getObjectSize");
        stage = "describe.get_object_size";
        int expectedSize = ((Integer) objectSize.invoke(value)).intValue();
        stage = "describe.allocate_native_buffer";
        Object buffer = nativeBufferConstructor.newInstance(Integer.valueOf(expectedSize));
        Object decoded;
        int serializedSize;
        try {
            stage = "describe.serialize_method";
            Method serialize = value.getClass().getMethod("serializeToStream", outputSerializedDataClass);
            stage = "describe.serialize";
            serialize.invoke(value, buffer);
            stage = "describe.position_method";
            Method position = buffer.getClass().getMethod("position");
            stage = "describe.position";
            serializedSize = ((Integer) position.invoke(buffer)).intValue();
            require(serializedSize == expectedSize, "native_buffer_size_mismatch");
            stage = "describe.rewind";
            bufferRewind.invoke(buffer);
            stage = "describe.read_constructor";
            int constructor = ((Integer) bufferReadInt32.invoke(buffer, Boolean.TRUE)).intValue();
            stage = "describe.deserialize_method";
            Method deserialize = documentClass.getMethod(
                    "TLdeserialize", inputSerializedDataClass, int.class, boolean.class);
            stage = "describe.deserialize";
            decoded = deserialize.invoke(null, buffer, Integer.valueOf(constructor), Boolean.TRUE);
            require(decoded != null, "native_deserialize_null");
            stage = "describe.remaining_method";
            Method remaining = buffer.getClass().getMethod("remaining");
            stage = "describe.remaining";
            require(
                    ((Integer) remaining.invoke(buffer)).intValue() == 0,
                    "native_bytes_remaining");
        } finally {
            String priorStage = stage;
            stage = "describe.buffer_reuse";
            bufferReuse.invoke(buffer);
            stage = priorStage;
        }

        stage = "describe.document_attribute_class";
        Class<?> documentAttributeClass = Class.forName("org.telegram.tgnet.TLRPC$DocumentAttribute");
        List<?> attributes = (List<?>) field(decoded, "attributes");
        JSONArray describedAttributes = new JSONArray();
        for (Object attribute : attributes) {
            JSONObject description = new JSONObject()
                    .put("kind", attribute.getClass().getSimpleName());
            if ("TL_documentAttributeFilename".equals(attribute.getClass().getSimpleName())) {
                stage = "describe.filename_field";
                Field fileName = documentAttributeClass.getField("file_name");
                stage = "describe.filename";
                description.put("file_name", fileName.get(attribute));
            }
            describedAttributes.put(description);
        }

        byte[] fileReference = (byte[]) field(decoded, "file_reference");
        List<?> thumbs = (List<?>) field(decoded, "thumbs");
        List<?> videoThumbs = (List<?>) field(decoded, "video_thumbs");
        stage = "describe.image_location_class";
        Class<?> imageLocationClass = Class.forName("org.telegram.messenger.ImageLocation");
        stage = "describe.get_for_document_method";
        Method getForDocument = imageLocationClass.getMethod("getForDocument", documentClass);
        stage = "describe.get_for_document";
        Object location = getForDocument.invoke(null, decoded);
        stage = "describe.get_key_method";
        Method getKey = imageLocationClass.getMethod(
                "getKey", Object.class, Object.class, boolean.class);
        stage = "describe.get_key";
        String key = (String) getKey.invoke(location, decoded, null, Boolean.FALSE);
        stage = "describe.file_loader_class";
        Class<?> fileLoaderClass = Class.forName("org.telegram.messenger.FileLoader");
        stage = "describe.get_attach_file_name_method";
        Method getAttachFileName = fileLoaderClass.getMethod("getAttachFileName", tlObjectClass);
        stage = "describe.get_attach_file_name";
        String attachFileName = (String) getAttachFileName.invoke(null, decoded);

        stage = "describe.result";
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
        stage = "describe.field_method." + name;
        Field reflected = documentClass.getField(name);
        stage = "describe.field." + name;
        return reflected.get(value);
    }

    private static String bounded(String value) {
        if (value == null) {
            return "";
        }
        return value.length() <= DIAGNOSTIC_TEXT_LIMIT
                ? value : value.substring(0, DIAGNOSTIC_TEXT_LIMIT);
    }

    private static boolean relevant(StackTraceElement frame) {
        String className = frame.getClassName();
        return className.startsWith("org.telegram.gramlab.")
                || className.startsWith("org.telegram.tgnet.")
                || className.startsWith("org.telegram.messenger.");
    }

    private static String frame(StackTraceElement value) {
        return bounded(value.getClassName() + "#" + value.getMethodName() + ":" + value.getLineNumber());
    }

    private static JSONObject failureRecord(String name, Throwable failure) throws Exception {
        JSONObject record = new JSONObject()
                .put("name", name)
                .put("passed", false)
                .put("failure_class", failure.getClass().getSimpleName())
                .put("stage", bounded(stage));
        if (failure instanceof AssertionError) {
            record.put("assertion", bounded(failure.getMessage()));
        }

        JSONArray causeChain = new JSONArray();
        Throwable actual = failure;
        for (int depth = 0; depth < CAUSE_LIMIT && actual != null; depth++) {
            causeChain.put(new JSONObject()
                    .put("class", bounded(actual.getClass().getName()))
                    .put("message", bounded(actual.getMessage())));
            Throwable next = actual.getCause();
            if (next == null || next == actual) {
                break;
            }
            actual = next;
        }
        record.put("cause_chain", causeChain)
                .put("actual_cause_class", bounded(actual.getClass().getName()))
                .put("actual_cause_message", bounded(actual.getMessage()));

        JSONArray frames = new JSONArray();
        for (StackTraceElement value : actual.getStackTrace()) {
            if (relevant(value)) {
                frames.put(frame(value));
                if (frames.length() == STACK_FRAME_LIMIT) {
                    break;
                }
            }
        }
        if (frames.length() == 0) {
            StackTraceElement[] values = actual.getStackTrace();
            for (int index = 0; index < values.length && index < STACK_FRAME_LIMIT; index++) {
                frames.put(frame(values[index]));
            }
        }
        return record.put("relevant_frames", frames);
    }

    private static void emit(File output, JSONObject summary) throws Exception {
        writeRecord(new File(output, "summary.json"), summary);
        System.out.println(summary);
    }

    private static void run(String name, Case test) throws Exception {
        JSONObject record = new JSONObject().put("name", name);
        stage = "case." + name;
        try {
            test.run();
            record.put("passed", true);
            passed++;
        } catch (Exception | AssertionError failure) {
            record = failureRecord(name, failure);
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
        Class<?> codec;
        Class<?> entry;
        try {
            stage = "bootstrap.document_codec_class";
            codec = Class.forName("org.telegram.gramlab.GramLabDocument");
            stage = "bootstrap.document_entry_class";
            entry = Class.forName("org.telegram.gramlab.GramLabDocument$Entry");
            stage = "bootstrap.identifier_method";
            identifier = codec.getMethod("identifier", Object.class);
            stage = "bootstrap.parse_method";
            parse = codec.getMethod("parse", JSONArray.class);
            stage = "bootstrap.project_method";
            project = codec.getMethod("project", entry);
            stage = "bootstrap.custom_emoji_class";
            customEmojiIdentifier = Class.forName("org.telegram.gramlab.GramLabCustomEmoji")
                    .getMethod("identifier", Object.class);
            stage = "bootstrap.document_class";
            documentClass = Class.forName("org.telegram.tgnet.TLRPC$Document");
            stage = "bootstrap.input_serialized_data_class";
            inputSerializedDataClass = Class.forName("org.telegram.tgnet.InputSerializedData");
            stage = "bootstrap.output_serialized_data_class";
            outputSerializedDataClass = Class.forName("org.telegram.tgnet.OutputSerializedData");
        } catch (ClassNotFoundException failure) {
            JSONObject bootstrapFailure = failureRecord("bootstrap_document_codec", failure);
            emit(output, new JSONObject()
                    .put("schema", 1)
                    .put("passed", 0)
                    .put("failed", 1)
                    .put("total", 1)
                    .put("custom_emoji_ids", new JSONArray())
                    .put("documents", new JSONArray())
                    .put("cases", new JSONArray().put(bootstrapFailure)));
            System.exit(1);
            return;
        }
        stage = "bootstrap.native_library";
        System.load(new File(arguments[1]).getAbsolutePath());
        stage = "bootstrap.native_buffer_class";
        Class<?> nativeBuffer = Class.forName("org.telegram.tgnet.NativeByteBuffer");
        stage = "bootstrap.native_buffer_constructor";
        nativeBufferConstructor = nativeBuffer.getConstructor(int.class);
        stage = "bootstrap.read_int32_method";
        bufferReadInt32 = nativeBuffer.getMethod("readInt32", boolean.class);
        stage = "bootstrap.rewind_method";
        bufferRewind = nativeBuffer.getMethod("rewind");
        stage = "bootstrap.reuse_method";
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
            long[] expectedIds = {1L, 2L, 10L, 2_147_483_648L, Long.MAX_VALUE};
            long[] expectedSizes = {1L, 50_000_000L, 2L, 123L, 50_000_000L};
            String[] expectedFileNames = {
                    "گزارش🙂.pdf",
                    "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx🙂",
                    "archive.tar",
                    "sentinel.bin",
                    "maximum"
            };
            String[] expectedMimeTypes = {
                    "application/pdf", "", "application/x-tar", "application/octet-stream", ""
            };
            String[] expectedDigests = {
                    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                    "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
                    "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
                    "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
            };
            List<String> order = new ArrayList<>();
            int entryIndex = 0;
            for (Map.Entry<?, ?> item : entries.entrySet()) {
                Object parsedEntry = item.getValue();
                require(((Long) entry.getField("id").get(parsedEntry)).longValue()
                        == expectedIds[entryIndex], "wrong_entry_id_" + entryIndex);
                require(((Long) entry.getField("size").get(parsedEntry)).longValue()
                        == expectedSizes[entryIndex], "wrong_entry_size_" + entryIndex);
                require(expectedFileNames[entryIndex].equals(entry.getField("fileName").get(parsedEntry)),
                        "wrong_entry_file_name_" + entryIndex);
                require(expectedMimeTypes[entryIndex].equals(entry.getField("mimeType").get(parsedEntry)),
                        "wrong_entry_mime_type_" + entryIndex);
                require(expectedDigests[entryIndex].equals(entry.getField("sha256").get(parsedEntry)),
                        "wrong_entry_sha256_" + entryIndex);
                require(((Long) item.getKey()).longValue() == expectedIds[entryIndex],
                        "wrong_entry_key_" + entryIndex);
                order.add(item.getKey().toString());
                stage = "project." + entryIndex;
                Object document = project.invoke(null, parsedEntry);
                documents.put(describe(document));
                entryIndex++;
            }
            require(entryIndex == expectedIds.length, "wrong_asserted_entry_count");
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
        emit(output, summary);
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
