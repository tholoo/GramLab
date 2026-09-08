// SPDX-License-Identifier: GPL-2.0-or-later
// Fixture-only capability check. No production implementation or fallback.
#define _GNU_SOURCE 1
#include <errno.h>
#include <fcntl.h>
#include <jni.h>
#include <stdio.h>
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>

static int path_bytes(JNIEnv *env, jbyteArray value, char output[4096]) {
    if (value == NULL) return EINVAL;
    jsize size = (*env)->GetArrayLength(env, value);
    if (size <= 0 || size >= 4096) return EINVAL;
    (*env)->GetByteArrayRegion(env, value, 0, size, (jbyte *) output);
    if ((*env)->ExceptionCheck(env)) return EINVAL;
    if (memchr(output, 0, (size_t) size) != NULL) return EINVAL;
    output[size] = 0;
    return 0;
}

JNIEXPORT jint JNICALL
Java_org_telegram_gramlab_RenameNoReplaceProbe_renameNoReplace(
        JNIEnv *env, jclass type, jbyteArray source, jbyteArray destination) {
    (void) type;
    char old_path[4096], new_path[4096];
    int invalid = path_bytes(env, source, old_path);
    if (invalid != 0) return invalid;
    invalid = path_bytes(env, destination, new_path);
    if (invalid != 0) return invalid;
    // API26 libc has syscall(); the newer libc renameat2 symbol is not required.
    // Kernel, seccomp and filesystem support must be established in the target process.
    long result = syscall(SYS_renameat2, AT_FDCWD, old_path, AT_FDCWD,
                          new_path, RENAME_NOREPLACE);
    int failure = errno;
    return result == 0 ? 0 : failure;
}
