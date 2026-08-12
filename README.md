# retico-ollama

A local module for incremental, streaming LLM responses using Ollama using the ReTiCo framework.

## Installation and Requirements
To use the module you first need to install the retico-core package:
* Install retico_core:
```pip install git+https://github.com/retico-team/retico-core.git```

Right after that, install the retico-ollama package:
* Install the retico-ollama:
```pip install git+https://github.com/retico-team/retico-ollama.git```

You will also need Ollama installed and running locally with your chosen module:
* Install Ollama on their official website
```https://ollama.com/download```

## Modules

### `OllamaModule`
Incrementally generate LLM responses from text input (typed or transcribed), streaming tokens as they are produced.

**Input options:** `keyboard`, `mic`

The `keyboard` input attempts to stream partial input as it's typed and pre-warms the model between strokes. In an attempt to reduce token production when long prompts are made.
Input `mic` waits for a commited speech-recognition result before generating.

#### Arguments:

* `model` (str): Ollama model to use, defaults to 'llama3.1'
* `mode` (str): Input mode, defaults to 'keyboard'
* `system_prompt` (str): Optional system prompt, defaults to 'None'
* `num_ctx` (int): Context size, defaults to '2048'
* `repeat_last_n`(int): Tokens to look back repetition, defaults to '64'
* `repeat_penalty` (float): Repetition penalty, defaults to '1.1'
* `temperature` (float): Sampling temperature, defaults to '0.8'
* `seed` (int): Random seed, defaults to '0'
* `stop`(str): Stop sequences, defaults to 'None'
* `num_predict` (int): Max tokens, '-1' for unlimited, defaults to '-1'
* `draft_num_predict` (int): control how many tokens a draft pass, defaults to 4
* `top_k`(int): Top-k sampling, defaults to 40
* `top_p`(float): Top-p sampling, defaults to 0.9
* `min_p`(float): Min-p sampling, defaults to 0.0
* `speculative_delay` (float): seconds between speculative generation, defaults to '1.5'
* `from_lang` (str): Source language to use, defaults to 'en'
* `to_lang` (str): Target language to use, defaults to 'de'

### `TerminalInputModule`
Reads line of text from terminal and emits them as TextIU into the pipeline. Used with OllamaModule 'keyboard' module to allow the user to type on the terminal.

### `TerminalOutputModule`
Prints text from OllamaModule to the terminal token as they stream. Used for both 'keyboard' and 'mic' modes.

## Example Keyboard

```python
import retico_core
import time
from retico_ollama import OllamaModule, TerminalInputModule, TerminalOutputModule

terminal_in = TerminalInputModule()
ollama = OllamaModule(model="llama3.1")
terminal_out = TerminalOutputModule()

terminal_in.subscribe(ollama)
ollama.subscribe(terminal_out)

terminal_in.run()
ollama.run()
terminal_out.run()

print("Network is running")
# input()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    terminal_in.stop()
    ollama.stop()
    terminal_out.stop()
```

## Example Microphone

```python
import retico_core
import time
from retico_core.audio import MicrophoneModule
from retico_core.debug import DebugModule
from retico_whisperasr import WhisperASRModule
from retico_ollama import OllamaModule, TerminalOutputModule

mic = MicrophoneModule()
asr = WhisperASRModule()
ollama = OllamaModule(model="llama3.1", mode="mic")
terminal_out = TerminalOutputModule()

mic.subscribe(asr)
asr.subscribe(ollama)
ollama.subscribe(terminal_out)

mic.run()
asr.run()
ollama.run()
terminal_out.run()

print("Network is running")
# input()

try:
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    mic.stop()
    asr.stop()
    ollama.stop()
    terminal_out.stop()
```
