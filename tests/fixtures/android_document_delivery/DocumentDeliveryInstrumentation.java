// SPDX-License-Identifier: GPL-2.0-or-later
package org.telegram.gramlab;

import android.app.Application;
import android.app.Instrumentation;
import android.os.Bundle;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import org.json.JSONObject;
import org.telegram.messenger.ApplicationLoader;

/** Actual target-package process; deliberately suppresses the application's full onCreate. */
public final class DocumentDeliveryInstrumentation extends Instrumentation {
    private final CountDownLatch attached=new CountDownLatch(1);
    private Application application;
    private String mode;
    @Override public void onCreate(Bundle arguments) {
        mode=arguments==null?null:arguments.getString("mode");
        start();
    }
    @Override public void callApplicationOnCreate(Application value) {
        application=value;
        // No accounts/native_init/full lifecycle. Ticket105 separately exercises the real UI.
        attached.countDown();
    }
    @Override public void onStart() {
        Bundle retained=new Bundle();int status=2;
        try {
            DocumentDeliveryProbe.startDiagnostics(getTargetContext(),mode);
            DocumentDeliveryProbe.diagnosticStep="instrumentation.attachment_wait";
            if(!attached.await(10,TimeUnit.SECONDS)||!(application instanceof ApplicationLoader))
                throw new IllegalStateException("original_application_unavailable");
            if("rename".equals(mode)) {
                DocumentDeliveryProbe.diagnosticStep="instrumentation.rename_library";
                System.load(new java.io.File(getContext().getApplicationInfo().nativeLibraryDir,"libdocument_rename_probe.so").toString());
            }
            JSONObject result=DocumentDeliveryProbe.instrumented((ApplicationLoader)application,getTargetContext(),mode);
            String encoded=result.toString();if(encoded.getBytes(java.nio.charset.StandardCharsets.UTF_8).length>1024*1024)throw new IllegalStateException("result_bound");
            retained.putString("document_delivery",encoded);status=result.getInt("failed")==0?0:1;
            DocumentDeliveryProbe.diagnosticCheckpoint("instrumentation_complete",null);
        } catch(Throwable error) {
            try {
                JSONObject failure=DocumentDeliveryProbe.diagnosticFailure(error,"instrumentation_initialization");
                DocumentDeliveryProbe.diagnosticCheckpoint("instrumentation_failure",failure);
                retained.putString("document_delivery",failure.toString());
            } catch(Exception ignored) {retained.putString("document_delivery","{\"schema\":1}");}
        } finally {DocumentDeliveryProbe.stopDiagnostics();finish(status,retained);}
    }
}
