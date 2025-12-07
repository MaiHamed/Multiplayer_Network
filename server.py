# server.py (simplified)
import socket
import struct
import time
import select
import threading
import tkinter as tk
from protocol import (
    create_header, pack_grid_snapshot, parse_header,
    MSG_TYPE_JOIN_REQ, MSG_TYPE_JOIN_RESP,
    MSG_TYPE_CLAIM_REQ, MSG_TYPE_LEAVE, MSG_TYPE_BOARD_SNAPSHOT
)

class GameServer:
    def __init__(self, ip="127.0.0.1", port=5005):
        self.ip = ip
        self.port = port
        
        self.server_socket = None
        self.clients = {}
        self.next_player_id = 1
        self.seq_num = 0
        self.snapshot_id = 0
        
        self.grid_state = [[0 for _ in range(20)] for _ in range(20)]
        self.running = False
        self.server_thread = None
        
        # Statistics
        self.stats = {
            'sent': 0,
            'received': 0,
            'dropped': 0
        }
        
        # Import GUI
        from gui import GameGUI
        self.gui = GameGUI(title="Grid Game Server")
        
        # Setup callbacks
        self._setup_gui_callbacks()
        
        # Snapshot timing
        self.SNAPSHOT_INTERVAL = 0.033
        self.last_snapshot_time = 0
        self.last_log_time = 0
    
    def _setup_gui_callbacks(self):
        """Setup GUI button callbacks"""
        self.gui.connect_button.config(text="Start Server", command=self.start)
        self.gui.disconnect_button.config(text="Stop Server", command=self.stop)
        
        # Disable auto-claim for server
        self.gui.auto_check.config(state=tk.DISABLED)
    
    def start(self):
        """Start the server"""
        if self.running:
            self.gui.log_message("Server is already running", "warning")
            return False
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            
            # Try to bind to port
            try:
                self.server_socket.bind((self.ip, self.port))
            except OSError:
                self.gui.log_message(f"Port {self.port} is busy, trying alternatives...", "warning")
                for alt_port in range(5006, 5010):
                    try:
                        self.port = alt_port
                        self.server_socket.bind((self.ip, self.port))
                        self.gui.log_message(f"Using port {self.port} instead", "info")
                        break
                    except OSError:
                        continue
                else:
                    raise Exception("No available ports")
            
            self.running = True
            self.server_thread = threading.Thread(target=self._server_loop)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            self.gui.log_message(f"Server started on port {self.port}", "success")
            self.gui.update_player_info("Server", True)
            
            return True
            
        except Exception as e:
            self.gui.log_message(f"Server start error: {e}", "error")
            return False
    
    def stop(self):
        """Stop the server"""
        if not self.running:
            self.gui.log_message("Server is not running", "warning")
            return
        
        self.running = False
        
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        
        self.clients.clear()
        self.next_player_id = 1
        
        self.gui.log_message("Server stopped", "info")
        self.gui.update_player_info("Server", False)
        self.gui.update_players(self.clients)
    
    def _server_loop(self):
        """Main server loop with reduced logging"""
        while self.running:
            current_time = time.time()
            next_snapshot_time = self.last_snapshot_time + self.SNAPSHOT_INTERVAL
            timeout = max(0, next_snapshot_time - current_time) if self.clients else 0.1
            
            readable, _, _ = select.select([self.server_socket], [], [], timeout)
            
            if self.server_socket in readable:
                try:
                    data, addr = self.server_socket.recvfrom(1024)
                    
                    if len(data) < 22:
                        continue
                    
                    try:
                        header = parse_header(data)
                    except:
                        continue
                    
                    self.stats['received'] += 1
                    
                    msg_type = header["msg_type"]
                    
                    if msg_type == MSG_TYPE_JOIN_REQ:
                        player_id = self.next_player_id
                        self.next_player_id += 1
                        
                        self.clients[player_id] = addr
                        
                        # Send response
                        payload = struct.pack("!B", player_id)
                        resp = create_header(MSG_TYPE_JOIN_RESP, self.seq_num, len(payload)) + payload
                        self.server_socket.sendto(resp, addr)
                        self.seq_num += 1
                        self.stats['sent'] += 1
                        
                        # Log only important events
                        self.gui.log_message(f"Player {player_id} joined", "success")
                        self.gui.update_players(self.clients)
                        self.gui.update_stats(self.stats)
                    
                    elif msg_type == MSG_TYPE_CLAIM_REQ:
                        payload = data[22:]
                        if len(payload) >= 2:
                            row, col = struct.unpack("!BB", payload[:2])
                            if 0 <= row < 20 and 0 <= col < 20:
                                self.grid_state[row][col] = 1
                                self.gui.update_grid(self.grid_state)
                    
                    elif msg_type == MSG_TYPE_LEAVE:
                        for pid, client_addr in list(self.clients.items()):
                            if client_addr == addr:
                                del self.clients[pid]
                                self.gui.log_message(f"Player {pid} left", "info")
                                self.gui.update_players(self.clients)
                                break
                
                except Exception:
                    continue
            
            # Send snapshots
            current_time = time.time()
            if self.clients and current_time - self.last_snapshot_time >= self.SNAPSHOT_INTERVAL:
                self._send_snapshot()
                self.last_snapshot_time = current_time
    
    def _send_snapshot(self):
        """Send snapshot to all clients"""
        snapshot_bytes = pack_grid_snapshot(self.grid_state)
        payload_len = len(snapshot_bytes)
        
        header = create_header(MSG_TYPE_BOARD_SNAPSHOT, self.seq_num, payload_len)
        message = header + snapshot_bytes
        
        sent_count = 0
        for pid, addr in list(self.clients.items()):
            try:
                self.server_socket.sendto(message, addr)
                sent_count += 1
            except:
                del self.clients[pid]
        
        if sent_count > 0:
            self.stats['sent'] += sent_count
            self.snapshot_id += 1
            self.seq_num += 1
            
            # Update GUI less frequently
            current_time = time.time()
            if current_time - self.last_log_time > 1.0:  # Update every second
                self.gui.update_snapshot(self.snapshot_id)
                self.gui.update_stats(self.stats)
                self.gui.update_players(self.clients)
                self.last_log_time = current_time
    
    def start_gui(self):
        """Start the GUI"""
        self.gui.run()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--no-gui":
        # Original code
        pass
    else:
        server = GameServer()
        server.start_gui()