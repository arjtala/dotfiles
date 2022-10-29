#!/bin/sh

function get_batt_level()
{
    MX="MXErgo"
	local _PATH=$1
	local _BATT="Not connected"
	if [[ !  -z  $1  ]]
	then
	   local _MX="MXErgo"
	   local _NAME=$(/usr/bin/upower --show-info $_PATH | /usr/bin/grep model | /usr/bin/awk '{print $2 $3}')
	   if [[ $_NAME = $_MX ]]
	   then
		   local _BATT=$(/usr/bin/upower --show-info $_PATH | /usr/bin/grep percentage | /usr/bin/awk '{print $2}')
	   fi
	fi
    BATT=$_BATT
}

PATH=$(upower --dump | grep hidpp | grep org | awk '{print $2}')
get_batt_level $PATH
echo "${MX}: ${BATT}"