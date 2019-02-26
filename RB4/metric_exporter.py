from prometheus_client import Gauge, Counter, start_http_server, registry

from argparse import ArgumentParser
from datetime import datetime, timedelta
import sys
import os
import time
import logging as pylogging

class ExporterError(Exception):
    pass

class MinerMetrics():
    def __init__(self, export_python_metrics=False):
        self.hashrate = Gauge('hashrate', 'Hashrate (GH/S)', ['card'])
        self.clock_speed = Gauge('clock_speed', 'Clock Speed (MHz)', ['card'])
        self.temperature = Gauge('temperature', 'Temperature (C)', ['card'])
        self.voltage = Gauge('voltage', 'VINT Voltage', ['card'])
        self.errors = Gauge('errors', 'Errors (%)', ['card'])
        self.last_updated = Gauge('last_update', 'Last updated', ['card'])
        self.solutions_good = Gauge('solutions_good', 'good solutions', ['card'])
        self.solutions_total = Gauge('solutions_total', 'total solutions', ['card'])

        #We use our own registry to stop prometheus_client exporting extra stats
        if export_python_metrics:
            self.registry = registry.REGISTRY
        else:
            self.registry = registry.CollectorRegistry()
            self.registry.register(self.hashrate)
            self.registry.register(self.clock_speed)
            self.registry.register(self.temperature)
            self.registry.register(self.voltage)
            self.registry.register(self.errors)
            self.registry.register(self.last_updated)
            self.registry.register(self.solutions_good)
            self.registry.register(self.solutions_total)

    def start_http_server(self, port=9090):
        start_http_server(port, registry=self.registry)

class RB4MinerParser():
    """
    Parses the RB4 miner output

    miner_output - Miner input, must provide readlines() 
    cardname - The card name to be used as a metric label
    """
    def __init__(self, miner_output, cardname, logging=True):
        #Check that we aren't already exporting with this metric name
        self.miner = miner_output
        self.name = cardname
        self.logging = True

        #Setup logging
        if self.logging:
            logname = "RB4Parser-{}".format(self.name)
            self.log = pylogging.getLogger(logname)
            fh = pylogging.FileHandler('{}.log'.format(logname), 'a')
            formatter = pylogging.Formatter('%(asctime)s - %(message)s')
            fh.setFormatter(formatter)
            self.log.addHandler(fh)
            self.log.setLevel(pylogging.DEBUG)
            self.log.info("New instance of parser started")

    def parse_stats(self, metrics):
        """
        Reads all unread data from miner_output and updates metrics

        metrics - MinerMetric object
        """
        lines = self.miner.readlines()
        if not lines:
            #TODO if no output for X attempts raise an error
            self.logging and self.log.warning("No output from miner")
            return False

        self.logging and self.log.info("Recieved {} lines from miner".format(len(lines)))
        #TODO: a better way to check for hashrate lines
        def is_hashrate(line):
            if len(line.split()) is 12:
                return True
            else:
                return False

        #Loop through all lines, logging and getting latest hashrate numbers
        last_stats = None
        for line in lines:
            if is_hashrate(line):
                last_stats = line
            else:
                #log everything else at the debug level
                sline = line.strip()
                if sline is not None:
                    self.logging and self.log.debug(sline)

        if last_stats is None:
            self.logging and self.log.info("No hashrate information")
            return

        recent_stats = last_stats.split()

        #parse the stats
        #TODO: better way to the values from the units.
        try:
            metrics.hashrate.labels(self.name).set(recent_stats[2][:-4])
            metrics.clock_speed.labels(self.name).set(recent_stats[3][1:-4])
            metrics.errors.labels(self.name).set(recent_stats[5][:-1])
            metrics.temperature.labels(self.name).set(recent_stats[6][:-1])
            metrics.voltage.labels(self.name).set(recent_stats[7][:-1])
            sol_good, sol_total = recent_stats[9].split('/')
            metrics.solutions_good.labels(self.name).set(sol_good)
            metrics.solutions_total.labels(self.name).set(sol_total)
            metrics.last_updated.labels(self.name).set(int(datetime.now().timestamp()))
        except IndexError:
            self.logging and self.log.error("Index Error when parsing .. {}".format(recent_stats))
        except ValueError:
            self.logging and self.log.error("Value error when parsing .. {}".format(recent_stats))

class BitstreamLogExporter():
    """
    Reads miner out from a file and uses RB4MinerParser to parse the output"

    prometheus http server be launched elsewhere
    """
    def __init__(self, interval, log_paths=['fpga.log',], card_names=['fpga',], logging=True, port=9090):
        self.logging = logging
        self.port = port
        self.metrics = MinerMetrics()
        self.interval = interval
        self.log_paths = log_paths
        self.card_names = card_names
        logs = len(log_paths)
        cards = len(card_names)
        if logs > 1:
         if logs != cards:
             raise ExporterError("{} log paths but only {} cards".format(logs, cards))

    def start(self):
        self.metrics.start_http_server(port=self.port)
        #Initialise the parser(s)
        parsers = []
        self.open_logs = []
        for logpath, name in zip(self.log_paths, self.card_names):
            try:
                log_handle = open(logpath, 'r')
            except:
                #TODO: an error message?
                raise
            self.open_logs.append(log_handle)
            parsers.append(RB4MinerParser(log_handle, name, logging=self.logging))

        #Loop forever
        #TODO: close the files? who cares?
        while True:
            for parser in parsers:
                parser.parse_stats(self.metrics)
            time.sleep(self.interval)

            
def main():
    DEFAULT_METRICS_PORT = 9090
    DEFAULT_METRICS_INTERVAL = 30
    DEFAULT_LABEL = "card{}"

    argparse = ArgumentParser(description='fx-tokenminer metric exporter')
    argparse.add_argument('--minerlogpaths', '-m', nargs='+', 
                          help="List of miner log paths to parse", metavar='path',
                          required=True)
    argparse.add_argument('--cardnames', '-c', nargs='+', 
                          help="List of card names to use as metric labels", metavar='label')
    argparse.add_argument('--port', '-p', type=int, help='Port webserver will run on',
                          default=DEFAULT_METRICS_PORT)
    argparse.add_argument('--interval', '-i', type=int, 
                          help='Time in seconds between updating metrics',
                          default=DEFAULT_METRICS_INTERVAL)
    argparse.add_argument('--logging',  '-l', action="store_true",
                          help='Enable logging of non hashrate messages to a file',
                          default=True)
    
   
    args = argparse.parse_args()
    paths = args.minerlogpaths
    #Initialise to empty list if not set so we can len() it
    cards = args.cardnames or []

    #Check that we have the same number of paths as card names, and if we don't use default labels
    if len (paths) > len(cards):
        print("{} log paths provided but no label names.. Using default label {}".format(len(paths),
                                                                                         DEFAULT_LABEL))
        cards = []
        for i in range(len(paths)):
            cards.append(DEFAULT_LABEL.format(i))

    #Check the paths exist
    fail = False
    for p in paths:
        if not os.path.exists(p):
            fail = True
            print("ERROR: could not find file {}".format(p))
        else:
            print("Found file {}".format(p))

    #Quit now if files are not in order
    if fail:
        print("Bye bye")
        sys.exit(1)

    #Start the Exporter
    bs = BitstreamLogExporter(args.interval, 
                              paths,
                              cards,
                              logging=args.logging,
                              port=args.port)
    bs.start()

if __name__ == "__main__":
    main()
    
