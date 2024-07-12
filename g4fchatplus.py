import g4f
import sys
import inspect
import json
import os
import pickle
from datetime import datetime
import sys
import select

# Dictionary to store available providers
available_providers = {}

# File to store API keys
API_KEYS_FILE = "api_keys.json"

# File to store custom prompts
CUSTOM_PROMPTS_FILE = "custom_prompts.json"

# Directory for caching
CACHE_DIR = "cache"

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
    print("\nAvailable providers:")
    for i, provider in enumerate(available_providers.keys(), start=1):
        print(f"{i}. {provider}")

# Function to get user input for provider selection
def get_provider_choice():
    while True:
        choice = input("Enter your choice (number) or 'q' to quit: ")
        if choice.lower() == 'q':
            return None
        try:
            index = int(choice) - 1
            if 0 <= index < len(available_providers):
                return list(available_providers.keys())[index]
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number or 'q'.")

# Function to manage API keys
def manage_api_keys(api_keys):
    while True:
        print("\nAPI Key Management:")
        print("1. View API keys")
        print("2. Add/Update API key")
        print("3. Remove API key")
        print("4. Return to main menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            print("\nCurrent API keys:")
            for provider, key in api_keys.items():
                print(f"{provider}: {key[:5]}...{key[-5:]}")
        elif choice == '2':
            provider = input("Enter provider name: ")
            key = input("Enter API key: ")
            api_keys[provider] = key
            save_api_keys(api_keys)
            print("API key added/updated successfully.")
        elif choice == '3':
            provider = input("Enter provider name to remove: ")
            if provider in api_keys:
                del api_keys[provider]
                save_api_keys(api_keys)
                print("API key removed successfully.")
            else:
                print("Provider not found.")
        elif choice == '4':
            break
        else:
            print("Invalid choice. Please try again.")

# Function to manage custom prompts
def manage_custom_prompts(custom_prompts):
    while True:
        print("\nCustom Prompts Management:")
        print("1. View custom prompts")
        print("2. Add/Update custom prompt")
        print("3. Remove custom prompt")
        print("4. Return to main menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            print("\nCurrent custom prompts:")
            for name, prompt in custom_prompts.items():
                print(f"{name}: {prompt}")
        elif choice == '2':
            name = input("Enter prompt name: ")
            prompt = input("Enter prompt: ")
            custom_prompts[name] = prompt
            save_custom_prompts(custom_prompts)
            print("Custom prompt added/updated successfully.")
        elif choice == '3':
            name = input("Enter prompt name to remove: ")
            if name in custom_prompts:
                del custom_prompts[name]
                save_custom_prompts(custom_prompts)
                print("Custom prompt removed successfully.")
            else:
                print("Prompt not found.")
        elif choice == '4':
            break
        else:
            print("Invalid choice. Please try again.")

# Function to display provider information
def display_provider_info(provider_name):
    provider = available_providers[provider_name]
    print(f"\nProvider Information for {provider_name}:")
    print(f"Working: {provider.working}")
    print(f"Supports Stream: {provider.supports_stream}")
    print(f"Needs Auth: {provider.needs_auth}")
    if hasattr(provider, 'params'):
        print("Parameters:")
        for param, value in provider.params.items():
            print(f"  {param}: {value}")

def start_conversation(provider_name, api_keys, custom_prompts):
    provider = available_providers[provider_name]
    print(f"\nConversing with {provider_name}...")
    print("Type 'menu' at any time to return to the main menu.")
    history = []

    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            return False  # Signal to end the chat
        if user_input.lower() == 'menu':
            return 'menu'  # Signal to return to the main menu
        if user_input.lower() == 'switch':
            return True  # Signal to switch provider
        if user_input.lower() == 'info':
            display_provider_info(provider_name)
            continue
        if user_input.lower().startswith('use prompt '):
            prompt_name = user_input[11:].strip()
            if prompt_name in custom_prompts:
                user_input = custom_prompts[prompt_name]
                print(f"Using custom prompt: {user_input}")
            else:
                print(f"Custom prompt '{prompt_name}' not found.")
                continue

        history.append({"role": "user", "content": user_input})

        cached_response = get_cached_response(provider_name, user_input)
        if cached_response:
            print(f"{provider_name} (cached): {cached_response}")
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
            print(f"{provider_name}: {response}")
            history.append({"role": "assistant", "content": response})
            cache_response(provider_name, user_input, response)
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            print("This could be due to provider issues, rate limiting, or missing API key.")
            print("You can try again, switch providers, check your API key, or type 'menu' to return to the main menu.")

    return False  # Signal to not switch provider

def manage_chats(api_keys, custom_prompts):
    chats = {}
    current_chat = None

    while True:
        print("\nChat Management:")
        print("1. Create new chat")
        print("2. Switch to existing chat")
        print("3. List all chats")
        print("4. Delete a chat")
        print("5. Return to main menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            display_providers()
            provider_choice = get_provider_choice()
            if provider_choice:
                chat_name = input("Enter a name for this chat: ")
                chats[chat_name] = {"provider": provider_choice, "history": []}
                current_chat = chat_name
                print(f"Created and switched to chat '{chat_name}' with provider {provider_choice}")
        elif choice == '2':
            if chats:
                print("\nExisting chats:")
                for name in chats.keys():
                    print(name)
                chat_name = input("Enter the name of the chat to switch to: ")
                if chat_name in chats:
                    current_chat = chat_name
                    print(f"Switched to chat '{chat_name}'")
                else:
                    print("Chat not found.")
            else:
                print("No existing chats.")
        elif choice == '3':
            if chats:
                print("\nAll chats:")
                for name, info in chats.items():
                    print(f"{name} (Provider: {info['provider']})")
            else:
                print("No existing chats.")
        elif choice == '4':
            if chats:
                print("\nExisting chats:")
                for name in chats.keys():
                    print(name)
                chat_name = input("Enter the name of the chat to delete: ")
                if chat_name in chats:
                    del chats[chat_name]
                    if current_chat == chat_name:
                        current_chat = None
                    print(f"Deleted chat '{chat_name}'")
                else:
                    print("Chat not found.")
            else:
                print("No existing chats.")
        elif choice == '5':
            return

        if current_chat:
            print(f"\nCurrent chat: {current_chat}")
            chat_info = chats[current_chat]
            result = start_conversation(chat_info["provider"], api_keys, custom_prompts)
            if result == 'menu':
                continue  # Return to the chat management menu
            elif result:  # True means switch provider
                display_providers()
                new_provider = get_provider_choice()
                if new_provider:
                    chat_info["provider"] = new_provider
                    print(f"Switched provider to {new_provider}")

# Main function
def main():
    api_keys = load_api_keys()
    custom_prompts = load_custom_prompts()

    while True:
        print("\nMain Menu:")
        print("1. Manage chats")
        print("2. Manage API keys")
        print("3. Manage custom prompts")
        print("4. Quit")
        choice = input("Enter your choice: ")

        if choice == '1':
            manage_chats(api_keys, custom_prompts)
        elif choice == '2':
            manage_api_keys(api_keys)
        elif choice == '3':
            manage_custom_prompts(custom_prompts)
        elif choice == '4':
            print("Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()