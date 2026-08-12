"""
Terminal Output Module
=======================

This module provides the ability to print GeneratedTextIUs to the terminal.
"""

import retico_core
import threading
from retico_core.text import GeneratedTextIU

from retico_ollama.ollama import ResponseEndIU


class TerminalOutputModule(retico_core.AbstractConsumingModule):
    """Prints GeneratedTextIUs to terminal token by token."""

    @staticmethod
    def name():
        return "Terminal Output Module"

    @staticmethod
    def description():
        return "Prints Ollama responses to terminal."

    @staticmethod
    def input_ius():
        return [GeneratedTextIU, ResponseEndIU]

    def __init__(self):
        super().__init__()
        self.started = False

    def reset(self):
        self.started = False

    ##Make space inbetween words @fixit
    def process_update(self, update_message):
        for iu, ut in update_message:

            if isinstance(iu, ResponseEndIU):
                self.started = False
                print()
                continue

            if ut == retico_core.UpdateType.COMMIT:
                if not self.started:
                    print("AI:", end=" ", flush=True)
                    self.started = True

                print(iu.payload, end=" ", flush=True)
