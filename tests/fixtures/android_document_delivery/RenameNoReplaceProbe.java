// SPDX-License-Identifier: GPL-2.0-or-later
package org.telegram.gramlab;

import android.system.OsConstants;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardOpenOption;
import java.util.Arrays;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import org.json.JSONArray;
import org.json.JSONObject;

/** Executes the real syscall on the original app external-files mount. */
public final class RenameNoReplaceProbe {
    private RenameNoReplaceProbe() {}
    private static native int renameNoReplace(byte[] source,byte[] destination);
    private static byte[] path(File file) {return file.toString().getBytes(StandardCharsets.UTF_8);}
    private static void require(boolean value,String name) {if(!value)throw new AssertionError(name);}
    private static void write(File file,byte[] bytes) throws Exception {Files.write(file.toPath(),bytes,StandardOpenOption.CREATE_NEW);}
    private static boolean matches(File file,byte[] bytes) throws Exception {return Arrays.equals(Files.readAllBytes(file.toPath()),bytes);}
    private interface Operation {int rename(byte[] source,byte[] destination) throws Exception;}
    public static void run(File parent,JSONArray observations) throws Exception {
        run(parent,observations,RenameNoReplaceProbe::renameNoReplace,"fixture_syscall");
    }
    public static void runProduction(File parent,JSONArray observations) throws Exception {
        java.lang.reflect.Method method=org.telegram.messenger.FileLoader.class.getDeclaredMethod("nativeRenameDocument",byte[].class,byte[].class);
        method.setAccessible(true);
        run(parent,observations,(source,destination)->(Integer)method.invoke(null,source,destination),"original_FileLoader_JNI");
    }
    private static void run(File parent,JSONArray observations,Operation operation,String implementation) throws Exception {
        JSONObject result=new JSONObject().put("case",implementation.equals("fixture_syscall")?"external_rename_noreplace":"production_document_rename")
                .put("implementation",implementation);observations.put(result);
        require(parent!=null,"external_root_unavailable");
        result.put("external_root",parent.getCanonicalPath()).put("root_exists",parent.exists())
                .put("root_is_directory",parent.isDirectory()).put("root_can_write",parent.canWrite())
                .put("syscall","renameat2").put("flags",1).put("path_encoding","UTF-8");
        File directory=new File(parent,"document-delivery-rename-probe");
        DocumentDeliveryProbe.diagnosticStep="rename.create_directory";Files.createDirectory(directory.toPath());
        byte[] a=new byte[16384],b=new byte[16384];Arrays.fill(a,(byte)0x31);Arrays.fill(b,(byte)0xa7);
        File source=new File(directory,"source.bin"),destination=new File(directory,"destination.bin");write(source,a);
        DocumentDeliveryProbe.diagnosticStep="rename.absent";
        int absent=operation.rename(path(source),path(destination));result.put("absent_errno",absent);
        require(absent==0&&!source.exists()&&matches(destination,a),"absent_complete_publication");
        write(source,b);DocumentDeliveryProbe.diagnosticStep="rename.occupied";
        int occupied=operation.rename(path(source),path(destination));result.put("occupied_errno",occupied);
        require(occupied==OsConstants.EEXIST&&matches(source,b)&&matches(destination,a),"occupied_unchanged");
        DocumentDeliveryProbe.diagnosticStep="rename.invalid_paths";
        JSONArray invalid=new JSONArray();
        for(byte[] value:new byte[][]{null,new byte[0],new byte[]{'a',0,'b'},new byte[4096]}) {
            int sourceError=operation.rename(value,path(destination)),destinationError=operation.rename(path(source),value);
            invalid.put(new JSONArray().put(sourceError).put(destinationError));
            require(sourceError==OsConstants.EINVAL&&destinationError==OsConstants.EINVAL,"invalid_path_rejected");
        }
        result.put("invalid_errno_pairs",invalid);require(matches(source,b)&&matches(destination,a),"invalid_paths_no_mutation");
        DocumentDeliveryProbe.diagnosticStep="rename.missing_source";
        File missing=new File(directory,"missing.bin"),unused=new File(directory,"unused.bin");
        int absentSource=operation.rename(path(missing),path(unused));result.put("missing_source_errno",absentSource);
        require(absentSource==OsConstants.ENOENT&&!unused.exists(),"missing_source_no_publication");
        DocumentDeliveryProbe.diagnosticStep="rename.unicode";
        File unicodeSource=new File(directory,".source-\u00e9-\ud83e\uddea.bin"),unicodeTarget=new File(directory,".target-\u0641-\ud83d\ude80.bin");write(unicodeSource,b);
        int unicode=operation.rename(path(unicodeSource),path(unicodeTarget));result.put("unicode_errno",unicode)
                .put("unicode_destination",unicodeTarget.getName());
        require(unicode==0&&!unicodeSource.exists()&&matches(unicodeTarget,b),"unicode_complete_publication");
        JSONArray races=new JSONArray();result.put("races",races);
        for(int index=0;index<8;index++) {
            DocumentDeliveryProbe.diagnosticStep="rename.race_"+index;
            File left=new File(directory,"left-"+index),right=new File(directory,"right-"+index),target=new File(directory,"winner-"+index);
            write(left,a);write(right,b);CountDownLatch ready=new CountDownLatch(2),start=new CountDownLatch(1);
            int[] codes={-1,-1};Throwable[] failures=new Throwable[2];Thread[] threads=new Thread[2];
            File[] sources={left,right};
            for(int side=0;side<2;side++){final int slot=side;threads[side]=new Thread(()->{
                try{ready.countDown();if(!start.await(5,TimeUnit.SECONDS))throw new AssertionError("race_start_timeout");
                    codes[slot]=operation.rename(path(sources[slot]),path(target));}
                catch(Throwable error){failures[slot]=error;}
            },"rename-contender-"+side);threads[side].start();}
            try{require(ready.await(5,TimeUnit.SECONDS),"race_ready_timeout");}
            finally{start.countDown();for(Thread thread:threads)thread.join(5000);}
            races.put(new JSONObject().put("left_errno",codes[0]).put("right_errno",codes[1]));
            require(!threads[0].isAlive()&&!threads[1].isAlive()&&failures[0]==null&&failures[1]==null,"race_threads_complete");
            require((codes[0]==0&&codes[1]==OsConstants.EEXIST)||(codes[1]==0&&codes[0]==OsConstants.EEXIST),"race_single_winner");
            int winner=codes[0]==0?0:1;require(!sources[winner].exists()&&matches(sources[1-winner],winner==0?b:a)
                    &&matches(target,winner==0?a:b),"race_complete_winner_and_preserved_loser");
        }
        result.put("complete",true);
    }
}
