// SPDX-License-Identifier: GPL-2.0-or-later
package org.telegram.gramlab;

import android.app.Activity;
import android.app.Application;
import android.content.Context;
import android.graphics.Rect;
import android.graphics.RectF;
import android.os.Bundle;
import android.os.SystemClock;
import android.text.Spanned;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewParent;
import android.view.ViewTreeObserver;
import org.json.JSONArray;
import org.json.JSONObject;
import org.telegram.messenger.MessageObject;
import org.telegram.messenger.RichMessageLayout;
import org.telegram.tgnet.tl.TL_keyboard;
import org.telegram.ui.Cells.ChatMessageCell;
import org.telegram.ui.LaunchActivity;

import java.io.File;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Opt-in experiment only. Reads original post-draw objects; never performs input. */
public final class RichActionGeometryProbe implements Application.ActivityLifecycleCallbacks {
    private final File directory;
    private final String nonce;
    private final long peerId;
    private final int messageId;
    private final ExecutorService writer = Executors.newSingleThreadExecutor();
    private View decor;
    private ViewTreeObserver.OnDrawListener listener;
    private boolean posted;
    private boolean redrawScheduled;
    private long generation;
    private long lastSample;

    private RichActionGeometryProbe(File directory, JSONObject input) throws Exception {
        this.directory = directory;
        nonce = input.getString("nonce");
        peerId = input.getLong("peer_id");
        messageId = input.getInt("message_id");
        if (!nonce.matches("[a-zA-Z0-9_-]{1,64}") || peerId <= 0 || messageId <= 0) {
            throw new IllegalArgumentException("invalid_geometry_identity");
        }
    }

    public static void install(Context context, GramLabBridge.Snapshot snapshot) throws Exception {
        File directory = new File(context.getFilesDir(), "gramlab");
        File input = new File(directory, "rich-action-geometry.json");
        if (!input.exists()) return;
        Files.deleteIfExists(new File(directory, "rich-action-geometry-result.json").toPath());
        if (!input.isFile() || input.length() > 4096) {
            throw new IllegalArgumentException("invalid_geometry_configuration");
        }
        JSONObject config = new JSONObject(new String(Files.readAllBytes(input.toPath()), StandardCharsets.UTF_8));
        if (config.length() != 6 || config.getInt("schema") != 1
                || !snapshot.worldId.equals(config.getString("world_id"))
                || snapshot.persona != config.getLong("user_id")) {
            throw new IllegalArgumentException("geometry_binding_mismatch");
        }
        RichActionGeometryProbe probe = new RichActionGeometryProbe(directory, config);
        ((Application) context.getApplicationContext()).registerActivityLifecycleCallbacks(probe);
        probe.publish(new JSONObject().put("available", false).put("reason", "awaiting_activity"));
    }

    private static Object field(Object object, String name) throws Exception {
        Field field = object.getClass().getDeclaredField(name);
        field.setAccessible(true);
        return field.get(object);
    }

    private static final class Unavailable extends RuntimeException {
        Unavailable(String reason) { super(reason); }
    }

    private static void require(boolean condition, String reason) {
        if (!condition) throw new Unavailable(reason);
    }

    private static JSONArray rect(RectF rectangle) throws Exception {
        return new JSONArray().put(rectangle.left).put(rectangle.top).put(rectangle.right).put(rectangle.bottom);
    }

    private void publish(JSONObject result) throws Exception {
        result.put("schema", 1).put("nonce", nonce).put("generation", ++generation)
                .put("uptime_ms", SystemClock.uptimeMillis()).put("pid", android.os.Process.myPid())
                .put("peer_id", peerId).put("message_id", messageId);
        byte[] bytes = result.toString().getBytes(StandardCharsets.UTF_8);
        // Small, throttled observations; no filesystem operation runs in a drawing callback.
        writer.execute(() -> {
            try {
                File temporary = new File(directory, "rich-action-geometry-result.tmp");
                Files.write(temporary.toPath(), bytes);
                Files.move(temporary.toPath(), new File(directory, "rich-action-geometry-result.json").toPath(),
                        StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            } catch (Exception ignored) {
                // A missing/stale result is an observation failure, never an input fallback.
            }
        });
    }

    private void find(View view, ArrayList<ChatMessageCell> cells) {
        if (!view.isShown()) return;
        if (view instanceof ChatMessageCell) {
            ChatMessageCell cell = (ChatMessageCell) view;
            MessageObject message = cell.getMessageObject();
            if (message != null && message.getId() == messageId && message.getDialogId() == peerId) cells.add(cell);
        }
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) find(group.getChildAt(i), cells);
        }
    }

    private JSONObject target(String kind, int block, int index, RichMessageLayout.RichButton button,
                              RectF local, float originX, float originY, Rect visible) throws Exception {
        RectF screen = new RectF(local);
        screen.offset(originX, originY);
        require(screen.width() > 0 && screen.height() > 0 && new RectF(visible).contains(screen), "clipped_target");
        JSONObject result = new JSONObject().put("kind", kind).put("block", block).put("index", index)
                .put("text", button.text.layout.getText().toString());
        if (button.type instanceof TL_keyboard.TL_inlineButtonTypeCallback) {
            require(!button.isDisabled, "callback_disabled_state");
            TL_keyboard.TL_inlineButtonTypeCallback action = (TL_keyboard.TL_inlineButtonTypeCallback) button.type;
            require(!action.requires_password, "password_callback");
            result.put("callback_data", new String(action.data, StandardCharsets.UTF_8));
        } else if (button.type instanceof TL_keyboard.TL_inlineButtonTypeCopy) {
            require(!button.isDisabled, "copy_disabled_state");
            TL_keyboard.TL_inlineButtonTypeCopy action = (TL_keyboard.TL_inlineButtonTypeCopy) button.type;
            require(action.copy_text != null, "copy_text_unavailable");
            result.put("copy_text", action.copy_text);
        } else if (button.type instanceof TL_keyboard.TL_inlineButtonTypeDisabled) {
            require(button.isDisabled, "disabled_action_state_mismatch");
            result.put("disabled", true);
        } else {
            throw new Unavailable("unsupported_action");
        }
        return result
                .put("local_bounds", rect(local)).put("origin", new JSONArray().put(originX).put(originY))
                .put("screen_bounds", rect(screen));
    }

    private JSONObject observe(View root) throws Exception {
        require(root.isAttachedToWindow() && root.hasWindowFocus(), "inactive_window");
        ArrayList<ChatMessageCell> cells = new ArrayList<>();
        find(root, cells);
        require(cells.size() == 1, "message_not_unique_or_visible");
        ChatMessageCell cell = cells.get(0);
        require(cell.getClass() == ChatMessageCell.class, "unsupported_cell_subclass");
        for (View view = cell; view != null;) {
            require(view.getScaleX() == 1 && view.getScaleY() == 1 && view.getRotation() == 0
                    && view.getRotationX() == 0 && view.getRotationY() == 0 && view.getAlpha() == 1,
                    "transformed_view");
            ViewParent parent = view.getParent();
            view = parent instanceof View ? (View) parent : null;
        }
        require(!cell.getTransitionParams().animateRichLayout, "rich_transition");
        RichMessageLayout layout = cell.getMessageObject().richLayout;
        require(layout != null && !layout.isRtl() && !layout.isPart && !layout.detailsAnimating && !layout.blockquoteAnimating
                && (layout.typingAnimator == null || !layout.typingAnimator.isRunning()),
                "unsupported_layout_state");
        Rect visible = new Rect();
        require(cell.getGlobalVisibleRect(visible), "hidden_cell");
        int[] location = new int[2];
        cell.getLocationOnScreen(location);
        float originX = location[0] + cell.getTextX();
        float originY = location[1] + cell.getTextY() + cell.getPaddingTop();
        JSONArray targets = new JSONArray();
        for (int i = 0; i < layout.blocks.size(); i++) {
            RichMessageLayout.RichBlock block = layout.blocks.get(i);
            require(block.currVisible && block.parentDetails == null && block.padding.equals(new Rect()),
                    "unsupported_block_padding_or_visibility");
            if (block instanceof RichMessageLayout.RichButtonRowBlock) {
                RichMessageLayout.RichButton[] buttons = (RichMessageLayout.RichButton[]) field(block, "buttons");
                for (int j = 0; j < buttons.length; j++) {
                    RichMessageLayout.RichButton button = buttons[j];
                    float top = block.currY + Math.round((block.getHeight() - button.getHeight()) / 2f);
                    targets.put(target("row", i, j, button,
                            new RectF(button.x, top, button.x + button.width, top + button.getHeight()),
                            originX, originY, visible));
                }
            } else if (block.getClass() == RichMessageLayout.RichTextBlock.class) {
                RichMessageLayout.Text text = ((RichMessageLayout.RichTextBlock) block).text;
                if (text.layout.getText() instanceof Spanned) {
                    Spanned spanned = (Spanned) text.layout.getText();
                    RichMessageLayout.RichButtonSpan[] spans = spanned.getSpans(0, spanned.length(), RichMessageLayout.RichButtonSpan.class);
                    for (int j = 0; j < spans.length; j++) {
                        RectF bounds = new RectF((RectF) field(spans[j], "bounds"));
                        targets.put(target("inline", i, j, spans[j].getButton(), bounds,
                                originX + text.getX(), originY + text.getY(), visible));
                    }
                }
            } else {
                throw new Unavailable("initial_experiment_requires_row_and_paragraph");
            }
        }
        require(targets.length() == 2, "initial_experiment_requires_two_targets");
        return new JSONObject().put("available", true).put("targets", targets)
                .put("cell_origin", new JSONArray().put(location[0]).put(location[1]))
                .put("text_origin", new JSONArray().put(cell.getTextX()).put(cell.getTextY()))
                .put("cell_padding_top", cell.getPaddingTop()).put("visible_cell", rect(new RectF(visible)));
    }

    private void sample(View observed) {
        posted = false;
        if (decor != observed) return;
        lastSample = SystemClock.uptimeMillis();
        try {
            publish(observe(observed));
        } catch (Exception failure) {
            try {
                // Only locally authored reason codes; reflective/platform failures omit messages.
                String reason = failure instanceof Unavailable ? failure.getMessage() : "observation_unavailable";
                publish(new JSONObject().put("available", false).put("reason", reason));
            } catch (Exception ignored) {}
        }
    }

    private void detach() {
        if (decor != null && listener != null && decor.getViewTreeObserver().isAlive()) {
            decor.getViewTreeObserver().removeOnDrawListener(listener);
        }
        decor = null;
        listener = null;
        posted = false;
        try { publish(new JSONObject().put("available", false).put("reason", "activity_paused")); }
        catch (Exception ignored) {}
    }

    @Override public void onActivityResumed(Activity activity) {
        if (!(activity instanceof LaunchActivity)) return;
        detach();
        decor = activity.getWindow().getDecorView();
        final View observed = decor;
        listener = () -> {
            if (posted) return;
            long remaining = 200 - (SystemClock.uptimeMillis() - lastSample);
            if (remaining > 0) {
                // Do not lose a final quiet frame merely because its draw was throttled.
                if (!redrawScheduled) {
                    redrawScheduled = true;
                    observed.postDelayed(() -> {
                        redrawScheduled = false;
                        if (decor == observed) observed.invalidate();
                    }, remaining);
                }
            } else {
                posted = true;
                // OnDrawListener precedes drawing; posting observes populated span bounds after it.
                observed.post(() -> sample(observed));
            }
        };
        decor.getViewTreeObserver().addOnDrawListener(listener);
        decor.invalidate();
    }
    @Override public void onActivityPaused(Activity activity) { if (activity instanceof LaunchActivity) detach(); }
    @Override public void onActivityCreated(Activity activity, Bundle state) {}
    @Override public void onActivityStarted(Activity activity) {}
    @Override public void onActivityStopped(Activity activity) {}
    @Override public void onActivitySaveInstanceState(Activity activity, Bundle state) {}
    @Override public void onActivityDestroyed(Activity activity) {}
}
