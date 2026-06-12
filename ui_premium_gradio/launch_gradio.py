import os, sys

# Ensure local package import works when launched as a script
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_DIR)

from ui_premium_gradio.app_ui import create_app



def main():
    demo = create_app()
    demo.queue()

    preferred_port = int(os.getenv("GRADIO_SERVER_PORT", "7861"))
    try:
        demo.launch(server_name="127.0.0.1", server_port=preferred_port, show_error=True)
    except OSError:
        fallback_port = preferred_port + 1
        demo.launch(server_name="127.0.0.1", server_port=fallback_port, show_error=True)


if __name__ == "__main__":
    main()

