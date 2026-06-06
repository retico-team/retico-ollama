"""
Talon Module
=======================

This module provides the ability to add Indexing Units to the Talon Voice Command System.
It is designed to be used with ReTico, allowing a more efficient, powerful, use of Talon.
"""

# Imports

import threading
from retico_core.text import TextIU
import ollama
import retico_core
from retico_core.text import SpeechRecognitionIU, GeneratedTextIU


class OllamaModule(retico_core.AbstractModule):
    """
    @fixit
    """

    def __init__(
        self,
        model="llama3.1",
        system_prompt=None,
        num_ctx=2048,
        repeat_last_n=64,
        repeat_penalty=1.1,
        temperature=0.8,
        seed=0,
        stop=None,
        num_predict=-1,
        draft_num_predict=4,
        top_k=40,
        top_p=0.9,
        min_p=0.0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.model = model
        self.system_prompt = system_prompt
        self.options = {
            "num_ctx": num_ctx,
            "repeat_last_n": repeat_last_n,
            "repeat_penalty": repeat_penalty,
            "temperature": temperature,
            "seed": seed,
            "num_predict": num_predict,
            "draft_num_predict": draft_num_predict,
            "top_k": top_k,
            "top_p": top_p,
            "min_p": min_p,
        }
        if stop is not None:
            self.options["stop"] = stop

        self._lock = threading.Lock()
        self._ollama_thread_active = False
        self.latest_input_iu = None

    @staticmethod
    def name():
        return "Ollama Module"

    @staticmethod
    def description():
        return "@fixit"

    @staticmethod
    def input_ius():
        return [SpeechRecognitionIU, GeneratedTextIU, TextIU]

    @staticmethod
    def output_iu():
        return GeneratedTextIU

    def process_update(self, update_message):
        for iu, ut in update_message:
            if ut == retico_core.UpdateType.ADD:
                self.current_input.append(iu)
                self.latest_input_iu = iu
            elif ut == retico_core.UpdateType.REVOKE:
                self.revoke(iu)
            elif ut == retico_core.UpdateType.COMMIT:
                self.commit(iu)

    def ollama_response(self):
        while self._ollama_thread_active:
            with self._lock:
                if not self.current_input:
                    continue
                prompt = " ".join(iu.text for iu in self.current_input if iu.text)
                self.current_input = []

            if not prompt:
                continue

            accumulated_response = ""

            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                system=self.system_prompt,
                options=self.options,
                stream=True,
            )

            for piece in response:
                if not self._ollama_thread_active:
                    break
                token = piece.get("response", "")
                accumulated_response += token
                completed = piece.get("done", False)

                if not token and not completed:
                    continue

                um, new_tokens = retico_core.text.get_text_increment(
                    self, accumulated_response
                )

                for i, token in enumerate(new_tokens):
                    output_iu = self.create_iu(self.latest_input_iu)
                    token = piece["response"]
                    is_done = piece["done"]
                    eou = i == len(new_tokens) - 1 and is_done
                    output_iu.payload = token
                    self.current_output.append(output_iu)
                    um.add_iu(output_iu, retico_core.UpdateType.ADD)

                if completed:
                    for iu in self.current_output:
                        self.commit(iu)
                        um.add_iu(iu, retico_core.UpdateType.COMMIT)
                    self.current_output = []

                self.latest_input_iu = None
                self.append(um)

    def prepare_run(self):
        self._ollama_thread_active = True
        threading.Thread(target=self.ollama_response).start()

    def shutdown(self):
        self._ollama_thread_active = False
