import socketio
from datetime import datetime
from threading import Thread
from prometheus_client import Gauge, Counter, start_http_server
import time

class PoolScraper():
    """
    Scraper for 0xBitcoin pools (mike.rs, rosti, hashxchange)
    Exports the data as prometheus metrics
    """
    POLL_INTERVAL = 30
    
    def __init__(self, url, address):
        """
        url -- The url of the pool websocket (including port)
        address -- The ethereum address being mined to
        """
        self.sio = socketio.Client()
        self.url = url
        self.mining_address = address

        #Setup metrics
        self.pool_hashrate = Gauge('pool_hashrate', 'Reported poolside hashrate')

        #Setup hooks
        self.sio.on('minerDetails', self.miner_details)
        self.sio.on('connect', self.connected)
        self.sio.on('disconnect', self.disconnected)

    def connected(self):
        print("CONNECTED")

    def disconnected(self):
        print("DISCONNECTED")

    def miner_details(self, data):
        if data:
            hr = data['hashRate']
            print(hr)
            if hr:
                #Divide by 1000000000 to convert from H -> GH
                hashrate = int(data['hashRate'])/1000000000.0
            else:
                hashrate = 0
            #update metrics
            self.pool_hashrate.set(hashrate)
        else:
            #Data is None if there is no hashrate data for this address.
            #Could happen when first mining to a pool.. so wait for X mins
            #and then error out, where x is around 30 mins
            print("ERROR FROM POOL")

    def start(self):
        self.sio.connect(self.url)
        msg = "getMinerDetails"
        data = {'address': self.mining_address}

        last_emit = datetime.now()
        self.sio.emit(msg, data)
        while True:
            self.sio.sleep(PoolScraper.POLL_INTERVAL)
            t = datetime.now()
            since_last = t - last_emit
            last_emit = t
            self.sio.emit(msg, data)


if __name__ == "__main__":
    METRICS_PORT = 9090
    METRICS_INTERVAL = 30

    #The URL of the pool
    POOL="http://0xbtc.extremehash.io"
    PORT="2095" #This is the same for every pool I've tried
    #The eth address to monitor
    ETHADDR='0x2D7B4F0F880Ea6e7f7968C1D36E3A8A953d7eb22'

    start_http_server(METRICS_PORT)
    ps = PoolScraper('{}:{}'.format(POOL, PORT), ETHADDR)
    ps.start()


