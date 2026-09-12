// SPDX-License-Identifier: GPL-2.0-or-later
package org.telegram.gramlab;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.util.SparseArray;
import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import org.json.JSONArray;
import org.json.JSONObject;
import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.ApplicationLoader;
import org.telegram.messenger.FileLoadOperation;
import org.telegram.messenger.FileLoader;
import org.telegram.messenger.FilePathDatabase;
import org.telegram.messenger.FileUploadOperation;
import org.telegram.messenger.ImageLoader;
import org.telegram.messenger.ImageLocation;
import org.telegram.messenger.MessageObject;
import org.telegram.messenger.NativeLoader;
import org.telegram.messenger.UserConfig;
import org.telegram.messenger.FileLoadOperationStream;
import org.telegram.tgnet.ConnectionsManager;
import org.telegram.tgnet.NativeByteBuffer;
import org.telegram.tgnet.TLRPC;
import org.telegram.tgnet.tl.TL_keyboard;

/** Actual bridge/FileLoader/SQLite probe. The only substituted collaborator is the HTTP peer. */
public final class DocumentDeliveryProbe {
    private static final byte[] PAYLOAD = "ordinary document\n".getBytes(StandardCharsets.UTF_8);
    private static final String CAPABILITY = "gramlab-client_ddddddddddddddddddddddddddddddddddddddddddd";
    private static final JSONArray cases = new JSONArray();
    private static final JSONArray observations = new JSONArray();
    private static File directory;
    private static Peer peer;
    private static JSONObject config;
    private static JSONArray descriptors;
    private static FileLoader loader;
    private static Listener listener;
    private static int sequence;
    private static volatile String phase = "initialization";

    private DocumentDeliveryProbe() {}
    private interface Check { void run() throws Exception; }
    private static void require(boolean value, String code) {
        if (!value) throw new AssertionError(code);
    }
    private static String hash(byte[] bytes) throws Exception {
        return GramLabMedia.hex(MessageDigest.getInstance("SHA-256").digest(bytes));
    }
    private static String fileHash(File file) throws Exception {
        MessageDigest digest=MessageDigest.getInstance("SHA-256");
        try(java.io.InputStream input=Files.newInputStream(file.toPath())) {
            byte[] buffer=new byte[8192];for(int count;(count=input.read(buffer))!=-1;)digest.update(buffer,0,count);
        }
        return GramLabMedia.hex(digest.digest());
    }
    private static JSONObject copy(JSONObject value) throws Exception { return new JSONObject(value.toString()); }
    private static JSONArray array(Object... values) {
        JSONArray result = new JSONArray(); for (Object value : values) result.put(value); return result;
    }
    private static void rejected(Check check) throws Exception {
        try { check.run(); }
        catch (IllegalArgumentException expected) { return; }
        catch (InvocationTargetException expected) {
            if (expected.getCause() instanceof IllegalArgumentException) return;
            throw expected;
        }
        throw new AssertionError("invalid_input_accepted");
    }
    static volatile String diagnosticStep="bootstrap";
    private static File diagnosticDirectory;
    private static String diagnosticPrefix;
    private static long diagnosticStarted;
    private static final java.util.concurrent.atomic.AtomicInteger diagnosticEvents=new java.util.concurrent.atomic.AtomicInteger();
    private static final CountDownLatch diagnosticDone=new CountDownLatch(1);
    private static volatile String diagnosticWriteError="";
    private static Thread diagnosticWatchdog;
    private static long diagnosticOperationThread;
    private static volatile int diagnosticCompleted;
    private static volatile int diagnosticFailed;

    private static JSONObject diagnosticPosition(String event) throws Exception {
        return new JSONObject().put("schema",1).put("event",event).put("phase",phase).put("stage",diagnosticStep)
                .put("elapsed_ms",android.os.SystemClock.elapsedRealtime()-diagnosticStarted)
                .put("pid",android.os.Process.myPid()).put("completed",diagnosticCompleted).put("failed",diagnosticFailed)
                .put("write_error",diagnosticWriteError);
    }
    private static void diagnosticWrite(String name,JSONObject value) {
        try {
            if(diagnosticDirectory==null)return;
            byte[] bytes=value.toString().replace(CAPABILITY,"[REDACTED]").getBytes(StandardCharsets.UTF_8);
            if(bytes.length>128*1024)throw new java.io.IOException("diagnostic_record_bound");
            Files.write(new File(diagnosticDirectory,diagnosticPrefix+"-"+name+".json").toPath(),bytes,
                    java.nio.file.StandardOpenOption.CREATE_NEW);
        } catch(Exception error) {diagnosticWriteError=error.getClass().getName();}
    }
    static void diagnosticCheckpoint(String event,JSONObject detail) {
        int position=diagnosticEvents.incrementAndGet();if(position>96)return;
        try {JSONObject record=diagnosticPosition(event);if(detail!=null)record.put("detail",detail);
            diagnosticWrite(String.format(java.util.Locale.ROOT,"event-%03d",position),record);
        } catch(Exception error) {diagnosticWriteError=error.getClass().getName();}
    }
    static void startDiagnostics(Context context,String mode) {
        diagnosticStarted=android.os.SystemClock.elapsedRealtime();diagnosticOperationThread=Thread.currentThread().getId();
        diagnosticPrefix=(java.util.Arrays.asList("suite","restart","filesystem","rename").contains(mode)?mode:"invalid")+"-"+android.os.Process.myPid();
        try {
            diagnosticDirectory=new File(context.getFilesDir(),"document-delivery-diagnostics");
            if(!diagnosticDirectory.mkdir()&&!diagnosticDirectory.isDirectory())throw new java.io.IOException("diagnostic_directory");
        } catch(Exception error) {diagnosticWriteError=error.getClass().getName();}
        diagnosticCheckpoint("instrumentation_start",null);
        diagnosticWatchdog=new Thread(()->{
            try {
                for(int sample=1;sample<=8;sample++) {
                    if(diagnosticDone.await(30,TimeUnit.SECONDS))return;
                    JSONObject record=diagnosticPosition("watchdog");
                    java.util.Map<Thread,StackTraceElement[]> traces=Thread.getAllStackTraces();
                    java.util.ArrayList<Thread> ordered=new java.util.ArrayList<>(traces.keySet());
                    ordered.sort(java.util.Comparator.comparingInt((Thread thread)->thread.getId()==diagnosticOperationThread?0:
                            thread.getName().equals("main")?1:thread.getName().toLowerCase(java.util.Locale.ROOT).contains("queue")?2:3)
                            .thenComparingLong(Thread::getId));
                    JSONArray threads=new JSONArray();record.put("thread_count",ordered.size()).put("threads_omitted",Math.max(0,ordered.size()-48));
                    for(int index=0;index<Math.min(48,ordered.size());index++) {
                        Thread thread=ordered.get(index);StackTraceElement[] trace=traces.get(thread);JSONArray frames=new JSONArray();
                        for(int frame=0;frame<Math.min(8,trace.length);frame++) {
                            String value=diagnosticText(trace[frame].toString());frames.put(value.substring(0,Math.min(256,value.length())));
                        }
                        String name=diagnosticText(thread.getName());
                        threads.put(new JSONObject().put("id",thread.getId()).put("name",name.substring(0,Math.min(96,name.length())))
                                .put("state",thread.getState().name()).put("frames",frames).put("frames_omitted",Math.max(0,trace.length-8)));
                    }
                    record.put("threads",threads);diagnosticWrite("watchdog-"+sample,record);
                }
            } catch(InterruptedException error){Thread.currentThread().interrupt();}
            catch(Throwable error){try{diagnosticWrite("watchdog-error",diagnosticFailure(error,"watchdog"));}catch(Exception ignored){}}
        },"document-delivery-watchdog");
        diagnosticWatchdog.setDaemon(true);diagnosticWatchdog.start();
    }
    static void stopDiagnostics() {
        diagnosticDone.countDown();
        if(diagnosticWatchdog!=null)try{diagnosticWatchdog.join(1000);}catch(InterruptedException error){Thread.currentThread().interrupt();}
    }
    private static String diagnosticText(String value) {
        if(value==null)return "";
        value=value.replace(CAPABILITY,"[REDACTED]");
        return value.substring(0,Math.min(512,value.length()));
    }
    private static Throwable diagnosticCause(Throwable actual) {
        if(actual instanceof ExceptionInInitializerError) {
            Throwable exception=((ExceptionInInitializerError)actual).getException();
            if(exception!=null)return exception;
        }
        return actual.getCause();
    }
    private static JSONObject diagnosticThrowable(Throwable actual,int depth,IdentityHashMap<Throwable,Boolean> seen) throws Exception {
        seen.put(actual,Boolean.TRUE);
        JSONObject result=new JSONObject().put("exception",actual.getClass().getName())
                .put("message",diagnosticText(actual.getMessage()));
        JSONArray frames=new JSONArray();StackTraceElement[] trace=actual.getStackTrace();
        for(int i=0;i<Math.min(4,trace.length);i++)frames.put(diagnosticText(trace[i].toString()));
        result.put("frames",frames);
        Throwable cause=diagnosticCause(actual);
        if(cause!=null) {
            if(seen.containsKey(cause))result.put("cause_cycle",true);
            else if(depth < 3)result.put("cause",diagnosticThrowable(cause,depth+1,seen));
            else result.put("causes_omitted",true);
        }
        return result;
    }
    private static JSONObject diagnosticThrowable(Throwable actual) throws Exception {
        return diagnosticThrowable(actual,0,new IdentityHashMap<>());
    }
    private static void run(String name, Check check) throws Exception {
        phase = name;diagnosticStep="case_start";diagnosticCheckpoint("case_start",null);
        JSONObject result = new JSONObject().put("name", name);
        try { check.run(); result.put("status", "passed"); }
        catch (Throwable failure) {
            Throwable actual = failure instanceof InvocationTargetException && failure.getCause() != null
                    ? ((InvocationTargetException)failure).getTargetException() : failure;
            result=diagnosticThrowable(actual).put("name",name).put("status","failed").put("stage",diagnosticStep);
            // Assertion messages are authored static codes, never arbitrary transport errors.
            if (actual instanceof AssertionError) result.put("assertion", String.valueOf(actual.getMessage()));
        }
        cases.put(result);diagnosticCompleted++;if(!result.getString("status").equals("passed"))diagnosticFailed++;
        diagnosticCheckpoint("case_complete",result);
        Files.write(new File(directory, "cases-" + (phase.equals("cold_process_saved_destinations") ? "restart" : "suite") + ".json").toPath(), cases.toString(2).getBytes(StandardCharsets.UTF_8));
    }
    private static JSONObject descriptor(String id, String filename, String mime, byte[] bytes) throws Exception {
        return new JSONObject().put("document_id", id).put("file_name", filename).put("mime_type", mime)
                .put("file_size", bytes.length).put("sha256", hash(bytes));
    }
    private static JSONObject record(int id, String document) throws Exception {
        return new JSONObject().put("id", id).put("chat_id", 3).put("sender_id", 2).put("date", 100)
                .put("text", "").put("document", new JSONObject().put("document_id", document));
    }
    private static JSONArray users() throws Exception {
        return array(new JSONObject().put("id", 1).put("is_bot", false).put("first_name", "Reader"),
                new JSONObject().put("id", 2).put("is_bot", true).put("first_name", "Files"));
    }
    private static JSONObject envelope(int version) throws Exception {
        return new JSONObject().put("schema", version).put("world_id", config.getString("world_id")).put("user_id", 1);
    }
    private static JSONObject snapshot(int version, JSONArray documents, JSONArray messages) throws Exception {
        JSONObject result = envelope(version).put("cursor", messages.length()).put("now", 100)
                .put("users", users()).put("chats", array(new JSONObject().put("id", 3).put("type", "private")
                        .put("user_id", 1).put("bot_id", 2)))
                .put("messages", messages).put("message_position", messages.length()).put("sends", array())
                .put("assets", array()).put("custom_emoji", array());
        JSONArray revisions = array();
        for (int i = 0; i < messages.length(); i++) revisions.put(new JSONObject().put("chat_id", 3)
                .put("message_id", messages.getJSONObject(i).getInt("id")).put("revision", 1));
        result.put("message_revisions", revisions);
        if (version == 5) result.put("documents", documents);
        return result;
    }
    private static GramLabBridge.Snapshot connect(JSONObject body) throws Exception {
        peer.json("/v" + config.getInt("bridge_version") + "/snapshot", body);
        return GramLabBridge.connect(config);
    }
    private static AutoCloseable scope(JSONObject configuration, JSONArray documents) throws Exception {
        return (AutoCloseable) GramLabMedia.class.getMethod("scope", JSONObject.class, JSONArray.class,
                JSONArray.class, JSONArray.class).invoke(null, configuration, array(), array(), documents);
    }
    private static TLRPC.Document required(String id) throws Exception {
        return (TLRPC.Document) GramLabMedia.class.getMethod("requireDocument", Object.class).invoke(null, id);
    }
    private static TLRPC.Document project(JSONObject row) throws Exception {
        return GramLabDocument.project(GramLabDocument.parse(array(row)).values().iterator().next());
    }
    private static Object binding(TLRPC.Document document) throws Exception {
        return GramLabMedia.class.getMethod("transferDocument", TLRPC.Document.class).invoke(null, document);
    }
    private static void install(JSONArray documents) throws Exception {
        try (AutoCloseable value = scope(config, documents)) {
            value.getClass().getMethod("commit").invoke(value);
        }
    }
    private static void fresh() throws Exception {
        sequence++;
        config = new JSONObject().put("endpoint", "http://127.0.0.1:" + peer.port()).put("capability", CAPABILITY)
                .put("world_id", "delivery-probe-" + sequence).put("user_id", 1).put("bridge_version", 5);
        descriptors = array(descriptor("1", "گزارش.pdf", "application/pdf", PAYLOAD),
                descriptor("2147483648", "sentinel.bin", "", PAYLOAD),
                descriptor("9223372036854775807", "maximum.bin", "", PAYLOAD));
    }
    private static Map<String, Object> registry() throws Exception {
        Map<String,Object> result=new LinkedHashMap<>();
        for(String name:Arrays.asList("assets","documents","ordinaryDocuments")) {
            Field field=GramLabMedia.class.getDeclaredField(name);field.setAccessible(true);
            result.put(name,new LinkedHashMap<>((Map<?,?>)field.get(null)));
        }
        result.put("configuration",GramLabMedia.configuration().toString());return result;
    }
    private static JSONObject image(long id, byte[] bytes) throws Exception {
        return new JSONObject().put("asset_id",id).put("mime_type","image/webp").put("file_size",bytes.length)
                .put("sha256",hash(bytes)).put("width",100).put("height",100);
    }
    private static JSONObject emoji() throws Exception {
        return new JSONObject().put("custom_emoji_id","7").put("main_asset_id",5).put("thumbnail_asset_id",5)
                .put("fallback","🙂").put("free",true).put("needs_repainting",false).put("duration_ms",0);
    }
    private static void bridgeCases() throws Exception {
        run("v5_snapshot_document_caption_keyboard", () -> {
            fresh();
            JSONObject message = record(1, "1").put("caption", "Hello 🙂")
                    .put("caption_entities", array(new JSONObject().put("type", "bold").put("offset", 0).put("length", 5)))
                    .put("reply_markup", new JSONObject().put("inline_keyboard", array(array(
                            new JSONObject().put("text", "Confirm").put("callback_data", "document:confirm")))));
            GramLabBridge.Snapshot state = connect(snapshot(5, descriptors, array(message)));
            TLRPC.Message decoded = state.histories.get(2L).messages.get(0);
            require(decoded.media instanceof TLRPC.TL_messageMediaDocument && decoded.media.flags == 1,
                    "original_document_carrier");
            require(decoded.media.document.id == -1 && decoded.media.document.dc_id == -1, "reserved_identity");
            require(decoded.message.equals("Hello 🙂") && decoded.entities.size() == 1
                    && decoded.entities.get(0) instanceof TLRPC.TL_messageEntityBold
                    && decoded.entities.get(0).offset == 0 && decoded.entities.get(0).length == 5, "caption_entities");
            require(((TLRPC.TL_replyInlineMarkup)decoded.reply_markup).rows.size() == 1 && ((TLRPC.TL_replyInlineMarkup)decoded.reply_markup).rows.get(0).buttons.size() == 1
                    && ((TLRPC.TL_replyInlineMarkup)decoded.reply_markup).rows.get(0).buttons.get(0).text.equals("Confirm")
                    && Arrays.equals(((TL_keyboard.TL_inlineButtonTypeCallback)((TLRPC.TL_replyInlineMarkup)decoded.reply_markup).rows.get(0).buttons.get(0).type).data,
                            "document:confirm".getBytes(StandardCharsets.UTF_8)), "keyboard");
            NativeByteBuffer buffer = new NativeByteBuffer(decoded.getObjectSize());
            decoded.serializeToStream(buffer); buffer.position(0);
            TLRPC.Message restored = TLRPC.Message.TLdeserialize(buffer, buffer.readInt32(true), true); buffer.reuse();
            require(restored.media.document.id == -1 && restored.message.equals("Hello 🙂")
                    && restored.entities.size() == 1 && ((TLRPC.TL_replyInlineMarkup)restored.reply_markup).rows.size() == 1, "native_roundtrip");
            observations.put(new JSONObject().put("case", phase).put("document_id", "-1").put("dc_id", -1)
                    .put("caption", decoded.message).put("entity", "bold:0:5").put("callback", "document:confirm"));
        });
        run("v5_mixed_emoji_and_lookup", () -> {
            fresh(); byte[] bytes=Files.readAllBytes(new File(directory.getParentFile(),"delivery-emoji.webp").toPath());
            JSONObject message=record(1,"1").put("caption","🙂").put("caption_entities",array(
                    new JSONObject().put("type","custom_emoji").put("offset",0).put("length",2).put("custom_emoji_id","7")));
            JSONObject body=snapshot(5,descriptors,array(message)).put("assets",array(image(5,bytes))).put("custom_emoji",array(emoji()));
            GramLabBridge.Snapshot state=connect(body);
            TLRPC.Message decoded=state.histories.get(2L).messages.get(0);
            require(decoded.media.document.id==-1 && decoded.entities.get(0) instanceof TLRPC.TL_messageEntityCustomEmoji
                    && ((TLRPC.TL_messageEntityCustomEmoji)decoded.entities.get(0)).document_id==7,"mixed_caption_namespace");
            peer.json("/v5/custom-emoji-documents",envelope(5).put("assets",array(image(5,bytes))).put("custom_emoji",array(emoji())));
            org.telegram.tgnet.Vector<?> result=GramLabBridge.customEmojiDocuments(config,state,Arrays.asList(7L));
            require(result.objects.size()==1 && ((TLRPC.Document)result.objects.get(0)).id==7,"v5_emoji_lookup");
            int count=peer.count();JSONObject wrong=copy(config).put("bridge_version",3);
            rejected(() -> GramLabBridge.customEmojiDocuments(wrong,state,Arrays.asList(7L)));
            require(peer.count()==count,"wrong_version_emoji_network");
        });
        run("rejected_snapshot_preserves_all_registries", () -> {
            fresh(); GramLabBridge.Snapshot state=connect(snapshot(5,descriptors,array(record(1,"1"))));
            Map<String,Object> before=registry();
            JSONObject body=snapshot(5,array(descriptor("2","new.bin","",PAYLOAD)),array(record(1,"2")));
            body.getJSONArray("users").getJSONObject(1).put("first_name","Conflicting bot identity");
            peer.json("/v5/snapshot",body);
            rejected(() -> GramLabBridge.connect(config,state));
            require(registry().equals(before),"rejection_published_registry");
            require(state.dialogs.users.get(1).first_name.equals("Files"),"rejection_mutated_user");
        });
        run("full_63bit_bindings", () -> {
            fresh(); install(descriptors);
            for (int i = 0; i < descriptors.length(); i++) {
                TLRPC.Document document = project(descriptors.getJSONObject(i));
                require(binding(document) != null && document.id == -Long.parseLong(descriptors.getJSONObject(i).getString("document_id")), "full_identifier");
            }
        });
        run("missing_dependency_atomic", () -> {
            fresh(); install(descriptors); Object old = binding(project(descriptors.getJSONObject(0)));
            rejected(() -> connect(snapshot(5, array(), array(record(1, "2")))));
            require(binding(project(descriptors.getJSONObject(0))) != null && old != null, "old_binding_lost");
            require(binding(project(descriptor("2", "other.bin", "", PAYLOAD))) == null, "missing_binding_published");
        });
        run("mixed_carrier_atomic", () -> {
            fresh(); JSONObject row = descriptor("2", "other.bin", "", PAYLOAD);
            rejected(() -> connect(snapshot(5, array(row), array(record(1, "2").put("photo", new JSONObject().put("asset_id", 1))))));
            require(binding(project(row)) == null, "rejected_binding_published");
        });
        run("changed_metadata_atomic", () -> {
            fresh(); install(descriptors);
            JSONObject changed = copy(descriptors.getJSONObject(0)).put("file_name", "replacement.pdf");
            rejected(() -> install(array(changed)));
            require(binding(project(descriptors.getJSONObject(0))) != null && binding(project(changed)) == null, "immutable_metadata_changed");
        });
        run("exact_event_dependencies", () -> {
            fresh(); GramLabBridge.Snapshot state = connect(snapshot(5, descriptors, array(record(1, "1"))));
            JSONObject event = new JSONObject().put("position", 2).put("type", "message.created")
                    .put("revision", 1).put("data", record(2, "2147483648"));
            JSONObject body = envelope(5).put("cursor", 2).put("head", 2).put("now", 100).put("changes", array(event))
                    .put("users", users()).put("assets", array()).put("custom_emoji", array()).put("documents", descriptors);
            peer.json("/v5/changes?after=1&limit=100", body);
            rejected(() -> GramLabBridge.events(config, state, 1, 100));
            body.put("documents", array(descriptors.getJSONObject(1))); peer.json("/v5/changes?after=1&limit=100", body);
            GramLabBridge.EventBatch batch = GramLabBridge.events(config, state, 1, 100);
            require(batch.cursor == 2 && batch.head == 2 && batch.changes.size() == 1, "event_batch");
        });
        run("historical_callback_dependencies", () -> {
            fresh(); GramLabBridge.Snapshot state = connect(snapshot(5, descriptors, array(record(1, "1"))));
            JSONObject callback = new JSONObject().put("id", "frozen-callback").put("user_id", 1).put("chat_id", 3)
                    .put("message", record(1, "2147483648")).put("data", "document:confirm")
                    .put("chat_instance", "0000000000000000000000000000000000000000000000000000000000000000")
                    .put("answer", new JSONObject().put("text", "Frozen").put("show_alert", false).put("cache_time", 0));
            JSONObject body = envelope(5).put("callback", callback).put("message_revision", 1).put("users", users())
                    .put("assets", array()).put("custom_emoji", array()).put("documents", array(descriptors.getJSONObject(1)));
            JSONObject pending=copy(body);pending.getJSONObject("callback").put("answer",JSONObject.NULL);
            peer.json("/v5/callbacks", pending);peer.json("/v5/callbacks/frozen-callback",body);
            TLRPC.TL_messages_getBotCallbackAnswer query = new TLRPC.TL_messages_getBotCallbackAnswer();
            query.peer = new TLRPC.TL_inputPeerUser(); query.peer.user_id = 2; query.msg_id = 1; query.flags = 1;
            query.data = "document:confirm".getBytes(StandardCharsets.UTF_8);
            require(GramLabBridge.callback(config, state, query).message.equals("Frozen"), "callback_answer");
            body.put("documents", array(descriptors.getJSONObject(0))); peer.json("/v5/callbacks", body);
            rejected(() -> GramLabBridge.callback(config, state, query));
        });
        run("v4_unchanged_and_document_rejected", () -> {
            fresh(); config.put("bridge_version", 4);
            JSONObject text = record(1, "1"); text.remove("document"); text.put("text", "Version four");
            GramLabBridge.Snapshot state = connect(snapshot(4, array(), array(text)));
            require(state.histories.get(2L).messages.get(0).message.equals("Version four"), "legacy_text");
            rejected(() -> connect(snapshot(4, array(), array(record(1, "1")))));
        });
        run("v4_changes_callback_and_emoji", () -> {
            fresh();config.put("bridge_version",4);
            byte[] bytes=Files.readAllBytes(new File(directory.getParentFile(),"delivery-emoji.webp").toPath());
            JSONObject text=record(1,"1");text.remove("document");text.put("text","🙂").put("entities",array(
                    new JSONObject().put("type","custom_emoji").put("offset",0).put("length",2).put("custom_emoji_id","7")));
            GramLabBridge.Snapshot state=connect(snapshot(4,array(),array(text)).put("assets",array(image(5,bytes)))
                    .put("custom_emoji",array(emoji())));
            JSONObject event=new JSONObject().put("position",2).put("type","message.created").put("revision",1)
                    .put("data",copy(text).put("id",2));
            JSONObject changes=envelope(4).put("cursor",2).put("head",2).put("now",100).put("changes",array(event))
                    .put("users",users()).put("assets",array(image(5,bytes))).put("custom_emoji",array(emoji()));
            peer.json("/v4/changes?after=1&limit=100",changes);
            GramLabBridge.EventBatch batch=GramLabBridge.events(config,state,1,100);
            require(batch.changes.size()==1 && batch.cursor==2,"v4_event");
            JSONObject callback=new JSONObject().put("id","v4-frozen").put("user_id",1).put("chat_id",3)
                    .put("message",text).put("data","confirm").put("chat_instance",new String(new char[64]).replace('\0','0'))
                    .put("answer",new JSONObject().put("text","Four").put("show_alert",false).put("cache_time",0));
            JSONObject answer=envelope(4).put("callback",callback).put("message_revision",1).put("users",users())
                    .put("assets",array(image(5,bytes))).put("custom_emoji",array(emoji()));
            JSONObject pending=copy(answer);pending.getJSONObject("callback").put("answer",JSONObject.NULL);
            peer.json("/v4/callbacks",pending);peer.json("/v4/callbacks/v4-frozen",answer);
            TLRPC.TL_messages_getBotCallbackAnswer query=new TLRPC.TL_messages_getBotCallbackAnswer();
            query.peer=new TLRPC.TL_inputPeerUser();query.peer.user_id=2;query.msg_id=1;query.flags=1;
            query.data="confirm".getBytes(StandardCharsets.UTF_8);
            require(GramLabBridge.callback(config,state,query).message.equals("Four"),"v4_callback");
            peer.json("/v4/custom-emoji-documents",envelope(4).put("assets",array(image(5,bytes))).put("custom_emoji",array(emoji())));
            require(((TLRPC.Document)GramLabBridge.customEmojiDocuments(config,state,Arrays.asList(7L)).objects.get(0)).id==7,
                    "v4_emoji_lookup");
        });
        run("v5_send_and_rejected_dependencies", () -> {
            fresh();GramLabBridge.Snapshot state=connect(snapshot(5,descriptors,array(record(1,"1"))));
            JSONObject text=record(2,"1");text.remove("document");text.put("sender_id",1).put("text","Read");
            JSONObject send=new JSONObject().put("request_id","123").put("position",2).put("message",text);
            JSONObject response=envelope(5).put("send",send).put("message_revision",1).put("users",users())
                    .put("assets",array()).put("custom_emoji",array()).put("documents",array());
            TLRPC.TL_messages_sendMessage query=new TLRPC.TL_messages_sendMessage();
            query.peer=new TLRPC.TL_inputPeerUser();query.peer.user_id=2;query.random_id=123;query.message="Read";
            peer.json("/v5/messages",response);GramLabBridge.SendResult result=GramLabBridge.send(config,state,query);
            require(result.randomId()==123 && result.position==2 && result.message.id==2 && result.message.out
                    && result.message.message.equals("Read"),"v5_send");
            Map<String,Object> before=registry();response.put("documents",array(descriptor("4","extra.bin","",PAYLOAD)));
            peer.json("/v5/messages",response);rejected(() -> GramLabBridge.send(config,state,query));
            require(registry().equals(before),"send_rejection_published");
        });
        run("world_persona_invalidation", () -> {
            fresh(); install(descriptors); TLRPC.Document document = project(descriptors.getJSONObject(0));
            Object old = binding(document); require(old != null, "initial_binding");
            config.put("world_id", "other-world"); install(array());
            require(binding(document) == null && !(Boolean) old.getClass().getMethod("current").invoke(old), "world_authority_retained");
            install(descriptors); old = binding(document); config.put("user_id", 9); install(array());
            require(binding(document) == null && !(Boolean) old.getClass().getMethod("current").invoke(old), "persona_authority_retained");
        });
        run("stale_response_epoch", () -> {
            fresh();
            try (AutoCloseable value = scope(config, descriptors)) {
                JSONObject other = copy(config).put("world_id", "concurrent-world");
                Thread thread = new Thread(() -> { try { GramLabMedia.beginWorld(other, "concurrent-world"); }
                    catch (Exception failure) { throw new AssertionError(failure); } });
                thread.start(); thread.join(5000); require(!thread.isAlive(), "epoch_worker_timeout");
                try { value.getClass().getMethod("commit").invoke(value); throw new AssertionError("stale_scope_committed"); }
                catch (InvocationTargetException expected) { require(expected.getCause() instanceof IllegalStateException, "epoch_rejection"); }
            }
        });
        run("original_gif_classification", () -> {
            fresh(); JSONObject gif = descriptor("4", "original.gif", "image/gif", PAYLOAD);
            TLRPC.Document document = project(gif);
            require(MessageObject.isGifDocument(document), "original_gif_predicate");
            require(document.attributes.size() == 1 && document.attributes.get(0) instanceof TLRPC.TL_documentAttributeFilename,
                    "invented_gif_attribute");
            observations.put(new JSONObject().put("case", phase).put("mime_type", document.mime_type).put("is_gif", true)
                    .put("attributes", array("filename")));
        });
    }

    private static final class Result {
        final String name; final File file; final int reason; final int type;
        Result(String name, File file, int reason, int type) { this.name=name; this.file=file; this.reason=reason; this.type=type; }
    }
    private static final class Listener implements FileLoader.FileLoaderDelegate {
        final BlockingQueue<Result> terminal = new LinkedBlockingQueue<>();
        final Map<String, Long> progress = Collections.synchronizedMap(new LinkedHashMap<>());
        public void fileDidLoaded(String name, File file, Object parent, int type) { terminal.add(new Result(name,file,-1,type)); }
        public void fileDidFailedLoad(String name, int reason) { terminal.add(new Result(name,null,reason,-1)); }
        public void fileLoadProgressChanged(FileLoadOperation operation, String name, long loaded, long total) {
            require(loaded > 0 && loaded <= total && loaded >= progress.getOrDefault(name,0L), "progress_bounds");
            progress.put(name,loaded);
        }
        public void fileUploadProgressChanged(FileUploadOperation operation, String name, long size, long total, boolean encrypted) { throw new AssertionError("upload"); }
        public void fileDidUploaded(String name, TLRPC.InputFile file, TLRPC.InputEncryptedFile encrypted, byte[] key, byte[] iv, long size) { throw new AssertionError("upload"); }
        public void fileDidFailedUpload(String name, boolean encrypted) { throw new AssertionError("upload"); }
    }
    private static void loadSetup() throws Exception {
        fresh(); install(descriptors);
        File caseDirectory = new File(directory, "files-" + sequence); require(caseDirectory.mkdir(), "fresh_case_directory");
        SparseArray<File> dirs = new SparseArray<>();
        for (int kind = 0; kind <= 6; kind++) { File dir = new File(caseDirectory,Integer.toString(kind)); require(dir.mkdir(), "media_directory"); dirs.put(kind,dir); }
        FileLoader.setMediaDirs(dirs);
        if (loader == null) {
            loader = new FileLoader(3);
            diagnosticStep="loader.file_path_database_initialization";
            databaseBarrier(loader.getFileDatabase());
        }
        listener = new Listener(); loader.setDelegate(listener);
    }
    private static Result await() throws Exception {
        Result result = listener.terminal.poll(8,TimeUnit.SECONDS); require(result != null, "notification_timeout"); return result;
    }
    private static void loaded(Result result, TLRPC.Document document, byte[] expected) throws Exception {
        require(result.reason == -1 && result.name.equals(FileLoader.getAttachFileName(document))
                && result.type == FileLoader.MEDIA_DIR_DOCUMENT && result.file != null, "original_success_notification");
        require(Arrays.equals(Files.readAllBytes(result.file.toPath()),expected), "published_bytes");
    }
    private static void databaseBarrier(FilePathDatabase database) throws Exception {
        CountDownLatch drained=new CountDownLatch(1);AtomicReference<Throwable> failure=new AtomicReference<>();
        database.getQueue().postRunnable(()->{
            try {database.ensureDatabaseCreated();}
            catch(Throwable error){failure.set(error);}
            finally {drained.countDown();}
        });
        require(drained.await(8,TimeUnit.SECONDS),"database_queue_timeout");
        Throwable error=failure.get();
        if(error instanceof Exception)throw (Exception)error;
        if(error instanceof Error)throw (Error)error;
        if(error!=null)throw new AssertionError("database_queue_failure",error);
    }
    private static void noPartials() throws Exception {
        try (java.util.stream.Stream<java.nio.file.Path> paths = Files.walk(directory.toPath())) {
            require(!paths.anyMatch(path -> path.getFileName().toString().endsWith(".part")), "partial_retained");
        }
    }
    private static void loaderCases() throws Exception {
        run("document_entry_full_range", () -> {
            loadSetup();
            for (int i=0;i<descriptors.length();i++) {
                JSONObject row=descriptors.getJSONObject(i); TLRPC.Document document=project(row);
                peer.bytes("/v5/documents/"+row.getString("document_id"),PAYLOAD,row.getString("mime_type").isEmpty()?"application/octet-stream":"application/pdf");
                loader.loadFile(document,null,1,1); loaded(await(),document,PAYLOAD);
            }
            noPartials();
        });
        run("v5_emoji_and_ordinary_namespaces", () -> {
            loadSetup();byte[] bytes=Files.readAllBytes(new File(directory.getParentFile(),"delivery-emoji.webp").toPath());
            JSONObject ordinary=descriptor("7","ordinary.bin","",PAYLOAD);
            JSONObject body=snapshot(5,array(ordinary),array(record(1,"7"))).put("assets",array(image(5,bytes))).put("custom_emoji",array(emoji()));
            connect(body);
            TLRPC.Document emojiDocument=GramLabCustomEmoji.project(GramLabMedia.document(7));
            TLRPC.Document document=project(ordinary);
            peer.bytes("/v5/assets/5",bytes,"image/webp");peer.bytes("/v5/documents/7",PAYLOAD,"application/octet-stream");
            loader.loadFile(emojiDocument,null,1,1);loaded(await(),emojiDocument,bytes);
            loader.loadFile(document,null,1,1);loaded(await(),document,PAYLOAD);
            require(emojiDocument.id==7 && document.id==-7,"namespaces_collapsed");
        });
        run("image_location_entry", () -> {
            loadSetup(); TLRPC.Document document=project(descriptors.getJSONObject(1));
            peer.bytes("/v5/documents/2147483648",PAYLOAD,"application/octet-stream");
            loader.loadFile(ImageLocation.getForDocument(document),null,null,1,1); loaded(await(),document,PAYLOAD);
        });
        run("unknown_reserved_ids_no_network", () -> {
            loadSetup(); int requests=peer.count();
            for (long id:new long[]{-44,44,Long.MIN_VALUE,0}) {
                TLRPC.TL_document document=(TLRPC.TL_document)project(descriptors.getJSONObject(0)); document.id=id;
                loader.loadFile(document,null,1,1); require(await().reason==0,"unknown_reserved_success");
            }
            require(peer.count()==requests,"unknown_reserved_network");
        });
        run("encrypted_and_stream_rejected", () -> {
            loadSetup(); TLRPC.Document document=project(descriptors.getJSONObject(0)); int requests=peer.count();
            loader.loadFile(document,null,1,ImageLoader.CACHE_TYPE_ENCRYPTED); require(await().reason==0,"encrypted_success");
            document.key=new byte[32]; loader.loadFile(document,null,1,1); require(await().reason==0,"encrypted_document_success");
            loader.loadFile(ImageLocation.getForDocument(document),null,null,1,1); require(await().reason==0,"encrypted_location_success");
            document.key=null;
            Method stream=FileLoader.class.getDeclaredMethod("loadStreamFile",FileLoadOperationStream.class,
                    TLRPC.Document.class,ImageLocation.class,Object.class,long.class,boolean.class,int.class,int.class);
            stream.setAccessible(true);
            rejected(() -> stream.invoke(loader,null,document,null,null,0L,false,1,1));
            rejected(() -> stream.invoke(loader,null,null,ImageLocation.getForDocument(document),null,0L,false,1,1));
            require(peer.count()==requests,"encrypted_or_stream_network"); noPartials();
        });
        for (String fault: new String[]{"wrong_digest","wrong_length","truncation","wrong_mime","not_found"}) {
            run(fault+"_then_retry", () -> {
                loadSetup(); TLRPC.Document document=project(descriptors.getJSONObject(0));
                Reply reply=new Reply(PAYLOAD,"application/pdf");
                if (fault.equals("wrong_digest")) reply.bytes="WRONG document!!!\n".getBytes(StandardCharsets.UTF_8);
                if (fault.equals("wrong_length")) reply.length=PAYLOAD.length+1;
                if (fault.equals("truncation")) reply.bytes=Arrays.copyOf(PAYLOAD,3);
                if (fault.equals("wrong_mime")) reply.mime="text/plain";
                if (fault.equals("not_found")) reply.status=404;
                peer.put("/v5/documents/1",reply); loader.loadFile(document,null,1,1);
                require(await().reason==0,"fault_success"); noPartials();
                peer.bytes("/v5/documents/1",PAYLOAD,"application/pdf");
                loader.loadFile(document,null,1,1); loaded(await(),document,PAYLOAD); noPartials();
            });
        }
        run("coalescing_cancel_retry", () -> {
            loadSetup(); TLRPC.Document document=project(descriptors.getJSONObject(0));
            Reply blocked=new Reply(PAYLOAD,"application/pdf"); blocked.release=new CountDownLatch(1);
            peer.put("/v5/documents/1",blocked); int before=peer.count();
            loader.loadFile(document,null,1,1); require(blocked.entered.await(5,TimeUnit.SECONDS),"request_not_entered");
            loader.loadFile(ImageLocation.getForDocument(document),null,null,1,1);
            loader.cancelLoadFile(document); require(await().reason==1,"cancel_reason");
            blocked.release.countDown(); require(blocked.finished.await(5,TimeUnit.SECONDS),"blocked_request_not_finished");
            require(peer.count()==before+1,"not_coalesced");
            peer.bytes("/v5/documents/1",PAYLOAD,"application/pdf"); loader.loadFile(document,null,1,1);
            loaded(await(),document,PAYLOAD); noPartials(); require(listener.terminal.isEmpty(),"duplicate_terminal");
        });
        run("coalesced_completion", () -> {
            loadSetup();TLRPC.Document document=project(descriptors.getJSONObject(0));
            Reply blocked=new Reply(PAYLOAD,"application/pdf");blocked.release=new CountDownLatch(1);
            peer.put("/v5/documents/1",blocked);int before=peer.count();
            loader.loadFile(document,null,1,1);require(blocked.entered.await(5,TimeUnit.SECONDS),"coalesced_request_start");
            loader.loadFile(ImageLocation.getForDocument(document),null,null,1,1);blocked.release.countDown();
            loaded(await(),document,PAYLOAD);require(blocked.finished.await(5,TimeUnit.SECONDS),"coalesced_request_finish");
            require(peer.count()==before+1&&listener.terminal.isEmpty(),"coalesced_terminal_or_request_count");
        });
        run("inflight_authority_change", () -> {
            loadSetup();TLRPC.Document document=project(descriptors.getJSONObject(0));
            Reply blocked=new Reply(PAYLOAD,"application/pdf");blocked.release=new CountDownLatch(1);
            peer.put("/v5/documents/1",blocked);loader.loadFile(document,null,1,1);
            require(blocked.entered.await(5,TimeUnit.SECONDS),"authority_request_start");
            config.put("world_id","different-authority");install(array());blocked.release.countDown();
            require(await().reason==0,"stale_authority_success");
            require(!new File(FileLoader.getDirectory(FileLoader.MEDIA_DIR_CACHE),FileLoader.getAttachFileName(document)).exists(),"stale_authority_publication");
            noPartials();
        });
        for (String authorityField : new String[]{"capability", "endpoint"}) {
            run("inflight_"+authorityField+"_rotation", () -> {
                loadSetup();TLRPC.Document document=project(descriptors.getJSONObject(0));
                Reply blocked=new Reply(PAYLOAD,"application/pdf");blocked.release=new CountDownLatch(1);
                peer.put("/v5/documents/1",blocked);loader.loadFile(document,null,1,1);
                require(blocked.entered.await(5,TimeUnit.SECONDS),"rotation_request_start");
                String original=config.getString(authorityField);
                config.put(authorityField,authorityField.equals("endpoint") ? "http://127.0.0.1:1"
                        : "gramlab-client_"+new String(new char[43]).replace('\0','e'));
                install(array());
                // A -> B -> A must not revive the old transfer after authority rotation.
                config.put(authorityField,original);install(array());blocked.release.countDown();
                require(await().reason==0,"rotated_authority_success");
                require(!new File(FileLoader.getDirectory(FileLoader.MEDIA_DIR_CACHE),FileLoader.getAttachFileName(document)).exists(),
                        "rotated_authority_publication");
                noPartials();
            });
        }
        run("warm_keyed_cache", () -> {
            loadSetup(); TLRPC.Document document=project(descriptors.getJSONObject(0)); peer.bytes("/v5/documents/1",PAYLOAD,"application/pdf");
            loader.loadFile(document,null,1,1); loaded(await(),document,PAYLOAD); int before=peer.count();
            loader.loadFile(document,null,1,1); loaded(await(),document,PAYLOAD); require(peer.count()==before,"warm_cache_network");
        });
        run("cache10_exact_boundary_and_upgrade", () -> {
            loadSetup();byte[] limit=new byte[2*1024*1024];Arrays.fill(limit,(byte)65);
            JSONObject small=descriptor("201","limit.bin","",limit);
            byte[] oversizedBytes=new byte[limit.length+1];
            JSONObject large=descriptor("202","over.bin","",oversizedBytes);install(array(small,large));
            TLRPC.Document document=project(small);String name=FileLoader.getAttachFileName(document);
            Reply blocked=new Reply(limit,"application/octet-stream");blocked.release=new CountDownLatch(1);
            peer.put("/v5/documents/201",blocked);loader.loadFile(document,null,1,10);
            require(blocked.entered.await(5,TimeUnit.SECONDS),"cache10_request_start");
            require(!loader.isLoadingFile(name),"cache10_ui_registration");
            loader.loadFile(document,null,1,0);require(loader.isLoadingFile(name),"cache10_upgrade_ui_missing");
            blocked.release.countDown();loaded(await(),document,limit);
            int requests=peer.count();TLRPC.Document oversized=project(large);
            File caseDirectory=FileLoader.getDirectory(FileLoader.MEDIA_DIR_DOCUMENT).getParentFile();
            List<String> before=new ArrayList<>();
            try(java.util.stream.Stream<java.nio.file.Path> paths=Files.walk(caseDirectory.toPath())) {
                paths.forEach(path -> before.add(path.toString()));
            }
            Collections.sort(before);
            loader.loadFile(oversized,null,1,10);require(await().reason==0,"unsupported_preload_success");
            loader.loadFile(ImageLocation.getForDocument(oversized),null,null,1,10);
            require(await().reason==0,"unsupported_image_preload_success");
            require(peer.count()==requests && !loader.isLoadingFile(FileLoader.getAttachFileName(oversized)),"unsupported_preload_network_or_ui");
            List<String> after=new ArrayList<>();
            try(java.util.stream.Stream<java.nio.file.Path> paths=Files.walk(caseDirectory.toPath())) {
                paths.forEach(path -> after.add(path.toString()));
            }
            Collections.sort(after);require(before.equals(after),"unsupported_preload_wrote_files");
            peer.bytes("/v5/documents/202",oversizedBytes,"application/octet-stream");
            loader.loadFile(oversized,null,1,0);loaded(await(),oversized,oversizedBytes);
            noPartials();
        });
        run("saved_and_missing_paths", () -> {
            loadSetup(); TLRPC.Document document=project(descriptors.getJSONObject(0));
            File saved=new File(FileLoader.getDirectory(FileLoader.MEDIA_DIR_FILES),"renamed.pdf"); Files.write(saved.toPath(),PAYLOAD);
            loader.getFileDatabase().putPath(document.id,-1,FileLoader.MEDIA_DIR_DOCUMENT,0,saved.toString());
            // Drain the original queue before reading its cache or reopening SQLite.
            databaseBarrier(loader.getFileDatabase());
            require(loader.getFileDatabase().getPath(document.id,-1,FileLoader.MEDIA_DIR_DOCUMENT,true).equals(saved.toString()),"saved_path_not_written");
            int before=peer.count(); loader.loadFile(document,null,1,0); Result result=await(); loaded(result,document,PAYLOAD);
            require(result.file.equals(saved)&&peer.count()==before,"saved_path_ignored");
            require(saved.delete(),"remove_saved_file"); peer.bytes("/v5/documents/1",PAYLOAD,"application/pdf");
            loader.loadFile(document,null,1,10); result=await(); loaded(result,document,PAYLOAD);
            require(result.file.getParentFile().equals(FileLoader.getDirectory(FileLoader.MEDIA_DIR_DOCUMENT)),"missing_path_destination");
        });
        run("presentation_collision_and_database_reopen", () -> {
            loadSetup();
            File externalRoot=ApplicationLoader.applicationContext.getExternalFilesDir(null);
            require(externalRoot!=null,"external_destination_unavailable");
            File external=new File(externalRoot,"document-delivery-collision-"+sequence);
            Files.createDirectory(external.toPath());
            SparseArray<File> originalDirs=new SparseArray<>();
            for(int kind=0;kind<=6;kind++)originalDirs.put(kind,FileLoader.getDirectory(kind));
            originalDirs.put(FileLoader.MEDIA_DIR_FILES,external);FileLoader.setMediaDirs(originalDirs);
            JSONObject first=descriptor("101","same.bin","",PAYLOAD);
            byte[] secondBytes="second payload\n".getBytes(StandardCharsets.UTF_8);
            JSONObject second=descriptor("102","same.bin","",secondBytes); install(array(first,second));
            TLRPC.Document a=project(first),b=project(second);
            TLRPC.TL_message aMessage=new TLRPC.TL_message(); aMessage.message=""; aMessage.id=101; aMessage.date=100;
            aMessage.peer_id=new TLRPC.TL_peerUser(); aMessage.peer_id.user_id=2;
            aMessage.from_id=new TLRPC.TL_peerUser(); aMessage.from_id.user_id=2;
            aMessage.media=new TLRPC.TL_messageMediaDocument(); aMessage.media.document=a; aMessage.media.flags=1;
            TLRPC.TL_message bMessage=new TLRPC.TL_message(); bMessage.message=""; bMessage.id=102; bMessage.date=100;
            bMessage.peer_id=aMessage.peer_id; bMessage.from_id=aMessage.from_id;
            bMessage.media=new TLRPC.TL_messageMediaDocument(); bMessage.media.document=b; bMessage.media.flags=1;
            java.util.HashMap<Long,TLRPC.User> people=new java.util.HashMap<>();
            TLRPC.TL_user sender=new TLRPC.TL_user();sender.id=2;sender.first_name="Files";sender.bot=true;people.put(2L,sender);
            java.lang.reflect.Constructor<MessageObject> constructor=MessageObject.class.getConstructor(
                    int.class,TLRPC.Message.class,java.util.AbstractMap.class,boolean.class,boolean.class);
            MessageObject aParent=constructor.newInstance(3,aMessage,people,false,false), bParent=constructor.newInstance(3,bMessage,people,false,false);
            require(FileLoader.canSaveAsFile(aParent)&&FileLoader.canSaveAsFile(bParent),"original_can_save");
            File original=new File(FileLoader.getDirectory(FileLoader.MEDIA_DIR_FILES),"same.bin"); Files.write(original.toPath(),PAYLOAD);
            peer.bytes("/v5/documents/101",PAYLOAD,"application/octet-stream"); peer.bytes("/v5/documents/102",secondBytes,"application/octet-stream");
            loader.loadFile(a,aParent,1,0); loader.loadFile(b,bParent,1,10);
            Result left=await(),right=await(); Map<String,Result> results=new LinkedHashMap<>();results.put(left.name,left);results.put(right.name,right);
            loaded(results.get(FileLoader.getAttachFileName(a)),a,PAYLOAD);loaded(results.get(FileLoader.getAttachFileName(b)),b,secondBytes);
            List<String> names=new ArrayList<>(Arrays.asList(left.file.getName(),right.file.getName())); Collections.sort(names);
            require(names.equals(Arrays.asList("same (1).bin","same (2).bin")),"collision_suffixes");
            require(Arrays.equals(Files.readAllBytes(original.toPath()),PAYLOAD),"existing_file_replaced");
            databaseBarrier(loader.getFileDatabase());
            FilePathDatabase reopened=new FilePathDatabase(3);
            for (TLRPC.Document document:Arrays.asList(a,b)) {
                String expected=results.get(FileLoader.getAttachFileName(document)).file.toString();
                require(loader.getFileDatabase().getPath(document.id,-1,3,true).equals(expected),"actual_path_not_persisted");
                require(reopened.getPath(document.id,-1,3,true).equals(expected),"reopened_path_mismatch");
            }
            File retained=new File(directory,"external-files-evidence");require(retained.mkdir(),"fresh_external_evidence");
            for(File file:Arrays.asList(original,left.file,right.file))Files.copy(file.toPath(),new File(retained,file.getName()).toPath());
            observations.put(new JSONObject().put("case",phase).put("new_names",new JSONArray(names)).put("original_unchanged",true)
                    .put("filesystem","app_external_files"));
            JSONObject restart=new JSONObject().put("world_id",config.getString("world_id")).put("sequence",sequence)
                    .put("documents",array(first,second)).put("paths",array(results.get(FileLoader.getAttachFileName(a)).file.toString(),
                            results.get(FileLoader.getAttachFileName(b)).file.toString()));
            Files.write(new File(directory,"restart-input.json").toPath(),restart.toString(2).getBytes(StandardCharsets.UTF_8));
        });
    }

    private static void filesystemCases() throws Exception {
        run("external_files_primitives", () -> {
            JSONObject result=new JSONObject().put("case",phase);observations.put(result);
            diagnosticStep="filesystem.getExternalFilesDir";
            File parent=ApplicationLoader.applicationContext.getExternalFilesDir(null);
            result.put("external_root",parent==null?JSONObject.NULL:parent.toString());
            diagnosticStep="filesystem.storage_state";
            result.put("storage_state",android.os.Environment.getExternalStorageState());
            require(parent!=null,"external_root_unavailable");
            result.put("canonical_root",parent.getCanonicalPath()).put("root_exists",parent.exists())
                    .put("root_is_directory",parent.isDirectory()).put("root_can_write",parent.canWrite());
            diagnosticStep="filesystem.newFile";
            File external=new File(parent,"document-delivery-filesystem-probe");
            result.put("directory",external.toString()).put("canonical_directory",external.getCanonicalPath())
                    .put("directory_exists",external.exists()).put("directory_is_directory",external.isDirectory())
                    .put("directory_can_write",external.canWrite());
            diagnosticStep="filesystem.createDirectory";Files.createDirectory(external.toPath());
            File source=new File(external,"source.bin"),target=new File(external,"linked.bin");
            diagnosticStep="filesystem.write_source";Files.write(source.toPath(),PAYLOAD,java.nio.file.StandardOpenOption.CREATE_NEW);
            diagnosticStep="filesystem.java_link";
            try {Files.createLink(target.toPath(),source.toPath());result.put("java_hard_link",true);}
            catch(java.io.IOException error){result.put("java_hard_link",false).put("java_exception",error.getClass().getName());}
            diagnosticStep="filesystem.os_link";
            try {android.system.Os.link(source.toString(),new File(external,"os-linked.bin").toString());result.put("os_hard_link",true);}
            catch(android.system.ErrnoException error){result.put("os_hard_link",false).put("errno",error.errno);}
            diagnosticStep="filesystem.write_collision";
            File occupied=new File(external,"occupied.bin");Files.write(occupied.toPath(),new byte[]{1},java.nio.file.StandardOpenOption.CREATE_NEW);
            diagnosticStep="filesystem.move_collision";
            try {Files.move(source.toPath(),occupied.toPath());throw new AssertionError("existing_destination_overwritten");}
            catch(java.nio.file.FileAlreadyExistsException expected){result.put("move_rejects_existing",true);}
            require(Arrays.equals(Files.readAllBytes(occupied.toPath()),new byte[]{1}),"existing_bytes_changed");
        });
    }

    private static void restartCases() throws Exception {
        run("cold_process_saved_destinations", () -> {
            JSONObject retained=new JSONObject(new String(Files.readAllBytes(new File(directory,"restart-input.json").toPath()),StandardCharsets.UTF_8));
            config=new JSONObject().put("endpoint","http://127.0.0.1:"+peer.port()).put("capability",CAPABILITY)
                    .put("world_id",retained.getString("world_id")).put("user_id",1).put("bridge_version",5);
            descriptors=retained.getJSONArray("documents");install(descriptors);
            SparseArray<File> dirs=new SparseArray<>();
            for(int kind=0;kind<=6;kind++)dirs.put(kind,new File(directory,"files-"+retained.getInt("sequence")+"/"+kind));
            FileLoader.setMediaDirs(dirs);loader=new FileLoader(3);listener=new Listener();loader.setDelegate(listener);
            for(int i=0;i<descriptors.length();i++) {
                TLRPC.Document document=project(descriptors.getJSONObject(i));loader.loadFile(document,null,1,i==0?0:10);
                Result result=await();require(result.reason==-1 && result.file.toString().equals(retained.getJSONArray("paths").getString(i)),"cold_saved_path");
                require(hash(Files.readAllBytes(result.file.toPath())).equals(descriptors.getJSONObject(i).getString("sha256")),"cold_bytes");
            }
            require(peer.count()==0,"cold_cache_network");noPartials();
        });
    }

    private static final class Reply {
        byte[] bytes; String mime; long length; int status=200;
        CountDownLatch release;
        final CountDownLatch entered=new CountDownLatch(1),finished=new CountDownLatch(1);
        Reply(byte[] bytes,String mime) { this.bytes=bytes;this.mime=mime;length=bytes.length; }
    }
    /** Bounded local HTTP peer; it cannot resolve or connect to any external address. */
    private static final class Peer implements AutoCloseable {
        final ServerSocket server=new ServerSocket(0,16,InetAddress.getByName("127.0.0.1"));
        final Map<String,Reply> replies=Collections.synchronizedMap(new LinkedHashMap<>());
        final List<JSONObject> requests=Collections.synchronizedList(new ArrayList<>());
        final List<Thread> workers=Collections.synchronizedList(new ArrayList<>());
        volatile boolean closed;
        final Thread acceptor;
        Peer() throws Exception {
            acceptor=new Thread(() -> {
                while (!closed) {
                    try {
                        Socket socket=server.accept(); Thread worker=new Thread(() -> serve(socket)); workers.add(worker); worker.start();
                    } catch (Exception error) { if (!closed) throw new AssertionError(error); }
                }
            }); acceptor.start();
        }
        int port() { return server.getLocalPort(); }
        int count() { return requests.size(); }
        void put(String path,Reply reply) { replies.put(path,reply); }
        void json(String path,JSONObject body) { put(path,new Reply(body.toString().getBytes(StandardCharsets.UTF_8),"application/json")); }
        void bytes(String path,byte[] bytes,String mime) { put(path,new Reply(bytes,mime)); }
        void serve(Socket socket) {
            Reply reply=null;
            try (Socket active=socket) {
                active.setSoTimeout(5000);
                BufferedReader reader=new BufferedReader(new InputStreamReader(active.getInputStream(),StandardCharsets.UTF_8));
                String first=reader.readLine(); require(first!=null && first.length()<2048,"request_line");
                String[] parts=first.split(" "); require(parts.length==3,"request_parts");
                int length=0,total=first.length(); boolean authenticated=false;
                for (String line;(line=reader.readLine())!=null&&!line.isEmpty();) {
                    total+=line.length();require(total<16384,"request_headers");
                    if (line.regionMatches(true,0,"Content-Length:",0,15)) length=Integer.parseInt(line.substring(15).trim());
                    if (line.regionMatches(true,0,"Authorization:",0,14)) authenticated=line.substring(14).trim().equals("Bearer "+CAPABILITY);
                }
                require(authenticated&&length>=0&&length<65536,"request_authority_or_size");
                char[] body=new char[length];int used=0;while(used<length) {int n=reader.read(body,used,length-used);require(n>0,"request_body");used+=n;}
                requests.add(new JSONObject().put("case",phase).put("method",parts[0]).put("path",parts[1]).put("authorized",true));
                reply=replies.get(parts[1]);require(reply!=null,"unexpected_request");reply.entered.countDown();
                if(reply.release!=null) require(reply.release.await(5,TimeUnit.SECONDS),"peer_release_timeout");
                OutputStream out=active.getOutputStream();
                String headers="HTTP/1.1 "+reply.status+" Probe\r\nContent-Type: "+reply.mime+"\r\nContent-Length: "+reply.length+"\r\nConnection: close\r\n\r\n";
                out.write(headers.getBytes(StandardCharsets.US_ASCII));out.write(reply.bytes);out.flush();
            } catch (Exception ignored) { /* Cancellation closes the original socket. Missing results fail the suite. */ }
            finally {if(reply!=null)reply.finished.countDown();}
        }
        public void close() throws java.io.IOException {
            closed=true;server.close();
            try {acceptor.join(5000);for(Thread worker:workers)worker.join(6000);}
            catch(InterruptedException error){Thread.currentThread().interrupt();throw new java.io.IOException("peer_close_interrupted",error);}
        }
    }

    private static byte[] boundedFile(String path,int maximum) throws Exception {
        try(java.io.InputStream input=Files.newInputStream(new File(path).toPath());
                java.io.ByteArrayOutputStream output=new java.io.ByteArrayOutputStream()) {
            byte[] buffer=new byte[4096];int count;
            while((count=input.read(buffer))!=-1){require(output.size()+count<=maximum,"process_metadata_bound");output.write(buffer,0,count);}
            return output.toByteArray();
        }
    }
    private static JSONObject processContext() throws Exception {
        JSONObject result=new JSONObject();
        for(String line:new String(boundedFile("/proc/self/status",16384),StandardCharsets.UTF_8).split("\n")) {
            if(line.startsWith("Uid:")||line.startsWith("Gid:")||line.startsWith("Groups:")) {
                require(line.length()<=1024,"process_identity_bound");result.put(line.substring(0,line.indexOf(':')),line.substring(line.indexOf(':')+1).trim());
            }
        }
        return result.put("mount_namespace",android.system.Os.readlink("/proc/self/ns/mnt"))
                .put("mountinfo_sha256",hash(boundedFile("/proc/self/mountinfo",512*1024)))
                .put("selinux_context",new String(boundedFile("/proc/self/attr/current",4096),StandardCharsets.UTF_8).trim());
    }
    private static JSONObject executeCases(String mode,JSONObject runtime) throws Exception {
        try(Peer value=new Peer()) {
            peer=value;if(mode.equals("suite")){bridgeCases();
                run("production_document_rename",()->RenameNoReplaceProbe.runProduction(ApplicationLoader.applicationContext.getExternalFilesDir(null),observations));
                loaderCases();}
            else if(mode.equals("filesystem"))filesystemCases();
            else if(mode.equals("rename"))run("external_rename_noreplace",()->RenameNoReplaceProbe.run(ApplicationLoader.applicationContext.getExternalFilesDir(null),observations));
            else if(mode.equals("restart"))restartCases();int failed=0;
            for(int i=0;i<cases.length();i++)if(!cases.getJSONObject(i).getString("status").equals("passed"))failed++;
            JSONObject summary=new JSONObject().put("schema",1).put("cases",cases).put("observations",observations)
                    .put("requests",new JSONArray(peer.requests)).put("passed",cases.length()-failed).put("failed",failed)
                    .put("runtime",runtime.put("native_loaded",NativeLoader.loaded()).put("activated_accounts",UserConfig.getActivatedAccountsCount()));
            Files.write(new File(directory,mode+"-summary.json").toPath(),summary.toString(2).getBytes(StandardCharsets.UTF_8));
            return summary;
        }
    }
    public static JSONObject diagnosticFailure(Throwable error,String failurePhase) throws Exception {
        Throwable actual=error instanceof InvocationTargetException
                &&((InvocationTargetException)error).getTargetException()!=null
                ?((InvocationTargetException)error).getTargetException():error;
        return diagnosticThrowable(actual).put("schema",1).put("phase",failurePhase).put("stage",diagnosticStep);
    }
    /** The framework supplies this actual installed target application and its Context. */
    public static JSONObject instrumented(ApplicationLoader application,Context context,String mode) throws Exception {
        diagnosticStep="instrumentation.target_identity";
        require(mode!=null && (mode.equals("filesystem")||mode.equals("rename")||mode.equals("suite")||mode.equals("restart")),"instrumentation_mode");
        require(context.getApplicationContext()==application && context.getPackageName().equals("org.gramlab.android")
                && application.getPackageName().equals(context.getPackageName())
                && context.getApplicationInfo().uid==android.os.Process.myUid()
                && application.getApplicationInfo().uid==android.os.Process.myUid()
                && context.getAttributionSource().getUid()==android.os.Process.myUid()
                && context.getPackageName().equals(context.getAttributionSource().getPackageName()),"instrumentation_target_identity");
        ApplicationLoader.applicationLoaderInstance=application;ApplicationLoader.applicationContext=context;
        diagnosticStep="instrumentation.android_utilities";
        require("Hello World!".equals(AndroidUtilities.getHelloWorld()),"original_android_utilities");
        ApplicationLoader.applicationHandler=new Handler(Looper.getMainLooper());
        diagnosticStep="instrumentation.private_directory";
        directory=new File(context.getFilesDir(),mode.equals("filesystem")?"document-delivery-filesystem-probe":mode.equals("rename")?"document-delivery-rename-probe":"document-delivery-probe").getCanonicalFile();
        require(directory.getParentFile().equals(context.getFilesDir().getCanonicalFile())
                && (mode.equals("restart")?directory.isDirectory():directory.mkdir()),"fresh_private_directory");
        diagnosticStep="instrumentation.native_loader";
        NativeLoader.initNativeLibs(context);require(NativeLoader.loaded(),"original_native_loader");
        diagnosticStep="instrumentation.native_vm_binding";ConnectionsManager.native_setJava(false);
        diagnosticStep="instrumentation.process_context";
        JSONObject runtime=new JSONObject().put("pid",android.os.Process.myPid()).put("uid",android.os.Process.myUid())
                .put("package",context.getPackageName()).put("application_package",application.getPackageName())
                .put("application_context_same",context.getApplicationContext()==application)
                .put("attribution_package",context.getAttributionSource().getPackageName())
                .put("attribution_uid",context.getAttributionSource().getUid())
                .put("current_application",application.getClass().getName())
                .put("execution","target_instrumentation").put("application_on_create_suppressed",true)
                .put("process_context",processContext()).put("apk_sha256",fileHash(new File(context.getApplicationInfo().sourceDir)));
        return executeCases(mode,runtime);
    }

    @SuppressWarnings("deprecation")
    public static void main(String[] args) {
        try {
            require(args.length==2 && (args[1].equals("suite") || args[1].equals("restart") || args[1].equals("filesystem") || args[1].equals("identity")),"arguments");
            if(Looper.getMainLooper()==null)Looper.prepareMainLooper();
            Class<?> activityThread=Class.forName("android.app.ActivityThread");
            Object thread=activityThread.getMethod("systemMain").invoke(null);
            Context system=(Context)activityThread.getMethod("getSystemContext").invoke(thread);
            diagnosticStep="context.package";
            Context packageContext=system.createPackageContext("org.gramlab.android",Context.CONTEXT_IGNORE_SECURITY);
            diagnosticStep="context.loadedApk";
            Class<?> implementation=Class.forName("android.app.ContextImpl");
            Field packageInfo=implementation.getDeclaredField("mPackageInfo");packageInfo.setAccessible(true);
            Object loadedApk=packageInfo.get(packageContext);
            diagnosticStep="context.createAppContext";
            Method create=implementation.getDeclaredMethod("createAppContext",activityThread,Class.forName("android.app.LoadedApk"));
            create.setAccessible(true);Context context=(Context)create.invoke(null,thread,loadedApk);
            diagnosticStep="context.attribution";
            Method opPackage=Context.class.getDeclaredMethod("getOpPackageName");opPackage.setAccessible(true);
            String opPackageName=(String)opPackage.invoke(context);
            require(context.getPackageName().equals("org.gramlab.android") && opPackageName.equals(context.getPackageName())
                    && context.getApplicationInfo().uid==android.os.Process.myUid()
                    && context.getAttributionSource().getUid()==android.os.Process.myUid()
                    && context.getPackageName().equals(context.getAttributionSource().getPackageName()),"original_context_attribution");
            ApplicationLoader application=new ApplicationLoader();
            Method attach=ApplicationLoader.class.getDeclaredMethod("attachBaseContext",Context.class);attach.setAccessible(true);attach.invoke(application,context);
            diagnosticStep="context.initialApplication";
            Method currentPackage=activityThread.getDeclaredMethod("currentOpPackageName");currentPackage.setAccessible(true);
            String previousOperationPackage=String.valueOf(currentPackage.invoke(null));
            Field initial=activityThread.getDeclaredField("mInitialApplication");initial.setAccessible(true);initial.set(thread,application);
            Object currentApplication=activityThread.getMethod("currentApplication").invoke(null);
            String currentOperationPackage=(String)currentPackage.invoke(null);
            require(currentApplication==application && currentOperationPackage.equals(context.getPackageName()),"activity_thread_attribution");
            ApplicationLoader.applicationLoaderInstance=application;ApplicationLoader.applicationContext=context;
            ApplicationLoader.applicationHandler=new Handler(Looper.getMainLooper());
            directory=new File(args[0]).getCanonicalFile();
            require(directory.getParentFile().equals(context.getFilesDir().getCanonicalFile())
                    &&directory.getName().equals(args[1].equals("identity")?"document-delivery-identity-probe":args[1].equals("filesystem")?"document-delivery-filesystem-probe":"document-delivery-probe")
                    && (args[1].equals("restart")?directory.isDirectory():directory.mkdir()),"fresh_private_directory");
            NativeLoader.initNativeLibs(context);require(NativeLoader.loaded(),"original_native_loader");ConnectionsManager.native_setJava(false);
            new Thread(() -> {
                int status=2;
                try {
                    JSONObject runtime=new JSONObject().put("pid",android.os.Process.myPid()).put("uid",android.os.Process.myUid())
                                    .put("package",context.getPackageName()).put("op_package",opPackageName)
                                    .put("previous_operation_package",previousOperationPackage)
                                    .put("current_operation_package",currentOperationPackage)
                                    .put("current_application",currentApplication.getClass().getName())
                                    .put("attribution_package",context.getAttributionSource().getPackageName())
                                    .put("attribution_uid",context.getAttributionSource().getUid())
                                    .put("apk_sha256",fileHash(new File(context.getApplicationInfo().sourceDir)))
                                    .put("execution","run_as_app_process").put("process_context",processContext());
                    JSONObject summary=executeCases(args[1],runtime);
                    System.out.println(summary);status=summary.getInt("failed")==0?0:1;
                } catch(Throwable error) {
                    System.out.println("{\"schema\":1,\"phase\":\""+phase+"\",\"exception\":\""+error.getClass().getName()+"\"}");
                } finally {System.exit(status);}
            },"document-delivery-suite").start();
            Looper.loop();
        } catch(Throwable error) {
            try {
                System.out.println(diagnosticFailure(error,"initialization"));
            } catch(Exception ignored) {System.out.println("{\"schema\":1,\"phase\":\"initialization\"}");}
            System.exit(2);
        }
    }
}
