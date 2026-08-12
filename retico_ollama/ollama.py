"""
Ollama Module
=======================

This module provides the ability to add Indexing Units to the Ollama LLM.
It is designed to be used with ReTico, allowing a more efficient, powerful, use of Ollama.
"""

# Imports

import threading
from retico_core.text import TextIU
import ollama
from retico_core import abstract
import retico_core
from retico_core.text import SpeechRecognitionIU, GeneratedTextIU


class OllamaModule(retico_core.AbstractModule):
    """
    @fixit
    """

    def __init__(
        self,
        model="llama3.1",
        mode="keyboard",
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
        speculative_delay=1.5,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.model = model
        self.mode = mode
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
        self.speculative_delay = speculative_delay
        self._speculative_thread = None
        self._cancel_speculative = threading.Event()
        self._last_speculated_prompt = None
        self._input_ready = threading.Event()
        self._conversation_context = None
        self._speculative_context = None

    @staticmethod
    def name():
        return "Ollama Module"

    @staticmethod
    def description():
        return "@fixit"

    @staticmethod
    def input_ius():
        return [SpeechRecognitionIU, TextIU]

    @staticmethod
    def output_iu():
        return GeneratedTextIU

    def _start_speculative(self):
        with self._lock:
            if not self.current_input:
                return
            partial_prompt = " ".join(iu.text for iu in self.current_input if iu.text)

        if not partial_prompt:
            return

        # skip if nothing new was added since last speculation
        if partial_prompt == self._last_speculated_prompt:
            return

        # cancel any existing speculative thread
        self._cancel_speculative.set()
        if self._speculative_thread and self._speculative_thread.is_alive():
            self._speculative_thread.join(timeout=0.5)
        self._cancel_speculative.clear()

        self._last_speculated_prompt = partial_prompt

        self._speculative_thread = threading.Thread(
            target=self._speculative_response, args=(partial_prompt,)
        )
        self._speculative_thread.start()

    def _speculative_response(self, partial_prompt):
        """Runs speculative generation privately — output not sent downstream."""
        try:
            response = ollama.generate(
                model=self.model,
                prompt=partial_prompt,
                system=self.system_prompt,
                options=self.options,
                context=self._conversation_context,
                stream=False,
            )

            if not self._cancel_speculative.is_set():
                self._speculative_context = response["context"]

        except Exception as e:
            print(f"[OllamaModule] Speculative error: {e}")

    def _speculation_heartbeat(self):
        """Fires every speculative_delay seconds and starts speculation if new input."""
        while self._ollama_thread_active:
            threading.Event().wait(self.speculative_delay)
            if not self._ollama_thread_active:
                break
            self._start_speculative()

    def process_update(self, update_message):
        for iu, ut in update_message:

            if self.mode == "keyboard":
                if ut == retico_core.UpdateType.ADD:
                    self.current_input.append(iu)
                    self.latest_input_iu = iu
                elif ut == retico_core.UpdateType.REVOKE:
                    self.revoke(iu)
                    if iu in self.current_input:
                        self.current_input.remove(iu)
                    self._cancel_speculative.set()
                    self._speculative_context = None
                    self._last_speculated_prompt = None
                elif ut == retico_core.UpdateType.COMMIT:
                    self.commit(iu)
                    self._input_ready.set()
            elif self.mode == "mic":
                if ut == retico_core.UpdateType.COMMIT:
                    self.current_input.append(iu)
                    self.latest_input_iu = iu
                    self.commit(iu)
                    self._input_ready.set()

    def ollama_response(self):
        while self._ollama_thread_active:
            self._input_ready.wait(timeout=0.5)
            self._input_ready.clear()
            with self._lock:
                if not self.current_input:
                    continue
                prompt = " ".join(iu.text for iu in self.current_input if iu.text)
                self.current_input = []

            if not prompt:
                continue

            # cancel any speculative thread
            self._cancel_speculative.set()
            if self._speculative_thread and self._speculative_thread.is_alive():
                self._speculative_thread.join(timeout=0.5)
            self._cancel_speculative.clear()

            # revoke all speculative output before real response
            if self.current_output:
                um = retico_core.UpdateMessage()
                for iu in self.current_output:
                    um.add_iu(iu, retico_core.UpdateType.REVOKE)
                self.current_output = []
                self.append(um)

            accumulated_response = ""
            if (
                prompt == self._last_speculated_prompt
                and self._speculative_context is not None
            ):
                context_to_use = self._speculative_context
            else:
                context_to_use = self._conversation_context

            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                system=self.system_prompt,
                options=self.options,
                context=context_to_use,
                stream=True,
            )

            self._speculative_context = None
            self._last_speculated_prompt = None

            for piece in response:
                if not self._ollama_thread_active:
                    break
                token = piece.get("response", "")
                accumulated_response += token
                is_done = piece.get("done", False)

                if not token and not is_done:
                    continue

                um, new_tokens = retico_core.text.get_text_increment(
                    self, accumulated_response
                )

                for i, new_token in enumerate(new_tokens):
                    output_iu = self.create_iu(self.latest_input_iu)
                    output_iu.payload = new_token
                    self.current_output.append(output_iu)
                    um.add_iu(output_iu, retico_core.UpdateType.ADD)

                if is_done:
                    for iu in self.current_output:
                        self.commit(iu)
                        um.add_iu(iu, retico_core.UpdateType.COMMIT)
                        end_iu = ResponseEndIU(
                            creator=self, iuid=id(self), previous_iu=None
                        )

                    um.add_iu(end_iu, retico_core.UpdateType.ADD)
                    um.add_iu(end_iu, retico_core.UpdateType.COMMIT)
                    self.current_output = []
                    self._conversation_context = piece.get("context")

                self.latest_input_iu = None
                self.append(um)

    def prepare_run(self):
        self._ollama_thread_active = True
        threading.Thread(target=self.ollama_response).start()
        if self.mode == "keyboard":
            threading.Thread(target=self._speculation_heartbeat).start()

    def shutdown(self):
        self._ollama_thread_active = False
        self._cancel_speculative.set()


class ResponseEndIU(abstract.IncrementalUnit):
    @staticmethod
    def type():
        return "ResponseEndIU"
