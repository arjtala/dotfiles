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
					  --query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total \
					  --format=csv,noheader,nounits) | awk -F'[,]' '{ gpuu=int(100*$3/1024)/100; gput=int(100*$4/1024)/100; print "  "$1"% "$2"°C "gpuu"GiB/"gput"GiB |"}';
	fi
fi
}

gpu
