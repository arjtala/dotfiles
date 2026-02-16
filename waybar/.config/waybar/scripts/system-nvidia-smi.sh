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
					  --format=csv,noheader,nounits) | awk -F'[,]' '{ printf "%d%% %d°C %.1fG/%.1fG\n", $1, $2, $3/1024, $4/1024 }';
	fi
fi
}

gpu
