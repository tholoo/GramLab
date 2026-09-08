// SPDX-License-Identifier: GPL-2.0-or-later
package org.telegram.gramlab;

import java.io.File;
import java.io.FileOutputStream;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Map;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONObject;

/** Actual GramLabButtonObserver.reload lifetime-scoping regression. */
public final class ButtonDisarmProbe {
    private static final String CURRENT_ACTIVATION = "activation-current";
    private static final String OLD_ACTIVATION = "activation-old";
    private static final String OLD_CLIENT = "client-old";
    private static final String LIVE_OPERATION = "operation-live";
    private static final String OTHER_OPERATION = "operation-other";

    private static Method reload;
    private static Field directoryField;
    private static Field activationField;
    private static Field armField;
    private static Field disarmedOperationField;
    private static Field invalidatedOperationsField;
    private static Field consumedOperationsField;
    private static Field publishedGroupsField;
    private static String currentClient;
    private static File output;
    private static final JSONArray cases = new JSONArray();
    private static int passed;
    private static int failed;

    private ButtonDisarmProbe() {}

    private interface Case {
        void run(File directory) throws Exception;
    }

    private static void require(boolean value, String code) {
        if (!value) throw new AssertionError(code);
    }

    private static Field field(Class<?> owner, String name) throws Exception {
        Field result = owner.getDeclaredField(name);
        result.setAccessible(true);
        return result;
    }

    private static Set<?> set(Field field) throws Exception {
        Object value = field.get(null);
        require(value instanceof Set, field.getName() + "_not_set");
        return (Set<?>) value;
    }

    private static JSONObject arm(String operation) throws Exception {
        return new JSONObject().put("operation_id", operation);
    }

    private static JSONObject activation() throws Exception {
        return new JSONObject()
                .put("schema", 1)
                .put("nonce", CURRENT_ACTIVATION)
                .put("world_id", "world-current")
                .put("user_id", 1)
                .put("chat_id", 1)
                .put("message_id", 2)
                .put("revision", 3);
    }

    private static JSONObject armCandidate() throws Exception {
        return activation()
                .put("client_nonce", currentClient)
                .put("operation_id", LIVE_OPERATION)
                .put("path", new JSONArray().put("blocks").put(0))
                .put("observation_generation", 1);
    }

    private static JSONObject disarm(String nonce, String client, String operation) throws Exception {
        return new JSONObject()
                .put("schema", 1)
                .put("nonce", nonce)
                .put("client_nonce", client)
                .put("operation_id", operation);
    }

    private static void reset(File directory) throws Exception {
        require(directory.mkdir(), "private_directory");
        directoryField.set(null, directory);
        activationField.set(null, activation());
        armField.set(null, arm(LIVE_OPERATION));
        disarmedOperationField.set(null, null);
        set(invalidatedOperationsField).clear();
        set(consumedOperationsField).clear();
        Object groups = publishedGroupsField.get(null);
        require(groups instanceof Map, "published_groups_not_map");
        ((Map<?, ?>) groups).clear();
        Map.class.getMethod("put", Object.class, Object.class)
                .invoke(groups, Long.valueOf(1), new ArrayList<Object>());
    }

    private static void write(File directory, String name, String value) throws Exception {
        Files.write(
                new File(directory, name).toPath(),
                value.getBytes(StandardCharsets.UTF_8));
    }

    private static void invokeReload() throws Exception {
        reload.invoke(null);
    }

    private static void assertUnchanged(JSONObject expected) throws Exception {
        require(armField.get(null) == expected, "arm_changed");
        require(disarmedOperationField.get(null) == null, "disarmed_operation_changed");
        require(set(invalidatedOperationsField).isEmpty(), "operation_invalidated");
        require(set(consumedOperationsField).isEmpty(), "operation_consumed");
    }

    private static void expectInvalid(JSONObject expected) throws Exception {
        try {
            reload.invoke(null);
            throw new AssertionError("malformed_control_accepted");
        } catch (InvocationTargetException failure) {
            Throwable cause = failure.getCause();
            require(cause instanceof IllegalArgumentException, "wrong_rejection_class");
            require(
                    "invalid_rich_button_observation".equals(cause.getMessage()),
                    "wrong_rejection_reason");
        }
        assertUnchanged(expected);
    }

    private static void malformed(File directory, String value) throws Exception {
        reset(directory);
        JSONObject expected = (JSONObject) armField.get(null);
        write(directory, "rich-button-disarm.json", value);
        expectInvalid(expected);
    }

    private static void run(String name, Case test) throws Exception {
        JSONObject record = new JSONObject().put("name", name);
        File directory = new File(output, name + "-private");
        try {
            test.run(directory);
            record.put("passed", true);
            passed++;
        } catch (Exception | AssertionError failure) {
            record.put("passed", false).put("failure_class", failure.getClass().getSimpleName());
            if (failure instanceof AssertionError) record.put("assertion", failure.getMessage());
            failed++;
        }
        cases.put(record);
        writeRecord(new File(output, name + ".json"), record);
    }

    public static void main(String[] arguments) throws Exception {
        if (arguments.length != 1) throw new IllegalArgumentException("OUTPUT_DIRECTORY");
        output = new File(arguments[0]);
        if (output.exists() || !output.mkdir()) throw new IllegalArgumentException("fresh output required");

        Class<?> observer = Class.forName("org.telegram.gramlab.GramLabButtonObserver");
        reload = observer.getDeclaredMethod("reload");
        reload.setAccessible(true);
        directoryField = field(observer, "directory");
        activationField = field(observer, "activation");
        armField = field(observer, "arm");
        disarmedOperationField = field(observer, "disarmedOperation");
        invalidatedOperationsField = field(observer, "invalidatedOperations");
        consumedOperationsField = field(observer, "consumedOperations");
        publishedGroupsField = field(observer, "publishedGroups");
        currentClient = (String) field(observer, "clientNonce").get(null);

        run("stale_activation", directory -> {
            reset(directory);
            JSONObject expected = (JSONObject) armField.get(null);
            write(
                    directory,
                    "rich-button-disarm.json",
                    disarm(OLD_ACTIVATION, currentClient, LIVE_OPERATION).toString());
            invokeReload();
            assertUnchanged(expected);
        });
        run("stale_client", directory -> {
            reset(directory);
            JSONObject expected = (JSONObject) armField.get(null);
            write(
                    directory,
                    "rich-button-disarm.json",
                    disarm(CURRENT_ACTIVATION, OLD_CLIENT, LIVE_OPERATION).toString());
            invokeReload();
            assertUnchanged(expected);
        });
        run("matching_current_operation", directory -> {
            reset(directory);
            write(
                    directory,
                    "rich-button-disarm.json",
                    disarm(CURRENT_ACTIVATION, currentClient, LIVE_OPERATION).toString());
            invokeReload();
            require(armField.get(null) == null, "matching_arm_retained");
            require(LIVE_OPERATION.equals(disarmedOperationField.get(null)), "wrong_disarmed_operation");
            require(set(invalidatedOperationsField).size() == 1, "wrong_invalidated_count");
            require(set(invalidatedOperationsField).contains(LIVE_OPERATION), "operation_not_invalidated");
            require(set(consumedOperationsField).isEmpty(), "operation_consumed");
            write(directory, "rich-button-arm.json", armCandidate().toString());
            invokeReload();
            require(armField.get(null) == null, "invalidated_operation_rearmed");
            require(set(invalidatedOperationsField).size() == 1, "invalidated_operation_lost");
            require(set(invalidatedOperationsField).contains(LIVE_OPERATION), "rearm_guard_lost");
        });
        run("different_current_operation", directory -> {
            reset(directory);
            JSONObject expected = (JSONObject) armField.get(null);
            write(
                    directory,
                    "rich-button-disarm.json",
                    disarm(CURRENT_ACTIVATION, currentClient, OTHER_OPERATION).toString());
            invokeReload();
            assertUnchanged(expected);
        });
        run("malformed_json", directory -> malformed(directory, "{"));
        run("extra_field", directory -> malformed(
                directory,
                disarm(CURRENT_ACTIVATION, currentClient, LIVE_OPERATION).put("extra", 1).toString()));
        run("invalid_schema", directory -> malformed(
                directory,
                disarm(CURRENT_ACTIVATION, currentClient, LIVE_OPERATION).put("schema", 0).toString()));
        run("invalid_activation_token", directory -> malformed(
                directory, disarm("", currentClient, LIVE_OPERATION).toString()));
        run("invalid_client_token", directory -> malformed(
                directory, disarm(CURRENT_ACTIVATION, "", LIVE_OPERATION).toString()));
        run("invalid_operation_token", directory -> malformed(
                directory, disarm(CURRENT_ACTIVATION, currentClient, "").toString()));

        JSONObject summary = new JSONObject()
                .put("schema", 1)
                .put("passed", passed)
                .put("failed", failed)
                .put("total", passed + failed)
                .put("cases", cases);
        writeRecord(new File(output, "summary.json"), summary);
        System.out.println(summary);
        System.exit(failed == 0 ? 0 : 1);
    }

    private static void writeRecord(File path, JSONObject value) throws Exception {
        byte[] encoded = value.toString(2).getBytes(StandardCharsets.UTF_8);
        require(encoded.length <= 65536, "output_too_large");
        try (FileOutputStream stream = new FileOutputStream(path)) {
            stream.write(encoded);
        }
    }
}
