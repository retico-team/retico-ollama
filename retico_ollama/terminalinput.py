"""
Terminal Input Module
=======================

This module provides the ability to grab input from the terminal and emit TextIUs into the ReTico pipeline.
"""

import retico_core
import threading
from retico_core.text import TextIU


class TerminalInputModule(retico_core.AbstractProducingModule):
    """Reads input from terminal and emits TextIUs into the pipeline."""

    @staticmethod
    def name():
        return "Terminal Input Module"

    @staticmethod
    def description():
        return "Reads input from terminal and emits TextIUs."

    @staticmethod
    def input_ius():
        return []

    @staticmethod
    def output_iu():
        return TextIU

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._reading = False

    def read_loop(self):
        while self._reading:
            try:
                text = input().strip()
            except EOFError:
                break
            if not text:
                continue
            print(f"You: {text}")
            output_iu = self.create_iu()
            output_iu.payload = text
            um = retico_core.UpdateMessage()
            um.add_iu(output_iu, retico_core.UpdateType.ADD)
            self.append(um)

            um = retico_core.UpdateMessage()
            um.add_iu(output_iu, retico_core.UpdateType.COMMIT)
            self.append(um)

    def process_update(self, update_message):
        pass

    def prepare_run(self):
        self._reading = True
        # daemon, so a thread blocked on input() doesn't keep the program alive
        threading.Thread(target=self.read_loop, daemon=True).start()

    def shutdown(self):
        self._reading = False
