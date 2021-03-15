sudo add-apt-repository universe
sudo apt-get install -y python3 python3-venv python3.6-venv
sudo apt-get -y install prometheus curl

#Configure prometheus
p_config=/etc/prometheus/prometheus.yml
if ! grep -q whitefire $p_config ; then
	sudo cat prometheus_target.yml >> $p_config
fi


##Install Grafana
curl https://packages.grafana.com/gpg.key | sudo apt-key add -
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
sudo apt-get update
sudo apt-get -y install grafana

sudo systemctl daemon-reload
sudo systemctl enable grafana-server
sudo systemctl start grafana-server
sudo systemctl enable prometheus
sudo systemctl restart prometheus


echo """
installation complete.
If you want to access grafana from another computer you may need to open 3000 on your firewall
"""


