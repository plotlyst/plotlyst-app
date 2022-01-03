#!/bin/bash

# exit when any command fails
set -e

#echo "Re-generate PyQt code..."
# generate UI > Python code first
#./gen.sh

python -X faulthandler src/main/python/plotlyst/__main__.py --mode DEV $@
