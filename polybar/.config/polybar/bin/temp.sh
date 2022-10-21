#!/bin/bash

TEMP=$(sensors | grep Tctl"" | awk -F ' ' '{print $2}')
echo ${TEMP:1:-4}
