"""
author: deadc0de6 (https://github.com/deadc0de6)
Copyright (c) 2018, deadc0de6
Daemon communication using unix socket
"""

import socket
import select
import sys
import os
import struct

# local import
from cploy.log import Log
from cploy.message import Message as Msg
from cploy.exceptions import *


class Com:

    BUFSZ = 1024
    TIMEOUT = 5
    SZLEN = 4

    def __init__(self, path, debug=False):
        self.path = path
        self.debug = debug
        self.sock = None
        self.cont = True

    def listen(self, callback):
        ''' start listening for message and transmit to callback '''
        try:
            self._listen(callback)
        except KeyboardInterrupt:
            if self.debug:
                Log.debug('interrupted')
        finally:
            self._clean()

    def stop(self):
        ''' stop listening '''
        self.cont = False

    def ping(self):
        ''' ping through unix socket '''
        if self.debug:
            Log.debug('pinging')
        return self.send(Msg.ping)

    def send(self, msg, timeout=None):
        ''' send message through the unix socket '''
        data = None
        if not os.path.exists(self.path):
            err = 'socket does not exist'
            raise ComException(err)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(self.path)
        except socket.error as e:
            err = 'socket error: {}'.format(e)
            raise ComException(e)

        try:
            if self.debug:
                Log.debug('sending \"{}\"'.format(msg))
            self._snd(sock, msg, timeout=timeout)
            data = self._rcv(sock, timeout=timeout)
        except KeyboardInterrupt:
            raise ComException('Interrupted by user')
        except Exception as e:
            Log.err('error when sending message: {}'.format(e))
            raise ComException(e)
        finally:
            sock.close()

        if self.debug:
            Log.debug('receiving \"{}\"'.format(data))
        return data

    def _clean(self):
        ''' clean socket '''
        if self.debug:
            Log.debug('cleaning socket')
        if self.sock:
            self.sock.close()
        if os.path.exists(self.path):
            if self.debug:
                Log.debug('removing socket file {}'.format(self.path))
            os.remove(self.path)

    def _process_msg(self, conn, callback, data):
        ''' process received message '''
        if not data:
            return
        msg = ''
        if self.debug:
            Log.debug('data received: {}'.format(data))
        try:
            msg = callback(data)
        except Exception as e:
            Log.err('starting task failed: {}'.format(e))
        if self.debug:
            Log.debug('sending message back: \"{}\"'.format(msg))
        if not msg:
            msg = Msg.error
        if msg:
            try:
                self._snd(conn, msg, timeout=self.TIMEOUT)
            except Exception as e:
                Log.err('error sending response \"{}\": {}'.format(msg, e))

    def _listen(self, callback):
        ''' listen on unix socket and process command through callback '''
        err = ''
        if os.path.exists(self.path):
            err = 'file \"{}\" exists'.format(self.path)
            if self.debug:
                Log.debug(err)
            raise ComException(err)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(self.path)
        self.sock.listen(1)
        if self.debug:
            Log.debug('start listening ...')

        while self.cont:
            if not os.path.exists(self.path):
                err = 'socket is gone'
                break
            conn, client = self.sock.accept()
            try:
                if self.debug:
                    Log.debug('new connection')
                data = self._rcv(conn, timeout=self.TIMEOUT)
                if not data:
                    conn.close()
                    continue
                # hijack some messages
                if data == Msg.ping:
                    if self.debug:
                        Log.debug('ping received')
                    self._snd(conn, Msg.pong, timeout=self.TIMEOUT)
                    conn.close()
                    continue
                elif data == Msg.stop:
                    if self.debug:
                        Log.debug('stop received')
                    self._process_msg(conn, callback, data)
                    self.cont = False
                elif data == Msg.debug:
                    if self.debug:
                        Log.debug('toggling debug')
                    self.debug = not self.debug
                # process received message
                self._process_msg(conn, callback, data)
            finally:
                # Clean up the connection
                conn.close()

    def _rcv(self, socket, timeout=None):
        ''' timeout aware socket '''
        data = None
        socket.setblocking(0)
        r, w, e = select.select([socket], [], [socket], timeout)
        if not (r or w or e):
            # timeout
            if self.debug:
                Log.debug('receive timeout')
            raise ComException('rcv timeout')
        try:
            for rsock in r:
                if rsock != socket:
                    continue
                if self.debug:
                    Log.debug('receiving data ...')
                data = ''
                blen = rsock.recv(self.SZLEN)
                if not blen:
                    if self.debug:
                        Log.debug('nothing received')
                    continue
                length = struct.unpack('>I', blen)[0]
                while len(data) < length:
                    data += rsock.recv(self.BUFSZ).decode()

            for rsock in e:
                if rsock != socket:
                    continue
                raise ComException(e)
        finally:
            socket.setblocking(1)
        return data

    def _snd(self, socket, data, timeout=None):
        ''' timeout aware socket '''
        socket.setblocking(0)
        r, w, e = select.select([], [socket], [socket], timeout)
        if not (r or w or e):
            if self.debug:
                Log.debug('send timeout')
            raise ComException('snd timeout')
        try:
            for wsock in w:
                if wsock != socket:
                    continue
                if self.debug:
                    Log.debug('sending data ...')
                raw = struct.pack('>I', len(data)) + data.encode()
                wsock.sendall(raw)
            for wsock in e:
                if wsock != socket:
                    continue
                raise ComException(e)
        finally:
            socket.setblocking(1)
        return data
