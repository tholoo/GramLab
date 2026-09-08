// SPDX-License-Identifier: GPL-2.0-or-later
package org.telegram.gramlab;

import android.graphics.Canvas;
import android.graphics.Matrix;
import android.graphics.RectF;
import java.io.File;
import java.io.FileOutputStream;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import org.json.JSONArray;
import org.json.JSONObject;

/** Actual Android Matrix/Canvas regression for the private cell-local normalization helper. */
public final class RichButtonMatrixProbe {
    private static final float EPSILON = 0.001f;
    private static Method begin;
    private static Method end;
    private static Method bounds;
    private static Object cellA;
    private static Object cellB;
    private static File output;
    private static int passed;
    private static int failed;

    private RichButtonMatrixProbe() {}
    private interface Case { void run() throws Exception; }

    private static void require(boolean value, String code) {
        if (!value) throw new AssertionError(code);
    }

    private static Object allocate(String className) throws Exception {
        Class<?> unsafeClass = Class.forName("sun.misc.Unsafe");
        Field singleton = unsafeClass.getDeclaredField("theUnsafe");
        singleton.setAccessible(true);
        Object unsafe = singleton.get(null);
        return unsafeClass.getMethod("allocateInstance", Class.class)
                .invoke(unsafe, Class.forName(className));
    }

    private static RectF normalized(Object cell, Canvas canvas, RectF local) throws Exception {
        return (RectF) bounds.invoke(null, cell, canvas, local);
    }

    private static void assertRect(RectF actual, float left, float top, float right, float bottom) {
        require(actual != null, "missing_rect");
        require(Math.abs(actual.left - left) <= EPSILON, "left");
        require(Math.abs(actual.top - top) <= EPSILON, "top");
        require(Math.abs(actual.right - right) <= EPSILON, "right");
        require(Math.abs(actual.bottom - bottom) <= EPSILON, "bottom");
    }

    private static Canvas canvas(Matrix outer) {
        Canvas canvas = new Canvas();
        canvas.setMatrix(outer);
        return canvas;
    }

    private static Matrix outer(float tx, float ty, float sx, float sy) {
        Matrix matrix = new Matrix();
        matrix.postTranslate(tx, ty);
        matrix.postScale(sx, sy);
        return matrix;
    }

    private static RectF exercise(Matrix outer) throws Exception {
        Canvas canvas = canvas(outer);
        begin.invoke(null, cellA, canvas);
        try {
            canvas.translate(11, 17);
            canvas.scale(2, 3);
            return normalized(cellA, canvas, new RectF(1, 2, 5, 7));
        } finally {
            end.invoke(null, cellA);
        }
    }

    private static void run(String name, Case test) throws Exception {
        JSONObject record = new JSONObject().put("schema", 1).put("case", name);
        try {
            test.run();
            record.put("passed", true);
            passed++;
        } catch (Exception | AssertionError failure) {
            record.put("passed", false).put("failure_class", failure.getClass().getSimpleName());
            if (failure instanceof AssertionError) record.put("assertion", failure.getMessage());
            failed++;
        }
        try (FileOutputStream stream = new FileOutputStream(new File(output, name + ".json"))) {
            stream.write(record.toString(2).getBytes(StandardCharsets.UTF_8));
        }
        System.out.println(record);
    }

    @SuppressWarnings("deprecation")
    public static void main(String[] arguments) throws Exception {
        if (arguments.length != 1) throw new IllegalArgumentException("OUTPUT_DIRECTORY");
        output = new File(arguments[0]);
        if (output.exists() || !output.mkdir()) throw new IllegalArgumentException("fresh output required");
        Class<?> observer = Class.forName("org.telegram.gramlab.GramLabButtonObserver");
        Class<?> cell = Class.forName("org.telegram.ui.Cells.ChatMessageCell");
        begin = observer.getMethod("beginCellDraw", cell, Canvas.class);
        end = observer.getMethod("endCellDraw", cell);
        bounds = observer.getDeclaredMethod("cellLocalBounds", cell, Canvas.class, RectF.class);
        bounds.setAccessible(true);
        cellA = allocate(cell.getName());
        cellB = allocate(cell.getName());

        run("outer_basis_invariant", () -> {
            RectF identity = exercise(outer(0, 0, 1, 1));
            RectF translated = exercise(outer(137, -53, 1, 1));
            RectF scaled = exercise(outer(19, 31, 1.75f, 0.625f));
            assertRect(identity, 13, 23, 21, 38);
            assertRect(translated, 13, 23, 21, 38);
            assertRect(scaled, 13, 23, 21, 38);
            JSONObject evidence = new JSONObject().put("cell_local", rect(identity))
                    .put("reference_only", true)
                    .put("expected_screen_origin", new JSONArray().put(29).put(41))
                    .put("expected_screen_bounds", new JSONArray().put(42).put(64).put(50).put(79));
            write("outer-basis-evidence.json", evidence);
        });
        run("missing_and_mismatched_context", () -> {
            Canvas canvas = canvas(outer(0, 0, 1, 1));
            require(normalized(cellA, canvas, new RectF(0, 0, 2, 2)) == null, "missing_context");
            begin.invoke(null, cellA, canvas);
            try {
                require(normalized(cellB, canvas, new RectF(0, 0, 2, 2)) == null, "mismatched_cell");
            } finally { end.invoke(null, cellA); }
        });
        run("nested_context_restoration", () -> {
            Canvas canvas = canvas(outer(83, 47, 1.25f, 0.75f));
            begin.invoke(null, cellA, canvas);
            try {
                canvas.translate(10, 20);
                assertRect(normalized(cellA, canvas, new RectF(0, 0, 4, 5)), 10, 20, 14, 25);
                begin.invoke(null, cellA, canvas);
                try {
                    canvas.translate(7, 9);
                    assertRect(normalized(cellA, canvas, new RectF(0, 0, 4, 5)), 7, 9, 11, 14);
                } finally { end.invoke(null, cellA); }
                assertRect(normalized(cellA, canvas, new RectF(0, 0, 4, 5)), 17, 29, 21, 34);
            } finally { end.invoke(null, cellA); }
        });
        run("mismatched_end_clears_context", () -> {
            Canvas canvas = new Canvas();
            begin.invoke(null, cellA, canvas);
            end.invoke(null, cellB);
            require(normalized(cellA, canvas, new RectF(0, 0, 2, 2)) == null, "context_not_cleared");
        });
        run("noninvertible_entry", () -> {
            Canvas canvas = new Canvas();
            canvas.scale(0, 1);
            begin.invoke(null, cellA, canvas);
            try { require(normalized(cellA, canvas, new RectF(0, 0, 2, 2)) == null, "accepted_singular"); }
            finally { end.invoke(null, cellA); }
        });
        run("empty_rectangle", () -> {
            Canvas canvas = new Canvas();
            begin.invoke(null, cellA, canvas);
            try { require(normalized(cellA, canvas, new RectF(2, 2, 2, 5)) == null, "accepted_empty"); }
            finally { end.invoke(null, cellA); }
        });
        run("nonfinite_first_corner", () -> {
            Canvas canvas = new Canvas();
            begin.invoke(null, cellA, canvas);
            try {
                Matrix projective = new Matrix();
                projective.setValues(new float[] {1, 0, 1, 0, 1, 1, 1, 1, 0});
                canvas.setMatrix(projective);
                float[] mapped = {0, 0, 2, 0, 2, 2, 0, 2};
                canvas.getMatrix().mapPoints(mapped);
                JSONArray actual = new JSONArray();
                boolean nonfinite = false;
                for (float coordinate : mapped) {
                    actual.put(Float.isFinite(coordinate) ? coordinate : Double.toString(coordinate));
                    nonfinite |= !Float.isFinite(coordinate);
                }
                write("nonfinite-first-corner-premise.json", new JSONObject()
                        .put("schema", 1).put("mapped_corners", actual)
                        .put("first_corner_nonfinite", !Float.isFinite(mapped[0]) || !Float.isFinite(mapped[1])));
                require(nonfinite, "fixture_did_not_produce_nonfinite");
                require(!Float.isFinite(mapped[0]) || !Float.isFinite(mapped[1]),
                        "fixture_nonfinite_not_in_first_corner");
                require(normalized(cellA, canvas, new RectF(0, 0, 2, 2)) == null,
                        "accepted_nonfinite_first_corner");
            } finally { end.invoke(null, cellA); }
        });

        JSONObject summary = new JSONObject().put("schema", 1).put("passed", passed)
                .put("failed", failed).put("total", passed + failed);
        write("summary.json", summary);
        System.out.println(summary);
        System.exit(failed == 0 ? 0 : 1);
    }

    private static JSONArray rect(RectF value) throws Exception {
        return new JSONArray().put(value.left).put(value.top).put(value.right).put(value.bottom);
    }

    private static void write(String name, JSONObject value) throws Exception {
        byte[] bytes = value.toString(2).getBytes(StandardCharsets.UTF_8);
        require(bytes.length <= 65536, "output_too_large");
        try (FileOutputStream stream = new FileOutputStream(new File(output, name))) {
            stream.write(bytes);
        }
    }
}
