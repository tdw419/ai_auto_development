#!/usr/bin/env python3
"""
Minimal Core AI Chat Interface - Refactored for Stability and Performance
A clean, robust foundation using ScrolledText, ready for freezing.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import json
import time
import os
from datetime import datetime

class MinimalCoreChat:
    """
    A robust, minimal, and extensible chat interface core.
    - Uses a performant ScrolledText widget for the chat display.
    - Manages UI updates from background threads safely.
    - Provides clear extension points for AI integration and other features.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Minimal Core AI Chat")
        self.root.geometry("800x600")
        self.root.minsize(400, 300)

        # Core data
        self.conversation_history = []

        # UI Setup
        self.setup_styles()
        self.setup_ui()
        self.add_welcome_message()

    def setup_styles(self):
        """Configure ttk styles and ScrolledText tags."""
        style = ttk.Style()
        try:
            # Use a modern theme if available
            style.theme_use('clam')
        except tk.TclError:
            print("Clam theme not available, using default.")

        # Padded style for buttons
        style.configure('TButton', padding=5)

    def setup_ui(self):
        """Build the main user interface."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Configure grid layout for responsiveness
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        self.setup_chat_display(main_frame)
        self.setup_input_area(main_frame)
        self.setup_actions_bar(main_frame)

    def setup_chat_display(self, parent):
        """
        Set up a single, performant ScrolledText widget for the chat history.
        This is more efficient than creating individual widgets for each message.
        """
        chat_frame = ttk.Frame(parent)
        chat_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        chat_frame.grid_rowconfigure(0, weight=1)
        chat_frame.grid_columnconfigure(0, weight=1)

        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=("Arial", 10),
            bg='#ffffff',
            fg='#111111',
            padx=10,
            pady=10,
            state=tk.DISABLED # Start as read-only
        )
        self.chat_display.grid(row=0, column=0, sticky="nsew")

        # Configure tags for styling different roles
        self.chat_display.tag_config('user_role', foreground='#00529B', font=("Arial", 10, "bold"))
        self.chat_display.tag_config('assistant_role', foreground='#C41E3A', font=("Arial", 10, "bold"))
        self.chat_display.tag_config('system_role', foreground='#2E8B57', font=("Arial", 10, "italic"))
        self.chat_display.tag_config('content', lmargin1=10, lmargin2=10)
        self.chat_display.tag_config('timestamp', foreground='gray', font=("Arial", 8))

    def setup_input_area(self, parent):
        """Set up the user input field and send button."""
        input_frame = ttk.Frame(parent)
        input_frame.grid(row=1, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        self.message_var = tk.StringVar()
        self.message_entry = ttk.Entry(
            input_frame,
            textvariable=self.message_var,
            font=("Arial", 11)
        )
        self.message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.message_entry.bind("<Return>", self.send_message_event)

        self.send_button = ttk.Button(
            input_frame,
            text="Send",
            command=self.send_message
        )
        self.send_button.grid(row=0, column=1)

        self.message_entry.focus()

    def setup_actions_bar(self, parent):
        """Set up the bar for actions like save, load, and clear."""
        actions_frame = ttk.Frame(parent)
        actions_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        ttk.Button(actions_frame, text="Clear Chat",
                   command=self.clear_chat).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(actions_frame, text="Save Session",
                   command=self.save_session).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(actions_frame, text="Load Session",
                   command=self.load_session).pack(side=tk.LEFT)

    def add_message(self, role: str, content: str):
        """
        Adds a message to the chat display, applying styles using tags.
        """
        timestamp = datetime.now().strftime("[%H:%M:%S]")

        # Store message in history before displaying
        self.conversation_history.append({
            'role': role,
            'content': content,
            'timestamp': timestamp[1:-1] # Store without brackets
        })

        # Make the widget writable to insert text
        self.chat_display.config(state=tk.NORMAL)

        # Add a newline for spacing if the chat is not empty
        if self.chat_display.get('1.0', tk.END).strip():
            self.chat_display.insert(tk.END, "\n")

        # Insert Role and Timestamp
        role_tag = f"{role.lower()}_role"
        self.chat_display.insert(tk.END, f"{role.title()} ", (role_tag,))
        self.chat_display.insert(tk.END, f"{timestamp}\n", ('timestamp',))

        # Insert Content
        self.chat_display.insert(tk.END, content + "\n", ('content',))

        # Make the widget read-only again
        self.chat_display.config(state=tk.DISABLED)

        # Ensure the view scrolls to the latest message
        self.chat_display.see(tk.END)

    def send_message_event(self, event=None):
        """Wrapper to handle the <Return> key event."""
        self.send_message()
        return "break" # Prevents the default newline insertion

    def send_message(self):
        """Handles the logic for sending a user message."""
        message = self.message_var.get().strip()
        if not message:
            return

        # Add user message to the UI
        self.add_message("user", message)
        self.message_var.set("")

        # Disable input while processing
        self.send_button.config(state=tk.DISABLED)
        self.message_entry.config(state=tk.DISABLED)

        # Process the message in a background thread to keep the UI responsive
        threading.Thread(
            target=self.process_message_thread,
            args=(message,),
            daemon=True
        ).start()

    # --- AI INTEGRATION EXTENSION POINT ---
    def process_message_thread(self, message: str):
        """
        This is the primary extension point for integrating a real AI model.
        It runs in a background thread.
        """
        try:
            # Simulate "thinking" time
            time.sleep(1.5)

            # --- REPLACE THIS MOCK LOGIC WITH YOUR AI CLIENT CALL ---
            if "hello" in message.lower():
                response = "Hello! This is the Minimal Core AI. It is now stable and ready for extensions."
            elif "build" in message.lower() or "create" in message.lower():
                response = "I see you're ready to build! To connect me to a real model, overwrite this 'process_message_thread' method."
            else:
                response = f"Simulated response to: '{message}'\n\nThe core is frozen. You can now add extensions for features like syntax highlighting or real-time streaming."
            # ---------------------------------------------------------

            # Safely schedule the UI update on the main thread
            self.root.after(0, self.add_message, "assistant", response)

        except Exception as e:
            # Handle any errors during AI processing
            error_message = f"An error occurred: {e}"
            self.root.after(0, self.add_message, "system", error_message)
            print(f"Error in process_message_thread: {e}")

        finally:
            # Always re-enable the UI on the main thread
            self.root.after(0, self.enable_input)

    def enable_input(self):
        """Re-enables the input field and send button."""
        self.send_button.config(state=tk.NORMAL)
        self.message_entry.config(state=tk.NORMAL)
        self.message_entry.focus()
    # ---------------------------------------

    def add_welcome_message(self):
        """Displays the initial welcome message."""
        welcome_message = """Welcome to the Minimal Core AI Chat!

This refactored version provides a stable and performant foundation. It is now ready to be "frozen" and extended with features like:
- Real AI model integration (e.g., LM Studio).
- Code syntax highlighting.
- Streaming responses.
- Advanced styling and themes.
"""
        self.add_message("system", welcome_message)

    def clear_chat(self):
        """Clears the chat history after user confirmation."""
        if messagebox.askyesno("Clear Chat", "Are you sure you want to clear the entire chat history?"):
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete('1.0', tk.END)
            self.chat_display.config(state=tk.DISABLED)
            self.conversation_history.clear()
            self.add_welcome_message()

    def save_session(self):
        """Saves the current conversation to a JSON file."""
        filename = filedialog.asksaveasfilename(
            title="Save Session",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            try:
                session_data = {
                    'version': '1.0-frozen',
                    'timestamp': datetime.now().isoformat(),
                    'conversation_history': self.conversation_history
                }
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2)
                self.add_message("system", f"Session saved to: {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save session: {e}")

    def load_session(self):
        """Loads a conversation from a JSON file."""
        filename = filedialog.askopenfilename(
            title="Load Session",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)

                # Perform a basic validation
                if 'conversation_history' not in session_data:
                    raise ValueError("Invalid session file format.")

                # Clear existing chat before loading
                self.chat_display.config(state=tk.NORMAL)
                self.chat_display.delete('1.0', tk.END)
                self.chat_display.config(state=tk.DISABLED)
                self.conversation_history.clear()

                # Load messages from the file
                for msg in session_data.get('conversation_history', []):
                    self.add_message(msg['role'], msg['content'])

                self.add_message("system", f"Session loaded from: {os.path.basename(filename)}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to load session: {e}")


def main():
    """Launch the Minimal Core Chat Interface."""
    root = tk.Tk()
    app = MinimalCoreChat(root)
    root.mainloop()

if __name__ == "__main__":
    main()
