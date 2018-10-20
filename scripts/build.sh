#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

sh $DIR/nuke.sh
sh $DIR/setup.sh
