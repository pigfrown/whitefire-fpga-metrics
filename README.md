# Overview

Python script to export prometheus metrics for tokenminer and scrape pools.

Metrics can be captured with prometheus and displayed in grafana.

![](example.gif)

## Installation

Run the installer to add the tokenminer-metrics command to your PATH.
It can now be launched from cmd prompt.

Alternatively you can also run the metric_exporter.py script directly with python
(if it is already installed on your system).

## Running 

Monitoring hashrates requires instances of fx-tokenminer to have their output redirected to a
file, and for tokenminer-metrics to be able to find those files.

### Launching tokenminer

If you would normally launch tokenminer with:

`fx-tokenminer-v1.50.exe -t 730 -C -P`

then you now need to launch it with:

`fx-tokenminer-v1.50.exe -t 730 -C -P > hashrates.log`

If you are launching multiple instances of fx-tokenminer for different cards,
make sure you use different log files to save the output.

You can still input keystrokes into tokenminer, e.g. +/- to change clockspeed,
or ESC to safely ramp down, but you will not be able to see the output in your
terminal as normal. If logging is enabled you can see these messages in the
tokenminer-metric log.

### Launching tokenminer-metrics

Once fx-tokenminer is started and writing to a file you can launch
tokenminer-metrics.

tokenminer-metrics requires the -m argument, which takes a list of log paths to
parse.

e.g. for a exporting metrics from one instance of tokenminer:

`tokenminer-metrics -m hashrates.log`

e.g. for exporting metrics for 3 instances of tokenminer
`tokenminer-metrics -m hashrates1.log hashrates2.log hashrates3.log`

Once tokenminer-metrics is launched you can check it is working by going to
127.0.0.1:9090 in your web browser on the miner, or by going to $IP:9090 from
elsewhere in your local network (where $IP is the local IP of your mining box).
metrics. 

You can check other options with `tokenminer-metrics -h`, notably the -c option
to tag card stats with custom labels (e.g. bcu1, bcu2, cvp1, etc). By
default metrics are exported in cardX format. (e.g. card1, card2, card3, etc)

## Prometheus Setup

Install prometheus for your operating system of choice (https://prometheus.io/) and run it/start the service.
Check prometheus is working correctly at this stage by loading it's web page. It's default port is 9090.

To configure prometheus to scrape your miner you will need it's IP address.

Prometheus is configued with a `prometheus.yml` config file. Locate this file
on your system (e.g. `/usr/local/etc/prometheus.yml` for FreeBSD). Everytime
you change this file you need to restart the prometheus service.

E.g. to add a target in `prometheus.yml` for a mining box with IP 192.168.1.1 add
the following at the bottom of the file. 

```
    - job_name: "yourjobname"
      metrics_path: "/"
      scheme: "http"
      static_configs:
            - targets: ['192.168.1.1:9090']
```

Once you have added this target and restarted prometheus go to the prometheus
web interface. If the web interface doesn't load you probably have syntax error
in your `prometheus.yml`.

In the web interface click "Status->Targets" and you should see "yourjobname"
target. If you are running tokenminer_metrics on the mining box this should show
as being up.

You can view data in prometheus but grafana is more user friendly.

## Grafana Setup

Install grafana for your operating system of choice (https://grafana.com/) and run it/start the service.

Follow grafana guides to add a new prometheus datasource.

Create a new dashboard or import the dashboard in this repository. Note I'm no
grafana whizz and the exported dashboard seems to have embedded my datasource name in
it. So if you want it to work you will need to call your prometheus datasource
in grafana "homelab", or change the json to match your datasource name.

# Note on poolscraper.py

Pool scraping still occasionally crashes but I'm putting it here in case people
don't mind it being slightly buggy.

poolscraper.py is not part of tokenminer-metric (yet). This
means that it exports metrics on a different page than tokenminer-metric (you
can run it on any box, not just your miner), but you will need to add a new target in `prometheus.yml` for it, and if
you want to run it on the same box as tokenminer-metrics, change the port from
9090.

No installer for pool scraper, you'll need to install prometheus-client, python-socketio and
urllib3 in pip (maybe others)

