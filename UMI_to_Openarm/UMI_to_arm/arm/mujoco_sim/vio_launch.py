"""Environment controls for the bundled Cyperstereo VIO viewer."""
import os


def vio_environment(show_viewer=False, environ=None):
    """Keep camera/pose settings; VIO_HEADLESS uses presence, even value '0'."""
    env = dict(os.environ if environ is None else environ)
    if show_viewer:
        env.pop("VIO_HEADLESS", None)
    else:
        env["VIO_HEADLESS"] = "1"
    return env
