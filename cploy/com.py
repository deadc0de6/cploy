"""
author: deadc0de6 (https://github.com/deadc0de6)
Copyright (c) 2018, deadc0de6
Daemon communication using unix socket
"""

import socket
import select
import sys
import os

# local import
from cploy.log import Log
from cploy.message import Message as Msg
from cploy.exceptions import *


class Com:

    BUFSZ = 1024
    TIMEOUT = 5

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
            self._debug('interrupted')
        finally:
            self._clean()

    def stop(self):
        ''' stop listening '''
        self.cont = False

    def ping(self):
        ''' ping through unix socket '''
        self._debug('pinging')
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
            self._debug('sending \"{}\"'.format(msg))
            self._snd(sock, msg, timeout=timeout)
            data = self._rcv(sock, timeout=timeout)
        except Exception as e:
            raise ComException(e)
        finally:
            sock.close()

        self._debug('receiving \"{}\"'.format(data))
        return data

    def _clean(self):
        ''' clean socket '''
        self._debug('cleaning socket')
        if self.sock:
            self.sock.close()
        if os.path.exists(self.path):
            self._debug('removing socket file {}'.format(self.path))
            os.remove(self.path)

    def _process_msg(self, conn, callback, data):
        ''' process received message '''
        if not data:
            return
        msg = ''
        self._debug('data received: {}'.format(data))
        try:
            msg = callback(data)
        except Exception as e:
            Log.err('error starting task: {}'.format(e))
        self._debug('sending message back: {}'.format(msg))
        if msg:
            try:
                self._snd(conn, msg, timeout=self.TIMEOUT)
            except Exception as e:
                Log.err('error starting task: {}'.format(e))

    def _listen(self, callback):
        ''' listen on unix socket and process command through callback '''
        err = ''
        if os.path.exists(self.path):
            err = 'file \"{}\" exists'.format(self.path)
            self._debug(err)
            raise ComException(err)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(self.path)
        self.sock.listen(1)
        self._debug('start listening ...')

        while self.cont:
            if not os.path.exists(self.path):
                err = 'socket is gone'
                break
            conn, client = self.sock.accept()
            try:
                self._debug('new connection')
                data = self._rcv(conn, timeout=self.TIMEOUT)
                if not data:
                    conn.close()
                    continue
                # hijack some messages
                if data == Msg.ping:
                    self._debug('ping received')
                    self._snd(conn, Msg.pong, timeout=self.TIMEOUT)
                    conn.close()
                    continue
                elif data == Msg.stop:
                    self._debug('stop received')
                    self._process_msg(conn, callback, data)
                    self.cont = False
                elif data == Msg.debug:
                    self._debug('toggling debug')
                    self.debug = not self.debug
                # process received message
                self._process_msg(conn, callback, data)
            finally:
                # Clean up the connection
                conn.close()
        self._clean()

    def _rcv(self, socket, timeout=None):
        ''' timeout aware socket '''
        data = None
        socket.setblocking(0)
        r, w, e = select.select([socket], [], [socket], timeout)
        if not (r or w or e):
            # timeout
            self._debug('receive timeout')
            raise ComException('rcv timeout')
        self._debug('send select {} {}'.format(r, e))
        try:
            for rsock in r:
                if rsock != socket:
                    continue
                self._debug('receiving data ...')
                data = rsock.recv(self.BUFSZ).decode()
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
            self._debug('send timeout')
            raise ComException('snd timeout')
        self._debug('send select {} {}'.format(w, e))
        try:
            for wsock in w:
                if wsock != socket:
                    continue
                self._debug('sending data ...')
                wsock.sendall(data.encode())
            for wsock in e:
                if wsock != socket:
                    continue
                raise ComException(e)
        finally:
            socket.setblocking(1)
        return data

    def _debug(self, msg):
        if not self.debug:
            return
        Log.debug(msg)
