import g4f
import sys
import inspect
import json
import os
import pickle
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue

# Dictionary to store available providers
available_providers = {}

# File to store API keys
API_KEYS_FILE = "api_keys.json"

# File to store custom prompts
CUSTOM_PROMPTS_FILE = "custom_prompts.json"

# Directory for caching
CACHE_DIR = "cache"

# Global variables for GUI
root = None
chat_output = None
user_input = None
send_button = None
provider_var = None
chat_name_var = None
current_chat = None
input_queue = queue.Queue()
output_queue = queue.Queue()

# Load API keys from file
def load_api_keys():
    if os.path.exists(API_KEYS_FILE):
        with open(API_KEYS_FILE, 'r') as f:
            return json.load(f)
    return {}

# Save API keys to file
def save_api_keys(api_keys):
    with open(API_KEYS_FILE, 'w') as f:
        json.dump(api_keys, f, indent=2)

# Load custom prompts from file
def load_custom_prompts():
    if os.path.exists(CUSTOM_PROMPTS_FILE):
        with open(CUSTOM_PROMPTS_FILE, 'r') as f:
            return json.load(f)
    return {}

# Save custom prompts to file
def save_custom_prompts(custom_prompts):
    with open(CUSTOM_PROMPTS_FILE, 'w') as f:
        json.dump(custom_prompts, f, indent=2)

# Cache function
def cache_response(provider, query, response):
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    cache_file = os.path.join(CACHE_DIR, f"{provider}_cache.pkl")
    cache = {}
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            cache = pickle.load(f)
    cache[query] = response
    with open(cache_file, 'wb') as f:
        pickle.dump(cache, f)

# Get cached response
def get_cached_response(provider, query):
    cache_file = os.path.join(CACHE_DIR, f"{provider}_cache.pkl")
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            cache = pickle.load(f)
        return cache.get(query)
    return None

# Dynamically get all provider classes from g4f.Provider
for name, obj in inspect.getmembers(g4f.Provider):
    if inspect.isclass(obj) and issubclass(obj, g4f.Provider.BaseProvider) and obj != g4f.Provider.BaseProvider:
        try:
            if obj.working:
                available_providers[name] = obj
        except AttributeError:
            pass

# Function to display available providers
def display_providers():
    provider_list = list(available_providers.keys())
    provider_var.set(provider_list[0] if provider_list else "No providers available")
    provider_menu['menu'].delete(0, 'end')
    for provider in provider_list:
        provider_menu['menu'].add_command(label=provider, command=tk._setit(provider_var, provider))

# Function to manage API keys
def manage_api_keys():
    api_keys = load_api_keys()
    api_key_window = tk.Toplevel(root)
    api_key_window.title("API Key Management")

    ttk.Label(api_key_window, text="Provider:").grid(row=0, column=0, padx=5, pady=5)
    ttk.Label(api_key_window, text="API Key:").grid(row=0, column=1, padx=5, pady=5)

    for i, (provider, key) in enumerate(api_keys.items(), start=1):
        ttk.Label(api_key_window, text=provider).grid(row=i, column=0, padx=5, pady=2)
        ttk.Label(api_key_window, text=f"{key[:5]}...{key[-5:]}").grid(row=i, column=1, padx=5, pady=2)

    def add_api_key():
        provider = provider_entry.get()
        key = key_entry.get()
        if provider and key:
            api_keys[provider] = key
            save_api_keys(api_keys)
            provider_entry.delete(0, tk.END)
            key_entry.delete(0, tk.END)
            manage_api_keys()  # Refresh the window

    ttk.Label(api_key_window, text="Add/Update API Key:").grid(row=len(api_keys)+1, column=0, columnspan=2, padx=5, pady=10)
    provider_entry = ttk.Entry(api_key_window)
    provider_entry.grid(row=len(api_keys)+2, column=0, padx=5, pady=2)
    key_entry = ttk.Entry(api_key_window)
    key_entry.grid(row=len(api_keys)+2, column=1, padx=5, pady=2)
    ttk.Button(api_key_window, text="Add/Update", command=add_api_key).grid(row=len(api_keys)+3, column=0, columnspan=2, padx=5, pady=10)

# Function to manage custom prompts
def manage_custom_prompts():
    custom_prompts = load_custom_prompts()
    prompt_window = tk.Toplevel(root)
    prompt_window.title("Custom Prompts Management")

    ttk.Label(prompt_window, text="Name:").grid(row=0, column=0, padx=5, pady=5)
    ttk.Label(prompt_window, text="Prompt:").grid(row=0, column=1, padx=5, pady=5)

    for i, (name, prompt) in enumerate(custom_prompts.items(), start=1):
        ttk.Label(prompt_window, text=name).grid(row=i, column=0, padx=5, pady=2)
        ttk.Label(prompt_window, text=prompt[:50] + "...").grid(row=i, column=1, padx=5, pady=2)

    def add_custom_prompt():
        name = name_entry.get()
        prompt = prompt_entry.get()
        if name and prompt:
            custom_prompts[name] = prompt
            save_custom_prompts(custom_prompts)
            name_entry.delete(0, tk.END)
            prompt_entry.delete(0, tk.END)
            manage_custom_prompts()  # Refresh the window

    ttk.Label(prompt_window, text="Add/Update Custom Prompt:").grid(row=len(custom_prompts)+1, column=0, columnspan=2, padx=5, pady=10)
    name_entry = ttk.Entry(prompt_window)
    name_entry.grid(row=len(custom_prompts)+2, column=0, padx=5, pady=2)
    prompt_entry = ttk.Entry(prompt_window)
    prompt_entry.grid(row=len(custom_prompts)+2, column=1, padx=5, pady=2)
    ttk.Button(prompt_window, text="Add/Update", command=add_custom_prompt).grid(row=len(custom_prompts)+3, column=0, columnspan=2, padx=5, pady=10)

# Function to display provider information
def display_provider_info(provider_name):
    provider = available_providers[provider_name]
    info = f"Provider Information for {provider_name}:\n"
    info += f"Working: {provider.working}\n"
    info += f"Supports Stream: {provider.supports_stream}\n"
    info += f"Needs Auth: {provider.needs_auth}\n"
    if hasattr(provider, 'params'):
        info += "Parameters:\n"
        for param, value in provider.params.items():
            info += f" {param}: {value}\n"
    messagebox.showinfo("Provider Information", info)

# Function to start a conversation with the selected provider
def start_conversation():
    global current_chat
    api_keys = load_api_keys()
    custom_prompts = load_custom_prompts()
    provider_name = provider_var.get()
    chat_name = chat_name_var.get()
    
    if not chat_name:
        messagebox.showerror("Error", "Please enter a chat name.")
        return

    current_chat = chat_name
    provider = available_providers[provider_name]
    output_queue.put(f"\nConversing with {provider_name} in chat '{chat_name}'...")
    history = []

    while True:
        try:
            user_input = input_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        if user_input.lower() == 'exit':
            break
        if user_input.lower() == 'switch':
            output_queue.put("Please select a new provider and start a new chat.")
            break
        if user_input.lower() == 'info':
            display_provider_info(provider_name)
            continue
        if user_input.lower().startswith('use prompt '):
            prompt_name = user_input[11:].strip()
            if prompt_name in custom_prompts:
                user_input = custom_prompts[prompt_name]
                output_queue.put(f"Using custom prompt: {user_input}")
            else:
                output_queue.put(f"Custom prompt '{prompt_name}' not found.")
            continue

        # Log user input in chat output
        output_queue.put(f"You: {user_input}")

        history.append({"role": "user", "content": user_input})
        cached_response = get_cached_response(provider_name, user_input)
        if cached_response:
            output_queue.put(f"{provider_name} (cached): {cached_response}")
            history.append({"role": "assistant", "content": cached_response})
            continue

        try:
            api_key = api_keys.get(provider_name)
            response = g4f.ChatCompletion.create(
                model=None,
                provider=provider,
                messages=history,
                api_key=api_key
            )
            output_queue.put(f"{provider_name}: {response}")
            history.append({"role": "assistant", "content": response})
            cache_response(provider_name, user_input, response)
        except Exception as e:
            error_message = f"An error occurred: {str(e)}\n"
            error_message += "This could be due to provider issues, rate limiting, or missing API key.\n"
            error_message += "You can try again, switch providers, or check your API key."
            output_queue.put(error_message)

# GUI setup
def setup_gui():
    global root, chat_output, user_input, send_button, provider_var, chat_name_var, provider_menu

    root = tk.Tk()
    root.title("G4F Advanced Chat")

    # Provider selection
    provider_frame = ttk.Frame(root)
    provider_frame.pack(pady=10)
    ttk.Label(provider_frame, text="Select Provider:").pack(side=tk.LEFT)
    provider_var = tk.StringVar(root)
    provider_menu = ttk.OptionMenu(provider_frame, provider_var, "")
    provider_menu.pack(side=tk.LEFT)

    # Chat name entry
    chat_name_frame = ttk.Frame(root)
    chat_name_frame.pack(pady=10)
    ttk.Label(chat_name_frame, text="Chat Name:").pack(side=tk.LEFT)
    chat_name_var = tk.StringVar(root)
    ttk.Entry(chat_name_frame, textvariable=chat_name_var).pack(side=tk.LEFT)

    # Start chat button
    start_button = ttk.Button(root, text="Start Chat", command=start_chat_thread)
    start_button.pack(pady=5)

    # Chat output
    chat_output = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=80, height=20)
    chat_output.pack(padx=10, pady=10)
    chat_output.config(state=tk.DISABLED)

    # User input
    input_frame = ttk.Frame(root)
    input_frame.pack(pady=10)
    user_input = ttk.Entry(input_frame, width=70)
    user_input.pack(side=tk.LEFT, padx=5)
    send_button = ttk.Button(input_frame, text="Send", command=send_message)
    send_button.pack(side=tk.LEFT)

    # Menu bar
    menubar = tk.Menu(root)
    root.config(menu=menubar)

    # File menu
    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="Manage API Keys", command=manage_api_keys)
    file_menu.add_command(label="Manage Custom Prompts", command=manage_custom_prompts)
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=root.quit)

    # Update available providers
    display_providers()

    # Bind Ctrl+D to return to main menu
    root.bind('<Control-d>', lambda event: return_to_main_menu())

def return_to_main_menu():
    global current_chat
    current_chat = None
    output_queue.put("\nReturned to main menu. Please start a new chat.")

def send_message():
    message = user_input.get()
    if message:
        user_input.delete(0, tk.END)
        input_queue.put(message)

def start_chat_thread():
    conversation_thread = threading.Thread(target=start_conversation, daemon=True)
    conversation_thread.start()

def update_chat_output():
    while True:
        try:
            message = output_queue.get_nowait()
            chat_output.config(state=tk.NORMAL)
            chat_output.insert(tk.END, message + "\n")
            chat_output.see(tk.END)
            chat_output.config(state=tk.DISABLED)
        except queue.Empty:
            break
    root.after(100, update_chat_output)

def main():
    setup_gui()
    update_chat_output()
    root.mainloop()

if __name__ == "__main__":
    main()