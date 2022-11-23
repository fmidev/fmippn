#!/bin/bash

cmd="conda run -n fmippn python run_ppn.py --config=test_ravake --timestamp=202211230815"
echo $cmd
eval $cmd
