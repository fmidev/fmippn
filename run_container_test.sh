#!/bin/bash

export HDF5_USE_FILE_LOCKING=FALSE
DOMAIN=${DOMAIN:-"ravake"}

#List latest file in domain folder
INPATH=${INPATH:-"/tutka/data/input_composites/$DOMAIN/"}
LATEST_TIMESTAMP=`ls -t $INPATH | head -n1 | awk -F "_" '{print $1}'`

TIMESTAMP=${TIMESTAMP:-${LATEST_TIMESTAMP}}

#Output path
#Read short hostname from server to use as output folder names.
HOSTNAME=`hostname -s`
NODE=${NODE:-${HOSTNAME}}
OUTPATH=${OUTPATH:-"/tutka/data/dev/cache/radar/fmippn/${NODE}"}

#Log path
LOGPATH=${LOGPATH:-"/tutka/data/dev/cache/log/fmippn/${NODE}"}

echo INPATH: $INPATH
echo OUTPATH: $OUTPATH
echo LOGPATH: $LOGPATH
echo "Calculating PPN nowcast (testing callback function) for domain "$DOMAIN", timestamp "$TIMESTAMP

#Mkdirs if log and outpaths have been cleaned
mkdir -p $OUTPATH
mkdir -p $LOGPATH

# Build from Dockerfile
#docker build -t fmippn .

# --log-level=debug \
#--user $(id -u):$(id -g) \

# Run with volume mounts
docker run \
       --rm \
       --env "timestamp=$TIMESTAMP" \
       --env "domain=$DOMAIN" \
       --security-opt label=disable \
       -v  ${INPATH}:/input \
       -v  ${OUTPATH}:/output \
       -v  ${LOGPATH}:/log \
       -v "$(pwd)"/fmippn/config/${DOMAIN}.json:/fmippn/config/${DOMAIN}.json \
       fmippn:latest

