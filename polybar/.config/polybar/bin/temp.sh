#!/bin/bash

TEMP=$(sensors | grep "CPU" | awk -F ' ' '{print $2}')
echo ${TEMP:1:-4}
