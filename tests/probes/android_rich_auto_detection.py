"""Run the shared strict native message codec for automatic-detection nodes."""

from android_guest import main
from android_message_codec import probe

if __name__ == "__main__":
    main(probe)
