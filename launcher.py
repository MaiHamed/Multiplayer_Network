# launcher.py
import tkinter as tk
from tkinter import ttk
import subprocess
import sys

class Launcher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Grid Game Launcher")
        self.root.geometry("400x300")
        
        self.setup_ui()
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title = ttk.Label(main_frame, text="Grid Game Network", font=("Arial", 16, "bold"))
        title.grid(row=0, column=0, pady=(0, 20))
        
        # Description
        desc = ttk.Label(main_frame, text="A networking game where players claim cells on a grid", 
                        wraplength=350)
        desc.grid(row=1, column=0, pady=(0, 30))
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=2, column=0)
        
        server_btn = ttk.Button(
            btn_frame,
            text="Start Server",
            command=self.start_server,
            width=20
        )
        server_btn.grid(row=0, column=0, pady=5)
        
        client_btn = ttk.Button(
            btn_frame,
            text="Start Client",
            command=self.start_client,
            width=20
        )
        client_btn.grid(row=1, column=0, pady=5)
        
        both_btn = ttk.Button(
            btn_frame,
            text="Start Both",
            command=self.start_both,
            width=20
        )
        both_btn.grid(row=2, column=0, pady=5)
        
        quit_btn = ttk.Button(
            btn_frame,
            text="Quit",
            command=self.root.quit,
            width=20
        )
        quit_btn.grid(row=3, column=0, pady=(20, 0))
    
    def start_server(self):
        subprocess.Popen([sys.executable, "server.py"])
    
    def start_client(self):
        subprocess.Popen([sys.executable, "client.py"])
    
    def start_both(self):
        self.start_server()
        self.start_client()
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    launcher = Launcher()
    launcher.run()