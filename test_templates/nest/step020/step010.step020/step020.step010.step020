#!/bin/sh
#
# Echo the command name.
# If the command name occurs in the failsteps config variable,
# print an error message to stdout and return failure.

{
set -o nounset
set -o errexit

inconfig=$1
outconfig=$2

cmdname=`basename $0`
failsteps=`srs-config -default none -c $inconfig failsteps`
outfile=`srs-config -c $inconfig outfile`

echo $cmdname >> $outfile

if echo ",$failsteps," | grep -q ",$cmdname," ; then
  echo $cmdname failed >> $outfile 2>&1 
  exit 1
fi

exit
}
