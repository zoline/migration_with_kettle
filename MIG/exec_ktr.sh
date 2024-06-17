#!/bin/bash
. /home/pentaho/pentaho.env
for tab in  COUNTRIES
do
	KTR_FILE=/home/pentaho/MIG/hr/$tab.ktr 
	LOG_FILE=/home/pentaho/MIG/logs/$tab.log
	pan.sh -file=$KTR_FILE -level=Basic -logfile=$LOG_FILE
done
