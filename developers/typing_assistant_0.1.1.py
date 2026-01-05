import os
import sys
import time
import json
from pynput import keyboard

# --- CONFIGURATION ---
BASE_DIR = (
    os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__))
)

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DICTIONARY_FILE = os.path.join(BASE_DIR, "dictionary.txt")

# Load Configuration (Logging keys removed)
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

ACCEPT_KEY_NAME = config["accept_key"].lower()
ACCEPT_KEY = getattr(keyboard.Key, ACCEPT_KEY_NAME)
MAX_BUFFER = config["max_buffer"]
PRE_BACKSPACE_DELAY = config["replacement"]["pre_backspace_delay"]
POST_BACKSPACE_DELAY = config["replacement"]["post_backspace_delay"]
PER_CHAR_DELAY = config["replacement"]["per_character_delay"]
PRINT_BANNER = config["startup"]["print_banner"]
PRINT_DICT_COUNT = config["startup"]["print_dictionary_count"]

# Global State
word_buffer = ""
dictionary = {}
suggestion_active = False
current_suggestion = None
keyboard_controller = keyboard.Controller()

def load_dictionary():
    dictionary.clear()
    if not os.path.exists(DICTIONARY_FILE):
        print(f"[ERROR] {DICTIONARY_FILE} not found.")
        return
    try:
        with open(DICTIONARY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                plain, replacement = line.split("=", 1)
                dictionary[plain.strip().lower()] = replacement.strip()
        if PRINT_DICT_COUNT:
            print(f"[SUCCESS] Dictionary loaded: {len(dictionary)} entries.")
    except Exception as e:
        print(f"[ERROR] Failed to load dictionary: {e}")

def on_reload():
    print("\n[INFO] Reloading dictionary...")
    load_dictionary()

def replace_word(original, replacement):
    time.sleep(PRE_BACKSPACE_DELAY)
    for _ in range(len(original)):
        keyboard_controller.press(keyboard.Key.backspace)
        keyboard_controller.release(keyboard.Key.backspace)
    
    time.sleep(POST_BACKSPACE_DELAY)
    for char in replacement:
        keyboard_controller.press(char)
        keyboard_controller.release(char)
        if PER_CHAR_DELAY > 0:
            time.sleep(PER_CHAR_DELAY)

def on_press(key):
    global word_buffer, suggestion_active, current_suggestion
    
    if key == ACCEPT_KEY:
        if suggestion_active and current_suggestion:
            replace_word(word_buffer, current_suggestion)
            word_buffer = ""; suggestion_active = False; current_suggestion = None
        return True

    try:
        if key == keyboard.Key.backspace:
            word_buffer = word_buffer[:-1]
            return True
        if key in (keyboard.Key.space, keyboard.Key.enter):
            word_buffer = ""; suggestion_active = False; current_suggestion = None
            return True
        
        char = key.char
        if char is None or not char.isalpha():
            word_buffer = ""; suggestion_active = False; current_suggestion = None
            return True

        word_buffer += char.lower()
        if len(word_buffer) > MAX_BUFFER:
            word_buffer = word_buffer[-MAX_BUFFER:]

        matched = False
        for i in range(len(word_buffer), 0, -1):
            substr = word_buffer[-i:]
            if substr in dictionary:
                suggestion_active = True
                current_suggestion = dictionary[substr]
                matched = True
                break
        
        if not matched:
            suggestion_active = False; current_suggestion = None

    except AttributeError:
        pass

if __name__ == "__main__":
    load_dictionary()

    if PRINT_BANNER:
        print("-" * 30)
        print("Typing Assistant (Local + Reload)")
        print("-" * 30)
        print(f"Accept key: {ACCEPT_KEY_NAME}")
        print("Reload key: Ctrl + Alt + R")
        print("-" * 30)

    with keyboard.GlobalHotKeys({'<ctrl>+<alt>+r': on_reload}) as h:
        with keyboard.Listener(on_press=on_press) as listener:
            try:
                listener.join()
            except KeyboardInterrupt:
                print("\nStopped.")