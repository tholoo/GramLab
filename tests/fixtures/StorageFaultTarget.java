// Original fixture for the external debugger helper; no client-derived code.
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.file.Files;
import java.nio.file.Path;

public final class StorageFaultTarget {
    static Path destination;

    static void persist(int id) throws Exception {
        Files.writeString(destination, Integer.toString(id));
    }

    public static void main(String[] arguments) throws Exception {
        destination = Path.of(arguments[0]);
        BufferedReader input = new BufferedReader(new InputStreamReader(System.in));
        System.out.println("ready");
        for (String line; (line = input.readLine()) != null;) {
            if (line.equals("send")) {
                new Thread(() -> {
                    try {
                        persist(42);
                        System.out.println("stored");
                    } catch (Exception failure) {
                        throw new RuntimeException(failure);
                    }
                }, "storageQueue_0").start();
            } else if (line.equals("ping")) {
                System.out.println("alive");
            }
        }
    }
}
