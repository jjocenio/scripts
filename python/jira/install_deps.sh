#!/bin/bash

cd /tmp
wget https://github.com/kennethreitz/requests/zipball/master -O requests.zip
unzip requests.zip
mv kennethreitz-requests* requests
cd requests
sudo python setup.py install

cd -
sudo rm -rf /tmp/requests
