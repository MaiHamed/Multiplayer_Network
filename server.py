# server.py - SR ARQ with snapshot_id for late-joining clients
import socket
import struct
import time
import select
import threading
from protocol import (
    create_header, pack_grid_snapshot, parse_header,
    MSG_TYPE_JOIN_REQ, MSG_TYPE_JOIN_RESP,
    MSG_TYPE_CLAIM_REQ, MSG_TYPE_LEAVE, MSG_TYPE_BOARD_SNAPSHOT,
    MSG_TYPE_ACK, MSG_TYPE_GAME_START, MSG_TYPE_GAME_OVER
)

def current_time_ms():
    return int(time.time() * 1000)

class GameServer:
    def __init__(self, ip="127.0.0.1", port=5005):
        self.ip = ip
        self.port = port
        self.server_socket = None
        self.clients = {}  # player_id -> (addr, last_seen)
        self.waiting_room_players = {}  # player_id -> addr
        self.seq_num = 0  # overall seq num
        self.snapshot_id = 0  # incremental snapshot ID
        self.grid_state = [[0]*20 for _ in range(20)]
        self.game_active = False
        self.min_players = 2
        self.running = False
        self.SNAPSHOT_INTERVAL = 0.033
        self.last_snapshot_time = time.time()
<<<<<<< HEAD
        
        # Statistics
        self.stats = {
            'sent': 0,
            'received': 0,
            'dropped': 0,
            'client_count': 0
        }
        
        # Import GUI
        from gui import GameGUI
        self.gui = GameGUI(title="Grid Game Server")
        self._setup_gui_callbacks()

        self.allow_cell_stealing = True  # Default: allow stealing
        
        # Also add to stats for GUI:
        self.stats = {
            'sent': 0,
            'received': 0,
            'dropped': 0,
            'client_count': 0,
            'allow_stealing': True  # Add this
        }
    
    def _setup_gui_callbacks(self):
        """Setup GUI button callbacks for server"""
        self.gui.connect_button.config(text="Start Server", command=self.start)
        self.gui.disconnect_button.config(text="Stop Server", command=self.stop)
        
        # Override the GUI's callback methods
        self.gui.on_connect_click = self.start
        self.gui.on_disconnect_click = self.stop
    
=======
        self.stats = {'sent':0,'received':0,'dropped':0,'client_count':0}

        # SR ARQ per client
        self.N = 6
        self.client_windows = {}  # player_id -> {seq_num: packet}
        self.client_timers = {}   # player_id -> {seq_num: timestamp}
        self.client_next_seq = {} # player_id -> next seq num
        self.RTO = 200  # default RTO ms

    # ==================== Server Start/Stop ====================
>>>>>>> 40126e1ecaa522e46e5dbf044e06d7ad0b8cd395
    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.setblocking(0)
        self.server_socket.bind((self.ip,self.port))
        self.running = True
        threading.Thread(target=self._server_loop, daemon=True).start()
        print(f"[INFO] Server started at {self.ip}:{self.port}")

    def stop(self):
        self.running = False
        if self.server_socket: self.server_socket.close()
        self.clients.clear()
        self.waiting_room_players.clear()
        print("[INFO] Server stopped.")

    # ==================== SR ARQ Sender ====================
    def _sr_send(self, player_id, msg_type, payload=b''):
        """Send a packet with SR ARQ reliability per client"""
        if player_id not in self.client_next_seq:
            self.client_next_seq[player_id] = 0
            self.client_windows[player_id] = {}
            self.client_timers[player_id] = {}

        next_seq = self.client_next_seq[player_id]
        window = self.client_windows[player_id]

        if len(window) < self.N:
            packet = create_header(msg_type, next_seq, len(payload)) + payload
            addr = self.clients[player_id][0]
            self.server_socket.sendto(packet, addr)
            window[next_seq] = packet
            self.client_timers[player_id][next_seq] = current_time_ms()
            self.client_next_seq[player_id] += 1
            self.stats['sent'] += 1
            print(f"[SEND] to player {player_id} seq={next_seq}, type={msg_type}, window={list(window.keys())}")
        else:
            self.stats['dropped'] += 1
            print(f"[DROPPED] to player {player_id}, window full")

    def _retransmit(self):
        """Check all client timers and retransmit if RTO exceeded"""
        now = current_time_ms()
        for pid in list(self.client_timers.keys()):
            timers = self.client_timers[pid]
            window = self.client_windows[pid]
            addr = self.clients.get(pid, (None,))[0]
            if not addr: continue
            for seq, ts in list(timers.items()):
                if now - ts >= self.RTO:
                    self.server_socket.sendto(window[seq], addr)
                    timers[seq] = now
                    self.stats['sent'] += 1
                    print(f"[RETRANSMIT] to player {pid} seq={seq}")

    # ==================== Server Loop ====================
    def _server_loop(self):
        while self.running:
            try:
                ready, _, _ = select.select([self.server_socket], [], [], 0.01)
                if ready:
                    data, addr = self.server_socket.recvfrom(2048)
                    if len(data) < 22: continue
                    self._handle_message(data, addr)

                # periodic snapshot
                if self.clients and time.time() - self.last_snapshot_time >= self.SNAPSHOT_INTERVAL:
                    self._send_snapshot()
                    self.last_snapshot_time = time.time()

                # handle retransmissions
                self._retransmit()
            except:
                time.sleep(0.01)

    # ==================== Handle Messages ====================
    def _handle_message(self, data, addr):
<<<<<<< HEAD
        try:
            header = parse_header(data)
            msg_type = header["msg_type"]
            seq_num = header.get("seq_num", 0)
            
            self.stats['received'] += 1
            
            if msg_type == MSG_TYPE_JOIN_REQ:
                # Check if game is already active
                if self.game_active:
                    self.gui.log_message("Game already active, rejecting join", "warning")
                    return
                
                # Assign new player ID
                new_player_id = 1
                while new_player_id in self.waiting_room_players:
                    new_player_id += 1
                
                self.waiting_room_players[new_player_id] = addr
                self.stats['client_count'] = len(self.waiting_room_players)
                
                self.gui.log_message(f"Player {new_player_id} joined waiting room", "success")
                
                # Send join response
                payload = struct.pack("!B", new_player_id)
                resp = create_header(MSG_TYPE_JOIN_RESP, self.seq_num, len(payload)) + payload
                self.server_socket.sendto(resp, addr)
                self.seq_num += 1
                self.stats['sent'] += 1
                
                # Check if we have enough players to start
                if len(self.waiting_room_players) >= self.min_players and not self.game_active:
                    self._start_game()
                
                # Update GUI
                self.gui.update_players(self.waiting_room_players)
                self.gui.update_stats(self.stats)
            
            elif msg_type == MSG_TYPE_CLAIM_REQ:
                # Find player ID
                player_id = None
                for pid, (client_addr, _) in self.clients.items():
                    if client_addr == addr:
                        player_id = pid
                        break
                
                if player_id:
                    payload = data[22:]
                    if len(payload) >= 2:
                        row, col = struct.unpack("!BB", payload[:2])
                        if 0 <= row < 20 and 0 <= col < 20:
                            old_owner = self.grid_state[row][col]
                            
                            # Check if stealing is allowed
                            # Only allow claim if: cell is unclaimed OR stealing is enabled
                            if old_owner == 0 or self.allow_cell_stealing:
                                # Process the claim
                                self.grid_state[row][col] = player_id
                                self.gui.update_grid(self.grid_state)
                                
                                # Log the claim
                                if old_owner == 0:
                                    self.gui.log_message(f"Player {player_id} claimed cell ({row},{col})", "info")
                                else:
                                    self.gui.log_message(f"Player {player_id} stole cell ({row},{col}) from Player {old_owner}", "warning")
                            else:
                                # Cell already claimed and stealing not allowed
                                self.gui.log_message(f"Player {player_id} tried to claim owned cell ({row},{col}) - stealing disabled", "warning")
                    
                    # Update client's last seen time
                    if player_id in self.clients:
                        self.clients[player_id] = (addr, time.time())
            
            elif msg_type == MSG_TYPE_LEAVE:
                # Remove client
                to_remove = []
                for pid, (client_addr, _) in self.clients.items():
                    if client_addr == addr:
                        to_remove.append(pid)
                
                for pid in to_remove:
                    del self.clients[pid]
                    self.gui.log_message(f"Player {pid} left", "info")
                
                self.stats['client_count'] = len(self.clients)
                self.gui.update_players(self.clients)
                self.gui.update_stats(self.stats)
            
            # Update stats in GUI
            self.gui.update_stats(self.stats)
        
        except Exception as e:
            self.gui.log_message(f"Message handling error: {e}", "error")
    
=======
        header = parse_header(data)
        msg_type = header["msg_type"]
        seq = header["seq_num"]
        self.stats['received'] += 1
        print(f"[RECEIVED] seq={seq}, type={msg_type}, from={addr}")

        # Send ACK for reliability
        ack_packet = create_header(MSG_TYPE_ACK, seq, 0)
        self.server_socket.sendto(ack_packet, addr)
        print(f"[SEND ACK] seq={seq}, to={addr}")

        if msg_type == MSG_TYPE_JOIN_REQ:
            # Assign new player_id
            new_pid = 1
            while new_pid in self.waiting_room_players: new_pid += 1
            self.waiting_room_players[new_pid] = addr
            self.stats['client_count'] = len(self.waiting_room_players)
            payload = struct.pack("!B", new_pid)
            self._sr_send(new_pid, MSG_TYPE_JOIN_RESP, payload)
            self.seq_num += 1

            if len(self.waiting_room_players) >= self.min_players and not self.game_active:
                self._start_game()

        elif msg_type == MSG_TYPE_CLAIM_REQ:
            player_id = self._addr_to_pid(addr)
            if player_id:
                r, c = struct.unpack("!BB", data[22:24])
                self.grid_state[r][c] = player_id
                print(f"[CLAIM] player {player_id} -> cell ({r},{c})")

        elif msg_type == MSG_TYPE_LEAVE:
            player_id = self._addr_to_pid(addr)
            if player_id:
                self._remove_player(player_id)
                print(f"[LEAVE] player {player_id}")

        elif msg_type == MSG_TYPE_ACK:
            player_id = self._addr_to_pid(addr)
            if player_id:
                window = self.client_windows.get(player_id, {})
                timers = self.client_timers.get(player_id, {})
                if seq in window:
                    del window[seq]
                    del timers[seq]
                    print(f"[ACK RECEIVED] from player {player_id} seq={seq}")

    # ==================== Helper ====================
    def _addr_to_pid(self, addr):
        for pid, a in self.clients.items():
            if a[0] == addr:
                return pid
        for pid, a in self.waiting_room_players.items():
            if a == addr:
                return pid
        return None

    def _remove_player(self, player_id):
        self.clients.pop(player_id, None)
        self.client_windows.pop(player_id, None)
        self.client_timers.pop(player_id, None)
        self.client_next_seq.pop(player_id, None)

    # ==================== Snapshot ====================
>>>>>>> 40126e1ecaa522e46e5dbf044e06d7ad0b8cd395
    def _send_snapshot(self):
        snapshot_bytes = pack_grid_snapshot(self.grid_state)
        payload = struct.pack("!I", self.snapshot_id) + snapshot_bytes
        for pid in self.clients.keys():
            self._sr_send(pid, MSG_TYPE_BOARD_SNAPSHOT, payload)
        self.snapshot_id += 1
        print(f"[SNAPSHOT] id={self.snapshot_id}")

    # ==================== Start Game ====================
    def _start_game(self):
        self.game_active = True
        self.clients.update(self.waiting_room_players)
        self.waiting_room_players.clear()
        for pid in self.clients.keys():
            self._sr_send(pid, MSG_TYPE_GAME_START)
        print("[GAME STARTED]")

    # ==================== End Game ====================
    def end_game(self):
        self.game_active = False
        for pid in self.clients.keys():
            self._sr_send(pid, MSG_TYPE_GAME_OVER)
        print("[GAME OVER]")
