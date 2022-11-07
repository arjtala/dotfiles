#!/bin/sh

if ! command -v nvidia-smi /dev/null
then
    exit
fi

query=$(nvidia-smi \
	--query-gpu=utilization.gpu,temperature.gpu,memory.free,memory.total \
	--format=csv,noheader,nounits)

if [[ $query == *"failed"* ]]; then
	echo "";
else
	echo $query | awk -F'[,]' '{ gpuf=int(100*$3/1024)/100; gpuu=int(100*$4/1024)/100; print "  "$1"% "$2"°C "gpuf"GiB/"gpuu"GiB"}'
fi

