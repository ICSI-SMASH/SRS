# Copyright 2012, 2013 International Computer Science Institute
# See the file LICENSE for licensing terms.
#
# NOTE: This is deprecated. You should probably just use srs-config -dumpperl
#

## This routine takes one argument $_[0] which is 
## a command to execute (specifially designed for srs-config calls) 
## and returns chomp([return value]) 
## (otherwise variable values would have the newline character which causes trouble)
## the routine breaks if the called command failed
##
## Make sure your variable PERLLIB is set 
## $Id: srs.pm 625 2013-09-24 21:46:06Z janin $
sub srs_config {
    my $var = `$_[0]`;
    ##The return value is set in $?; 
    ##this value is the exit status of the command as returned by the 'wait' call; 
    ##to get the real exit status of the command you have to shift right by 8 the value of $? ($? >> 8). 
    if($? >> 8 == 1 ) { exit 1; }
    chomp $var;
    return $var;
}


#Exit with true to indicate everything went fine
1;
