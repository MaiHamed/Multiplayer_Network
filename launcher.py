import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys


class Launcher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Grid Game Network Launcher")
        self.root.geometry("600x550")
        
        self.server_process = None
        self.client_processes = []
        self.mode = None  
        
        self.setup_ui()
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title = ttk.Label(main_frame, text="🎮 Grid Game Network", font=("Arial", 20, "bold"))
        title.grid(row=0, column=0, pady=(0, 10))
        
        # Subtitle
        subtitle = ttk.Label(main_frame, 
                           text="Computer Networks Project - Multiplayer Grid Game",
                           font=("Arial", 10))
        subtitle.grid(row=1, column=0, pady=(0, 30))
        
        # Mode selection section
        mode_frame = ttk.LabelFrame(main_frame, text="Select Mode", padding="15")
        mode_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Mode explanation
        mode_desc = ttk.Label(mode_frame, 
                            text="Choose whether you want to run the Server or Client(s)",
                            font=("Arial", 10))
        mode_desc.grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # Server button
        server_btn = ttk.Button(
            mode_frame,
            text="SERVER",
            command=self.select_server_mode,
            width=20,
            style="Accent.TButton"
        )
        server_btn.grid(row=1, column=0, padx=(0, 10))
        
        # Client button
        client_btn = ttk.Button(
            mode_frame,
            text="CLIENT(S)",
            command=self.select_client_mode,
            width=20,
            style="Accent.TButton"
        )
        client_btn.grid(row=1, column=1)
        
        # Server section 
        self.server_section = ttk.LabelFrame(main_frame, text="Server Controls", padding="10")
        self.server_section.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        self.server_section.grid_remove()  
        
        server_controls = ttk.Frame(self.server_section)
        server_controls.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.start_server_btn = ttk.Button(
            server_controls,
            text="Start Game Server",
            command=self.start_server,
            width=20,
            state='normal'
        )
        self.start_server_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.server_status = ttk.Label(server_controls, text="Not running", foreground="red")
        self.server_status.grid(row=0, column=1)
        
        # Client section (initially hidden)
        self.client_section = ttk.LabelFrame(main_frame, text="Client Controls", padding="10")
        self.client_section.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        self.client_section.grid_remove()  
        
        # Connection info
        conn_frame = ttk.Frame(self.client_section)
        conn_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(conn_frame, text="Server Address:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.server_addr_entry = ttk.Entry(conn_frame, width=15)
        self.server_addr_entry.grid(row=0, column=1, padx=(0, 10))
        self.server_addr_entry.insert(0, "127.0.0.1")
        
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        
        self.server_port_entry = ttk.Entry(conn_frame, width=8)
        self.server_port_entry.grid(row=0, column=3)
        self.server_port_entry.insert(0, "5005")
        
        # Client launch controls
        client_controls = ttk.LabelFrame(self.client_section, text="Launch Players", padding="10")
        client_controls.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Single client button
        ttk.Label(client_controls, text="Launch waiting room:").grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        single_client_btn = ttk.Button(
            client_controls,
            text="Player",
            command=self.launch_single_client,
            width=15
        )
        single_client_btn.grid(row=0, column=1, padx=(5, 10))
        
        
        # Quick launch buttons
        quick_frame = ttk.LabelFrame(main_frame, text="Quick Start", padding="10")
        quick_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        quick_frame.grid_remove()  # Hide initially
        
        
        # Status section
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.client_status = ttk.Label(status_frame, text="No clients running", foreground="gray")
        self.client_status.grid(row=0, column=0, sticky=tk.W)
        
        self.status_label = ttk.Label(status_frame, text="Select a mode to begin", foreground="blue")
        self.status_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=7, column=0, pady=(20, 0))
        
        # Quit button
        quit_btn = ttk.Button(control_frame, text="Quit All", 
                             command=self.quit_all, width=15)
        quit_btn.grid(row=0, column=1)
        
        # Instructions
        instructions = ttk.Label(
            main_frame,
            text="Tip: You need at least 2 players connected to start the game",
            foreground="gray",
            font=("Arial", 9)
        )
        instructions.grid(row=8, column=0, pady=(10, 0), sticky=tk.W)
    
    def select_server_mode(self):
        """Switch to server mode"""
        self.mode = 'server'
        self.server_section.grid()  # Show server section
        self.client_section.grid_remove()  # Hide client section
        self.status_label.config(text="Server mode selected. Click 'Start Game Server'")
        
        # Show quick start options
        self.root.nametowidget('.!frame.!labelframe4').grid()
    
    def select_client_mode(self):
        """Switch to client mode"""
        self.mode = 'client'
        self.client_section.grid()  # Show client section
        self.server_section.grid_remove()  # Hide server section
        self.root.nametowidget('.!frame.!labelframe4').grid_remove()  # Hide quick start
        
        self.status_label.config(text="Client mode selected. Enter server address and launch clients")
        self.add_more_btn.config(state='normal')
    
    def start_server(self):
        """Start the game server"""
        if self.server_process is None:
            try:
                self.server_process = subprocess.Popen([sys.executable, "server.py"])
                self.server_status.config(text="Running", foreground="green")
                self.start_server_btn.config(state='disabled')
                self.status_label.config(text="Server started successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start server: {e}")
                self.server_status.config(text="Failed to start", foreground="red")
   
    def launch_single_client(self):
        """Launch a single client and close launcher"""
        try:
            server_addr = self.server_addr_entry.get()
            server_port = self.server_port_entry.get()

            if not server_addr or not server_port:
                messagebox.showwarning("Warning", "Please enter server address and port")
                return

            # --- CLOSE THIS PAGE / TERMINATE WINDOW ---
            self.root.destroy()   # closes the launcher window completely

            # --- OPEN WAITING ROOM ---
            subprocess.Popen([sys.executable, "waiting_room.py",
                            server_addr, server_port])

        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch client: {e}")

    def quit_all(self):
        """Close all windows"""
        # Close server
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process = None
                self.server_status.config(text="Not running", foreground="red")
                self.start_server_btn.config(state='normal')
            except:
                pass
        
        # Close client processes
        for process in self.client_processes:
            try:
                process.terminate()
            except:
                pass
        self.client_processes = []
        self.update_client_status()
        
        # Update status
        self.status_label.config(text="All processes closed", foreground="green")
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    launcher = Launcher()
    launcher.run()