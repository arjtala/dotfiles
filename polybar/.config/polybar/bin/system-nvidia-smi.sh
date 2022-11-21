#!/bin/bash

function gpu()
{
if ! command -v nvidia-smi &> /dev/null
then
    echo "";
else
    local query=$(nvidia-smi)
	if [[ $query == *"failed"* ]]; then
		echo "";
	else
		echo $(nvidia-smi \
					  --query-gpu=utilization.gpu,temperature.gpu,memory.free,memory.total \
					  --format=csv,noheader,nounits) | awk -F'[,]' '{ gpuf=int(100*$3/1024)/100; gpuu=int(100*$4/1024)/100; print "  "$1"% "$2"°C "gpuf"GiB/"gpuu"GiB"}';
	fi
fi
}

gpu
