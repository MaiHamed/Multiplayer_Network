# client.py (simplified)
import socket
import struct
import time
import random
import threading
import tkinter as tk
from protocol import (
    create_header, parse_header,
    MSG_TYPE_JOIN_REQ, MSG_TYPE_JOIN_RESP,
    MSG_TYPE_CLAIM_REQ, MSG_TYPE_BOARD_SNAPSHOT, MSG_TYPE_LEAVE,
    unpack_grid_snapshot
)

class GameClient:
    def __init__(self, server_ip="127.0.0.1", server_port=5005):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_socket = None
        self.seq_num = 0
        self.player_id = None
        self.running = False
        self.receive_thread = None
        self.auto_claim_thread = None
        
        # Statistics
        self.stats = {
            'sent': 0,
            'received': 0,
            'dropped': 0,
            'latency_sum': 0,
            'latency_count': 0
        }
        
        # Import GUI
        from gui import GameGUI
        self.gui = GameGUI(title="Grid Game Client")
        
        # Keep track of claimed cells
        self.claimed_cells = set()
        
        # Setup callbacks
        self._setup_gui_callbacks()
    
    def _setup_gui_callbacks(self):
        """Setup GUI button callbacks"""
        self.gui.connect_button.config(command=self.connect)
        self.gui.disconnect_button.config(command=self.disconnect)
        
        # Set click callback for grid
        self.gui.set_click_callback(self.on_cell_click)
        
        # Set auto-claim callback
        self.gui.set_auto_claim_callback(self._on_auto_claim_toggle)
    
    def connect(self):
        """Connect to server"""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.client_socket.settimeout(2.0)
            
            self.gui.log_message(f"Connecting to server at {self.server_ip}:{self.server_port}", "info")
            
            # Send join request
            join_req = create_header(MSG_TYPE_JOIN_REQ, self.seq_num, 0)
            self.client_socket.sendto(join_req, (self.server_ip, self.server_port))
            self.seq_num += 1
            self.stats['sent'] += 1
            
            self.gui.log_message("JOIN_REQUEST sent to server", "info")
            self.gui.update_player_info("Connecting...", True)
            
            # Start receive thread
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            return True
            
        except Exception as e:
            self.gui.log_message(f"Connection error: {e}", "error")
            self.gui.update_player_info(None, False)
            return False
    
    def disconnect(self):
        """Disconnect from server"""
        self.running = False
        
        if self.auto_claim_thread and self.auto_claim_thread.is_alive():
            self.auto_claim_thread.join(timeout=1)
        
        if self.client_socket:
            # Send leave message
            leave_msg = create_header(MSG_TYPE_LEAVE, self.seq_num, 0)
            self.client_socket.sendto(leave_msg, (self.server_ip, self.server_port))
            self.seq_num += 1
            self.stats['sent'] += 1
            
            self.client_socket.close()
            self.client_socket = None
        
        self.gui.update_player_info(None, False)
        self.gui.log_message("Disconnected from server", "info")
    
    def on_cell_click(self, row, col):
        """Handle cell click from GUI"""
        if not self.client_socket or not self.running:
            self.gui.log_message("Not connected to server", "warning")
            return
        
        if self.player_id is None:
            self.gui.log_message("Not joined to game yet", "warning")
            return
        
        self._send_claim_request(row, col)
    
    def _send_claim_request(self, row, col):
        """Send claim request to server"""
        try:
            payload = struct.pack("!BB", row, col)
            claim_req = create_header(MSG_TYPE_CLAIM_REQ, self.seq_num, len(payload)) + payload
            self.client_socket.sendto(claim_req, (self.server_ip, self.server_port))
            self.seq_num += 1
            self.stats['sent'] += 1
            
            self.claimed_cells.add((row, col))
            self.gui.log_message(f"Claimed cell ({row}, {col})", "success")
            
            # Update GUI stats
            self.gui.update_stats(self.stats)
            
            return True
            
        except Exception as e:
            self.gui.log_message(f"Claim error: {e}", "error")
            return False
    
    def _start_auto_claim(self):
        """Start auto-claiming random cells"""
        def auto_claim_loop():
            self.gui.log_message("Auto-claim started", "info")
            while self.running and self.gui.auto_claim_var.get():
                try:
                    # Get auto-claim speed from GUI
                    speed = self.gui.speed_var.get()
                    
                    # Try to claim a random unclaimed cell
                    for _ in range(10):
                        row, col = random.randint(0, 19), random.randint(0, 19)
                        if (row, col) not in self.claimed_cells:
                            self._send_claim_request(row, col)
                            break
                    
                    time.sleep(speed)  # Use speed from GUI slider
                    
                except Exception as e:
                    self.gui.log_message(f"Auto-claim error: {e}", "error")
                    time.sleep(1)
        
        self.auto_claim_thread = threading.Thread(target=auto_claim_loop)
        self.auto_claim_thread.daemon = True
        self.auto_claim_thread.start()
    
    def _receive_loop(self):
        """Receive messages from server"""
        self.gui.log_message("Receive thread started", "info")
        
        join_timeout = 10
        join_start_time = time.time()
        join_received = False
        
        while self.running:
            try:
                data, addr = self.client_socket.recvfrom(2048)
                
                if len(data) < 22:
                    continue
                
                try:
                    header = parse_header(data)
                except:
                    continue
                
                self.stats['received'] += 1
                
                msg_type = header["msg_type"]
                
                if msg_type == MSG_TYPE_JOIN_RESP:
                    if len(data) >= 23:
                        self.player_id = struct.unpack("!B", data[22:23])[0]
                        self.gui.update_player_info(self.player_id, True)
                        self.gui.log_message(f"Successfully joined as Player {self.player_id}", "success")
                        join_received = True
                        
                        # Start auto-claim if enabled
                        if self.gui.auto_claim_var.get():
                            self._start_auto_claim()
                
                elif msg_type == MSG_TYPE_BOARD_SNAPSHOT:
                    if not join_received:
                        continue
                    
                    snapshot_id = header.get("seq_num", 0)
                    
                    # Unpack grid
                    payload = data[22:]
                    if len(payload) >= 200:
                        grid = unpack_grid_snapshot(payload)
                        
                        # Highlight our claimed cells
                        for r in range(20):
                            for c in range(20):
                                if grid[r][c] == 1 and (r, c) in self.claimed_cells:
                                    grid[r][c] = 2
                        
                        self.gui.update_grid(grid)
                        self.gui.update_snapshot(snapshot_id)
                        self.gui.update_stats(self.stats)
                
            except socket.timeout:
                if not join_received and time.time() - join_start_time < join_timeout:
                    continue
                elif not join_received:
                    self.gui.log_message("Server connection timeout", "error")
                    self.disconnect()
                    break
                else:
                    continue
            except Exception as e:
                if self.running:
                    continue  # Silent error handling
    
    def _on_auto_claim_toggle(self):
        """Handle auto-claim toggle"""
        if self.gui.auto_claim_var.get():
            self.gui.log_message("Auto-claim enabled", "info")
            if self.running and self.player_id:
                self._start_auto_claim()
        else:
            self.gui.log_message("Auto-claim disabled", "info")
    
    def start(self):
        """Start the client GUI"""
        self.gui.run()


# Run client with GUI
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--no-gui":
        # Original non-GUI code here
        pass
    else:
        client = GameClient()
        client.start()