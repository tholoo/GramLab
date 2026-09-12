// SPDX-License-Identifier: GPL-2.0-or-later
package org.telegram.gramlab;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;

/** Isolated launcher for the actual APK's bridge and serializer probe. */
public final class MediaGroupsCodecProbe {
    private MediaGroupsCodecProbe() {}

    public static void main(String[] args) throws Exception {
        Class<?> probe = Class.forName("org.telegram.gramlab.BridgeProbe");
        Method main = probe.getMethod("main", String[].class);
        try {
            main.invoke(null, (Object) args);
        } catch (InvocationTargetException failure) {
            Throwable cause = failure.getCause();
            if (cause instanceof Exception) {
                throw (Exception) cause;
            }
            if (cause instanceof Error) {
                throw (Error) cause;
            }
            throw failure;
        }
    }
}
