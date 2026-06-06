import retico_core
from retico_core.debug import DebugModule
from retico_core.text import TextIU
from retico_keyboard import KeyboardModule
from retico_ollama import OllamaModule

# Modules
keyboard = KeyboardModule()
ollama = OllamaModule(model="llama3.1")
debug = DebugModule()

# Wire
keyboard.subscribe(ollama)
ollama.subscribe(debug)

# Run
keyboard.run()
ollama.run()
debug.run()

print("Network is running")

input()

keyboard.stop()
ollama.stop()
debug.stop()
