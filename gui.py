# gui.py (fixed initialization order)
import tkinter as tk
from tkinter import ttk, scrolledtext, font
import threading
import queue
import time

class GameGUI:
    def __init__(self, title="Grid Game", rows=20, cols=20, cell_size=25):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("1300x800")
        
        # Configure theme colors
        self.colors = {
            'bg': '#2b2b2b',
            'fg': '#ffffff',
            'accent': '#4CAF50',
            'highlight': '#2196F3',
            'claimed': '#4CAF50',
            'unclaimed': '#3c3c3c',
            'yours': '#2196F3',
            'others': '#FF9800',
            'panel': '#3c3c3c',
            'panel_bg': '#2b2b2b',
            'text': '#ffffff',
            'button': '#4CAF50',
            'button_hover': '#45a049',
            'log_bg': '#1e1e1e'
        }
        
        # Configure root window
        self.root.configure(bg=self.colors['bg'])
        
        self.rows = rows
        self.cols = cols
        self.cell_size = cell_size
        
        # Data from network
        self.grid_state = [[0 for _ in range(cols)] for _ in range(rows)]
        self.players = {}
        self.snapshot_id = 0
        
        # Initialize variables BEFORE setup_ui
        self.snapshot_var = tk.StringVar(value="0")
        self.players_var = tk.StringVar(value="0")
        self.sent_var = tk.StringVar(value="0")
        self.received_var = tk.StringVar(value="0")
        self.dropped_var = tk.StringVar(value="0")
        self.latency_var = tk.StringVar(value="0 ms")
        self.player_id_var = tk.StringVar(value="Not Connected")
        self.status_var = tk.StringVar(value="🔴 Disconnected")
        self.row_var = tk.StringVar(value="0")
        self.col_var = tk.StringVar(value="0")
        self.speed_var = tk.DoubleVar(value=0.3)
        self.auto_claim_var = tk.BooleanVar(value=False)
        
        # Packet statistics
        self.packet_stats = {
            'sent': 0,
            'received': 0,
            'dropped': 0,
            'latency_sum': 0,
            'latency_count': 0
        }
        
        # For click tracking
        self.last_clicked = None
        self.click_callback = None
        
        # Message queue for thread-safe GUI updates
        self.message_queue = queue.Queue()
        
        # Setup UI with better aesthetics
        self.setup_ui()
        
        # Start queue processing
        self.root.after(100, self.process_queue)
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.close)
    
    def setup_ui(self):
        # Create main frames with better styling
        main_frame = tk.Frame(self.root, bg=self.colors['bg'], padx=15, pady=15)
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Left panel - Game Board
        left_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        
        # Right panel - Controls and Info
        right_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        right_frame.grid(row=0, column=1, sticky="nsew")
        
        # Game Board Canvas
        self.create_game_board(left_frame)
        
        # Control Panel
        self.create_control_panel(right_frame)
        
        # Status Panel
        self.create_status_panel(right_frame)
        
        # Log Panel
        self.create_log_panel(right_frame)
    
    def create_game_board(self, parent):
        # Create frame with modern styling
        board_frame = tk.Frame(parent, bg=self.colors['panel'], 
                              highlightbackground=self.colors['accent'], 
                              highlightthickness=2, padx=10, pady=10)
        board_frame.grid(row=0, column=0, sticky="nsew")
        
        # Title
        title_label = tk.Label(board_frame, text="🎮 GAME BOARD", 
                              font=("Arial", 16, "bold"),
                              fg=self.colors['accent'],
                              bg=self.colors['panel'])
        title_label.grid(row=0, column=0, pady=(0, 10))
        
        # Calculate canvas size
        canvas_width = self.cols * self.cell_size + 40
        canvas_height = self.rows * self.cell_size + 40
        
        # Create canvas with scrollbars
        canvas_frame = tk.Frame(board_frame, bg=self.colors['panel'])
        canvas_frame.grid(row=1, column=0)
        
        # Add scrollbars for large grids
        if self.rows > 15 or self.cols > 15:
            v_scrollbar = tk.Scrollbar(canvas_frame, orient="vertical")
            h_scrollbar = tk.Scrollbar(canvas_frame, orient="horizontal")
            
            self.canvas = tk.Canvas(
                canvas_frame, 
                width=min(canvas_width, 600),
                height=min(canvas_height, 600),
                bg=self.colors['panel_bg'],
                highlightthickness=0,
                yscrollcommand=v_scrollbar.set,
                xscrollcommand=h_scrollbar.set
            )
            
            v_scrollbar.config(command=self.canvas.yview)
            h_scrollbar.config(command=self.canvas.xview)
            
            self.canvas.grid(row=0, column=0, sticky="nsew")
            v_scrollbar.grid(row=0, column=1, sticky="ns")
            h_scrollbar.grid(row=1, column=0, sticky="ew")
            
            # Configure scrolling region
            self.canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))
        else:
            self.canvas = tk.Canvas(
                canvas_frame, 
                width=canvas_width,
                height=canvas_height,
                bg=self.colors['panel_bg'],
                highlightthickness=0
            )
            self.canvas.grid(row=0, column=0)
        
        # Bind click events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Enter>", lambda e: self.canvas.config(cursor="hand2"))
        self.canvas.bind("<Leave>", lambda e: self.canvas.config(cursor=""))
        
        # Draw grid
        self.draw_grid()
        
        # Add legend
        legend_frame = tk.Frame(board_frame, bg=self.colors['panel'])
        legend_frame.grid(row=2, column=0, pady=(15, 0))
        
        # Create legend items
        legend_items = [
            ("Unclaimed", self.colors['unclaimed']),
            ("Claimed", self.colors['claimed']),
            ("Your Claim", self.colors['yours']),
            ("Others' Claim", self.colors['others'])
        ]
        
        for i, (text, color) in enumerate(legend_items):
            item_frame = tk.Frame(legend_frame, bg=self.colors['panel'])
            item_frame.grid(row=0, column=i, padx=10)
            
            # Color box
            color_box = tk.Canvas(item_frame, width=20, height=20, 
                                 bg=color, highlightthickness=1,
                                 highlightbackground="#555555")
            color_box.grid(row=0, column=0, padx=(0, 5))
            
            # Label
            label = tk.Label(item_frame, text=text, font=("Arial", 9),
                            fg=self.colors['text'], bg=self.colors['panel'])
            label.grid(row=0, column=1)
        
        # Instructions
        instructions = tk.Label(board_frame, 
                               text="Click on any cell to claim it!",
                               font=("Arial", 10, "italic"),
                               fg=self.colors['accent'],
                               bg=self.colors['panel'])
        instructions.grid(row=3, column=0, pady=(10, 0))
    
    def draw_grid(self):
        # Clear existing grid
        self.canvas.delete("all")
        
        # Draw cells with better styling
        for r in range(self.rows):
            for c in range(self.cols):
                x1 = c * self.cell_size + 20
                y1 = r * self.cell_size + 20
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                
                # Determine cell color and style
                cell_value = self.grid_state[r][c]
                if cell_value == 1:
                    fill_color = self.colors['claimed']  # Green for claimed
                    outline_color = "#2E7D32"  # Darker green border
                    outline_width = 2
                elif cell_value == 2:
                    fill_color = self.colors['yours']  # Blue for your claim
                    outline_color = "#1565C0"  # Darker blue border
                    outline_width = 3
                elif cell_value == 3:
                    fill_color = self.colors['others']  # Orange for others
                    outline_color = "#EF6C00"  # Darker orange border
                    outline_width = 2
                else:
                    fill_color = self.colors['unclaimed']  # Gray for unclaimed
                    outline_color = "#555555"  # Dark gray border
                    outline_width = 1
                
                # Draw cell with rounded corners
                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=fill_color,
                    outline=outline_color,
                    width=outline_width,
                    tags=f"cell_{r}_{c}"
                )
                
                # Add hover effect tags
                self.canvas.tag_bind(f"cell_{r}_{c}", "<Enter>", 
                                   lambda e, r=r, c=c: self.on_cell_hover(r, c))
                self.canvas.tag_bind(f"cell_{r}_{c}", "<Leave>", 
                                   lambda e: self.on_cell_leave())
        
        # Draw grid coordinates for first row and column
        for i in range(self.rows):
            y = i * self.cell_size + 20 + self.cell_size/2
            self.canvas.create_text(10, y, text=str(i), 
                                   fill=self.colors['text'], font=("Arial", 9, "bold"))
        
        for i in range(self.cols):
            x = i * self.cell_size + 20 + self.cell_size/2
            self.canvas.create_text(x, 10, text=str(i), 
                                   fill=self.colors['text'], font=("Arial", 9, "bold"))
        
        # Update info panel
        claimed_count = sum(1 for row in self.grid_state for cell in row if cell > 0)
        total_cells = self.rows * self.cols
        percentage = (claimed_count / total_cells * 100) if total_cells > 0 else 0
        
        info_text = f"📊 Board Status: {claimed_count}/{total_cells} cells claimed ({percentage:.1f}%)"
        canvas_height = self.rows * self.cell_size + 40
        self.canvas.create_text(
            20, canvas_height - 20,
            text=info_text,
            anchor=tk.W,
            font=("Arial", 11, "bold"),
            fill=self.colors['accent']
        )
    
    def on_canvas_click(self, event):
        """Handle canvas click to claim cells"""
        if not self.click_callback:
            self.log_message("Not connected to server", "warning")
            return
        
        # Calculate grid coordinates
        x = event.x
        y = event.y
        
        # Adjust for scroll position if applicable
        if hasattr(self.canvas, 'xview'):
            x += self.canvas.canvasx(0)
            y += self.canvas.canvasy(0)
        
        # Calculate row and column
        col = int((x - 20) / self.cell_size)
        row = int((y - 20) / self.cell_size)
        
        # Check if click is within grid bounds
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.last_clicked = (row, col)
            self.log_message(f"Clicked cell ({row}, {col})", "info")
            
            # Call the click callback (set by client/server)
            if self.click_callback:
                self.click_callback(row, col)
    
    def on_cell_hover(self, row, col):
        """Handle cell hover effect"""
        self.canvas.itemconfig(f"cell_{row}_{col}", width=3)
        self.canvas.config(cursor="hand2")
        
        # Show tooltip
        cell_value = self.grid_state[row][col]
        status = ["Unclaimed", "Claimed", "Your Claim", "Others' Claim"][cell_value if cell_value < 4 else 0]
        self.canvas.create_text(
            col * self.cell_size + 20 + self.cell_size/2,
            row * self.cell_size + 20 - 10,
            text=f"({row}, {col}) - {status}",
            fill=self.colors['text'],
            font=("Arial", 8),
            tags="tooltip"
        )
    
    def on_cell_leave(self):
        """Handle cell leave"""
        self.canvas.delete("tooltip")
    
    def create_control_panel(self, parent):
        """Create control panel with modern styling"""
        # Control frame
        control_frame = tk.Frame(parent, bg=self.colors['panel'], 
                                highlightbackground=self.colors['accent'], 
                                highlightthickness=2, padx=15, pady=15)
        control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        
        # Title
        title_label = tk.Label(control_frame, text="⚙️ CONTROLS", 
                              font=("Arial", 14, "bold"),
                              fg=self.colors['accent'],
                              bg=self.colors['panel'])
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # Player ID display
        id_frame = tk.Frame(control_frame, bg=self.colors['panel'])
        id_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        tk.Label(id_frame, text="Player ID:", font=("Arial", 11),
                fg=self.colors['text'], bg=self.colors['panel'], width=12, anchor="w").grid(row=0, column=0)
        player_id_label = tk.Label(id_frame, textvariable=self.player_id_var, 
                                  font=("Arial", 11, "bold"),
                                  fg=self.colors['accent'], bg=self.colors['panel'])
        player_id_label.grid(row=0, column=1, sticky="w")
        
        # Connection status
        status_frame = tk.Frame(control_frame, bg=self.colors['panel'])
        status_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        
        tk.Label(status_frame, text="Status:", font=("Arial", 11),
                fg=self.colors['text'], bg=self.colors['panel'], width=12, anchor="w").grid(row=0, column=0)
        self.status_label = tk.Label(status_frame, textvariable=self.status_var,
                                    font=("Arial", 11, "bold"),
                                    fg="#FF5252", bg=self.colors['panel'])
        self.status_label.grid(row=0, column=1, sticky="w")
        
        # Control buttons
        button_frame = tk.Frame(control_frame, bg=self.colors['panel'])
        button_frame.grid(row=3, column=0, columnspan=2, pady=(0, 15))
        
        # Style for buttons
        button_style = {
            'font': ("Arial", 10, "bold"),
            'borderwidth': 0,
            'relief': "flat",
            'cursor': "hand2",
            'padx': 20,
            'pady': 8
        }
        
        self.connect_button = tk.Button(
            button_frame, 
            text="🚀 CONNECT",
            command=self._on_connect_click,
            bg=self.colors['button'],
            fg="white",
            activebackground=self.colors['button_hover'],
            activeforeground="white",
            **button_style
        )
        self.connect_button.grid(row=0, column=0, padx=(0, 10))
        
        self.disconnect_button = tk.Button(
            button_frame,
            text="🔌 DISCONNECT",
            command=self._on_disconnect_click,
            bg="#757575",
            fg="white",
            activebackground="#616161",
            activeforeground="white",
            state=tk.DISABLED,
            **button_style
        )
        self.disconnect_button.grid(row=0, column=1)
        
        # Auto-claim toggle
        toggle_frame = tk.Frame(control_frame, bg=self.colors['panel'])
        toggle_frame.grid(row=4, column=0, columnspan=2, pady=(0, 10))
        
        self.auto_check = tk.Checkbutton(
            toggle_frame,
            text="🤖 Auto-claim random cells",
            variable=self.auto_claim_var,
            command=self._on_auto_claim_toggle,
            font=("Arial", 10),
            fg=self.colors['text'],
            bg=self.colors['panel'],
            activebackground=self.colors['panel'],
            activeforeground=self.colors['text'],
            selectcolor=self.colors['panel']
        )
        self.auto_check.grid(row=0, column=0)
        
        # Speed control for auto-claim
        speed_frame = tk.Frame(control_frame, bg=self.colors['panel'])
        speed_frame.grid(row=5, column=0, columnspan=2, pady=(5, 0))
        
        tk.Label(speed_frame, text="Speed:", font=("Arial", 9),
                fg=self.colors['text'], bg=self.colors['panel']).grid(row=0, column=0, padx=(0, 5))
        
        speed_scale = tk.Scale(speed_frame, from_=0.1, to=1.0, resolution=0.1,
                              variable=self.speed_var, orient=tk.HORIZONTAL,
                              length=150, showvalue=False,
                              bg=self.colors['panel'], fg=self.colors['text'],
                              highlightbackground=self.colors['panel'])
        speed_scale.grid(row=0, column=1)
    
    def create_status_panel(self, parent):
        """Create status panel with modern styling"""
        status_frame = tk.Frame(parent, bg=self.colors['panel'], 
                               highlightbackground=self.colors['accent'], 
                               highlightthickness=2, padx=15, pady=15)
        status_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 15))
        
        parent.rowconfigure(1, weight=1)
        
        # Title
        title_label = tk.Label(status_frame, text="📈 STATISTICS", 
                              font=("Arial", 14, "bold"),
                              fg=self.colors['accent'],
                              bg=self.colors['panel'])
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # Statistics items - using the variables that were already initialized
        stats_items = [
            ("📊 Snapshot ID:", self.snapshot_var, "0"),
            ("👥 Active Players:", self.players_var, "0"),
            ("📤 Packets Sent:", self.sent_var, "0"),
            ("📥 Packets Received:", self.received_var, "0"),
            ("❌ Packets Dropped:", self.dropped_var, "0"),
            ("⏱️ Avg Latency:", self.latency_var, "0 ms")
        ]
        
        for i, (label_text, var, default) in enumerate(stats_items):
            # Label
            label = tk.Label(status_frame, text=label_text, font=("Arial", 10),
                            fg=self.colors['text'], bg=self.colors['panel'], anchor="w")
            label.grid(row=i+1, column=0, sticky="w", pady=5)
            
            # Value
            value_label = tk.Label(status_frame, textvariable=var, font=("Arial", 10, "bold"),
                                  fg=self.colors['accent'], bg=self.colors['panel'], anchor="e")
            value_label.grid(row=i+1, column=1, sticky="e", pady=5, padx=(10, 0))
        
        # Progress bar for board coverage
        progress_frame = tk.Frame(status_frame, bg=self.colors['panel'])
        progress_frame.grid(row=len(stats_items)+1, column=0, columnspan=2, pady=(15, 0), sticky="ew")
        
        tk.Label(progress_frame, text="📊 Board Coverage:", font=("Arial", 10),
                fg=self.colors['text'], bg=self.colors['panel']).grid(row=0, column=0, sticky="w")
        
        self.progress = ttk.Progressbar(progress_frame, length=200, mode='determinate')
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        
        # Configure progressbar style
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Horizontal.TProgressbar",
                       background=self.colors['accent'],
                       troughcolor=self.colors['panel_bg'])
        self.progress.configure(style="Horizontal.TProgressbar")
    
    def create_log_panel(self, parent):
        """Create log panel with modern styling"""
        log_frame = tk.Frame(parent, bg=self.colors['panel'], 
                            highlightbackground=self.colors['accent'], 
                            highlightthickness=2, padx=15, pady=15)
        log_frame.grid(row=2, column=0, sticky="nsew")
        
        parent.rowconfigure(2, weight=2)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        
        # Title
        title_label = tk.Label(log_frame, text="📝 EVENT LOG", 
                              font=("Arial", 14, "bold"),
                              fg=self.colors['accent'],
                              bg=self.colors['panel'])
        title_label.grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        # Create scrolled text widget with dark theme
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            width=45,
            height=12,
            font=("Consolas", 9),
            bg=self.colors['log_bg'],
            fg=self.colors['text'],
            insertbackground=self.colors['text'],
            relief="flat",
            borderwidth=0
        )
        self.log_text.grid(row=1, column=0, sticky="nsew")
        
        # Configure tags for different log levels
        self.log_text.tag_config("timestamp", foreground="#888888")
        self.log_text.tag_config("error", foreground="#FF5252", font=("Consolas", 9, "bold"))
        self.log_text.tag_config("success", foreground="#4CAF50", font=("Consolas", 9, "bold"))
        self.log_text.tag_config("info", foreground="#2196F3")
        self.log_text.tag_config("warning", foreground="#FF9800")
        self.log_text.tag_config("system", foreground="#9C27B0")
        
        # Clear log button
        clear_button = tk.Button(log_frame, text="Clear Log", command=self.clear_log,
                                font=("Arial", 9), bg="#616161", fg="white",
                                activebackground="#757575", activeforeground="white",
                                borderwidth=0, padx=10, pady=3, cursor="hand2")
        clear_button.grid(row=2, column=0, sticky="e", pady=(5, 0))
    
    def clear_log(self):
        """Clear the event log"""
        self.log_text.delete(1.0, tk.END)
    
    # Internal callback methods
    def _on_connect_click(self):
        self.log_message("Connect button clicked", "system")
    
    def _on_disconnect_click(self):
        self.log_message("Disconnect button clicked", "system")
    
    def _on_auto_claim_toggle(self):
        if self.auto_claim_var.get():
            self.log_message("Auto-claim enabled", "info")
        else:
            self.log_message("Auto-claim disabled", "info")
    
    # Public methods for setting callbacks
    def set_click_callback(self, callback):
        """Set callback for cell clicks"""
        self.click_callback = callback
    
    def set_connect_callback(self, callback):
        self.connect_button.config(command=callback)
    
    def set_disconnect_callback(self, callback):
        self.disconnect_button.config(command=callback)
    
    def set_auto_claim_callback(self, callback):
        self.auto_check.config(command=callback)
    
    # Thread-safe update methods
    def log_message(self, message, level="info"):
        """Thread-safe method to add messages to log"""
        # Limit log spam - only log important messages
        if level in ["error", "success", "system"] or "snapshot" not in message.lower():
            self.message_queue.put(("log", message, level))
    
    def update_grid(self, grid_data, highlight_cell=None):
        """Thread-safe method to update grid display"""
        self.message_queue.put(("grid", grid_data, highlight_cell))
    
    def update_stats(self, stats):
        """Thread-safe method to update statistics"""
        self.message_queue.put(("stats", stats))
    
    def update_players(self, players):
        """Thread-safe method to update players list"""
        self.message_queue.put(("players", players))
    
    def update_player_info(self, player_id, connected=True):
        """Thread-safe method to update player info"""
        self.message_queue.put(("player_info", player_id, connected))
    
    def update_snapshot(self, snapshot_id):
        """Thread-safe method to update snapshot info"""
        self.message_queue.put(("snapshot", snapshot_id))
    
    def process_queue(self):
        """Process messages from queue in main thread"""
        try:
            while True:
                msg_type, *args = self.message_queue.get_nowait()
                
                if msg_type == "log":
                    message, level = args
                    self._add_log_message(message, level)
                
                elif msg_type == "grid":
                    grid_data, highlight_cell = args
                    self._update_grid_display(grid_data, highlight_cell)
                
                elif msg_type == "stats":
                    self._update_stats_display(args[0])
                
                elif msg_type == "players":
                    self._update_players_display(args[0])
                
                elif msg_type == "player_info":
                    player_id, connected = args
                    self._update_player_info_display(player_id, connected)
                
                elif msg_type == "snapshot":
                    self._update_snapshot_display(args[0])
                
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.process_queue)
    
    def _add_log_message(self, message, level):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.log_text.insert(tk.END, f"{message}\n", level)
        self.log_text.see(tk.END)  # Auto-scroll to bottom
        
        # Limit log size to prevent memory issues
        lines = self.log_text.get(1.0, tk.END).split('\n')
        if len(lines) > 100:  # Keep last 100 lines
            self.log_text.delete(1.0, f"{len(lines)-100}.0")
    
    def _update_grid_display(self, grid_data, highlight_cell=None):
        self.grid_state = grid_data
        self.draw_grid()
    
    def _update_stats_display(self, stats):
        self.packet_stats.update(stats)
        self.sent_var.set(str(self.packet_stats.get('sent', 0)))
        self.received_var.set(str(self.packet_stats.get('received', 0)))
        self.dropped_var.set(str(self.packet_stats.get('dropped', 0)))
        
        latency_count = self.packet_stats.get('latency_count', 0)
        if latency_count > 0:
            avg_latency = self.packet_stats.get('latency_sum', 0) / latency_count
            self.latency_var.set(f"{avg_latency:.1f} ms")
        else:
            self.latency_var.set("0 ms")
        
        # Update progress bar
        claimed_count = sum(1 for row in self.grid_state for cell in row if cell > 0)
        total_cells = self.rows * self.cols
        percentage = (claimed_count / total_cells * 100) if total_cells > 0 else 0
        self.progress['value'] = percentage
    
    def _update_players_display(self, players):
        self.players = players
        self.players_var.set(str(len(players)))
    
    def _update_player_info_display(self, player_id, connected=True):
        if connected:
            if player_id == "Server":
                self.player_id_var.set("🎮 Server")
                self.status_var.set("🟢 Running")
                self.status_label.config(fg="#4CAF50")
                self.connect_button.config(state=tk.DISABLED, text="✅ Server Running")
                self.disconnect_button.config(state=tk.NORMAL, text="🛑 Stop Server")
                self.auto_check.config(state=tk.DISABLED)
            elif player_id == "Connecting...":
                self.player_id_var.set("⏳ Connecting...")
                self.status_var.set("🟡 Connecting")
                self.status_label.config(fg="#FF9800")
                self.connect_button.config(state=tk.DISABLED)
                self.disconnect_button.config(state=tk.NORMAL)
                self.auto_check.config(state=tk.DISABLED)
            else:
                self.player_id_var.set(f"👤 Player {player_id}")
                self.status_var.set("🟢 Connected")
                self.status_label.config(fg="#4CAF50")
                self.connect_button.config(state=tk.DISABLED)
                self.disconnect_button.config(state=tk.NORMAL)
                self.auto_check.config(state=tk.NORMAL)
        else:
            if player_id == "Server":
                self.player_id_var.set("🎮 Server")
                self.status_var.set("🔴 Stopped")
                self.status_label.config(fg="#FF5252")
                self.connect_button.config(state=tk.NORMAL, text="🚀 Start Server")
                self.disconnect_button.config(state=tk.DISABLED, text="🛑 Stop Server")
                self.auto_check.config(state=tk.DISABLED)
            else:
                self.player_id_var.set("👤 Not Connected")
                self.status_var.set("🔴 Disconnected")
                self.status_label.config(fg="#FF5252")
                self.connect_button.config(state=tk.NORMAL)
                self.disconnect_button.config(state=tk.DISABLED)
                self.auto_check.config(state=tk.NORMAL)
    
    def _update_snapshot_display(self, snapshot_id):
        self.snapshot_id = snapshot_id
        self.snapshot_var.set(str(snapshot_id))
    
    def run(self):
        """Start the GUI main loop"""
        self.root.mainloop()
    
    def close(self):
        """Safely close the GUI"""
        if self.root:
            self.root.quit()
            self.root.destroy()


# Test the GUI
if __name__ == "__main__":
    app = GameGUI()
    app.run()