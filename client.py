# client.py - Updated with SR ARQ and waiting room support
import socket
import struct
import time
import threading
import random
from protocol import (
    create_header, parse_header,
    MSG_TYPE_JOIN_REQ, MSG_TYPE_JOIN_RESP,
    MSG_TYPE_CLAIM_REQ, MSG_TYPE_BOARD_SNAPSHOT, MSG_TYPE_LEAVE,
    MSG_TYPE_GAME_START, MSG_TYPE_GAME_OVER,
    unpack_grid_snapshot, MSG_TYPE_ACK
)

def current_time_ms():
    return int(time.time() * 1000)

class GameClient:
    def __init__(self, server_ip="127.0.0.1", server_port=5005):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_socket = None
        self.running = False

        # SR ARQ
        self.N = 6
        self.base = 0
        self.nextSeqNum = 0
        self.window = {}
        self.timers = {}
        self.send_timestamp = {}
        self.estimatedRTT = 100
        self.devRTT = 50
        self.alpha = 0.125
        self.beta = 0.25
        self.RTO = self.estimatedRTT + 4*self.devRTT

        self.player_id = None
        self.game_active = False
        self.stats = {'sent':0,'received':0,'dropped':0}

    # ==================== SR ARQ ====================
    def _sr_send(self, msg_type, payload=b''):
        if self.nextSeqNum < self.base + self.N:
            seq = self.nextSeqNum
            packet = create_header(msg_type, seq, len(payload)) + payload
            self.client_socket.sendto(packet, (self.server_ip, self.server_port))
            self.window[seq] = packet
            self.timers[seq] = current_time_ms()
            self.send_timestamp[seq] = current_time_ms()
            self.nextSeqNum += 1
            self.stats['sent'] += 1
            print(f"[SEND] seq={seq}, type={msg_type}, window={list(self.window.keys())}")
            return True
        else:
            self.stats['dropped'] += 1
            print(f"[DROPPED] seq={self.nextSeqNum}, window full")
            return False

    def _retransmit(self, seq):
        packet = self.window.get(seq)
        if packet:
            self.client_socket.sendto(packet, (self.server_ip, self.server_port))
            self.timers[seq] = current_time_ms()
            self.stats['sent'] += 1
            print(f"[RETRANSMIT] seq={seq}")

    def _timer_loop(self):
        while self.running:
            now = current_time_ms()
            for seq in list(self.timers.keys()):
                if now - self.timers[seq] >= self.RTO:
                    self._retransmit(seq)
            time.sleep(0.01)

    # ==================== Network ====================
    def connect(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.settimeout(1.0)
        self.running = True
        threading.Thread(target=self._timer_loop, daemon=True).start()
        threading.Thread(target=self._receive_loop, daemon=True).start()
        self._sr_send(MSG_TYPE_JOIN_REQ)

    def _receive_loop(self):
        while self.running:
            try:
                data, addr = self.client_socket.recvfrom(2048)
                recv_ms = current_time_ms()
                header = parse_header(data)
                self.stats['received'] += 1
                seq = header["seq_num"]
                msg_type = header["msg_type"]

                # Handle ACK
                if msg_type == MSG_TYPE_ACK:
                    if seq in self.window:
                        sampleRTT = recv_ms - self.send_timestamp.get(seq, recv_ms)
                        self.estimatedRTT = (1-self.alpha)*self.estimatedRTT + self.alpha*sampleRTT
                        self.devRTT = (1-self.beta)*self.devRTT + self.beta*abs(sampleRTT - self.estimatedRTT)
                        self.RTO = self.estimatedRTT + 4*self.devRTT
                        del self.window[seq]
                        del self.timers[seq]
                        del self.send_timestamp[seq]
                        while self.base not in self.window and self.base < self.nextSeqNum:
                            self.base += 1
                        print(f"[ACK RECEIVED] seq={seq}")
                    continue

                # Send ACK
                ack_packet = create_header(MSG_TYPE_ACK, seq, 0)
                self.client_socket.sendto(ack_packet, addr)

            except socket.timeout:
                continue
