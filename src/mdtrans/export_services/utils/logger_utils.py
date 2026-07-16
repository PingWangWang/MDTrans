import logging
import os

global_gui_callback = None

def set_gui_log_callback(callback):
    global global_gui_callback
    global_gui_callback = callback

class GuiLogHandler(logging.Handler):
    def emit(self, record):
        if global_gui_callback:
            message = self.format(record)
            global_gui_callback(message)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Add Dify plugin logger handler if LOAD_FROM_DIFY_PLUGIN is set to "1" in main.py
    if os.environ.get("LOAD_FROM_DIFY_PLUGIN") == "1":
        from dify_plugin.config.logger_format import plugin_logger_handler  # noqa: PLC0415

        logger.addHandler(plugin_logger_handler)

    # Add stdio handler
    stdio_handler = logging.StreamHandler()
    stdio_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    stdio_handler.setFormatter(stdio_formatter)
    logger.addHandler(stdio_handler)
    
    # Add GUI log handler if callback is available
    if global_gui_callback:
        gui_handler = GuiLogHandler()
        gui_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        gui_handler.setFormatter(gui_formatter)
        logger.addHandler(gui_handler)

    return logger
