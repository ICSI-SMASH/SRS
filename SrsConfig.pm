######################################################################
#
# File: SrsConfig.pm
# Author: Adam Janin
#
# Copyright 2012, 2013 International Computer Science Institute
# See the file LICENSE for licensing terms.
#
# NOTE: This is deprecated. You should probably just use
# srs-config -dumpperl.
#         
# Package for using srs-config in perl.
#
# The package currently calls the executable srs-config to do the
# actual work, so srs-config must be in the path for this to work.
#
# Usage:
#
# use SrsConfig;
# $c = new SrsConfig('test1.config');
# print $c->{vars}{corpus_audio_dir}, "\n";
# print $c->get('corpus_audio_dir'), "\n";
#
# $v = $c->{vars};
# print $v->{corpus_audio_dir}, "\n";
#
# You can also skip the wrapper:
#
# tie %c, "SrsConfig::Vars", 'test1.config';
# print $c{corpus_audio_dir}, "\n";
#
# You can treat the things that look like perl hashes as hashes:
#
# if (exists($v->{foo})) {
#   print "Foo exists\n";
# }
#
# print join(' ', keys(%c));
#


######################################################################
#
# Define the inner package that handles storing variables.
# This works using tie to tie a hash to a set of subroutines
# that call 'srs-config'.
#

package SrsConfig::Vars;
use Carp;
use FileHandle;

our $ERRMSG = "Error from SrsConfig";
our $VERSION = '1.0';

sub TIEHASH {
    my $self = shift;
    my $configfile = shift;

    if (! -e $configfile) {
	croak "$ERRMSG: Config file '$configfile' does not exist";
    }
    
    my $data = {
	CONFIGFILE => $configfile,
	SRSCONFIG_CMD => 'srs-config',
	ITERFH => undef
    };

    return bless $data, $self;
}

sub FETCH {
    my($self, $var) = @_;

    if (!EXISTS($self, $var)) {
	croak "$ERRMSG: '$var' doesn't exist in config file '$self->{CONFIGFILE}'";
    }
    
    my $val = `$self->{SRSCONFIG_CMD} -config $self->{CONFIGFILE} $var`;
    if ($? == 0) {
	chop($val);
	return $val;
    } else {
	croak "$ERRMSG: srs-config returned non-zero exit status getting '$var' in '$self->{CONFIGFILE}'";
    }
}

sub EXISTS {
    my($self, $var) = @_;
    
    return system("$self->{SRSCONFIG_CMD} -quiet -config $self->{CONFIGFILE} $var") == 0;
}

sub FIRSTKEY {
    my($self) = @_;
    if (defined($self->{ITERFH})) {
	croak "$ERRMSG: error in FIRSTKEY. This shouldn't happen";
    }
    $fh = new FileHandle("$self->{SRSCONFIG_CMD} -config $self->{CONFIGFILE} -dump|") or croak "$ERRMSG: unable to start srs-config -dump command";
    my $val = getnextval($fh);
    if (!defined($val)) {
	$fh->close();
    } else {
	$self->{ITERFH} = $fh;
    }
    return $val;
}

sub NEXTKEY {
    my($self) = @_;
    if (!defined($self->{ITERFH})) {
	croak "$ERRMSG: error in NEXTKEY. This shouldn't happen";
    }
    my $val = getnextval($self->{ITERFH});
    if (!defined($val)) {
	$self->{ITERFH}->close();
	$self->{ITERFH} = undef;
    }
    return $val;
}

sub UNTIE {
    my($self) = @_;
    if (defined($self->{ITERFH})) {
	$self->{ITERFH}->close();
	$self->{ITERFH} = undef;
    }
}	

sub getnextval {
    my($fh) = @_;
    my($line);
    while ($line = <$fh>) {
	$line =~ s/#.*$//;
	next if $line =~ /^\s+$/;
	if ($line =~ /^\s*(\S+)/) {
	    return $1;
	}
    }
    return undef;
}

######################################################################
#
# All of the following are unimplemented by design.
#

sub STORE {
    my($self, $var, $val) = @_;
    croak "$ERRMSG: setting config variables is not supported";
}

sub DELETE {
    my($self, $var) = @_;
    croak "$ERRMSG: deleting config variables is not supported";
}

sub CLEAR {
    my($self) = @_;
    croak "$ERRMSG: clearing a config is not supported";
}

sub SCALAR {
    my($self) = @_;
    croak "$ERRMSG: using a config in scalar context is not supported";
}

######################################################################
#
# Now define the SrsConfig class, which is a simple wrapper
# around SrsConfig::Vars (and eventually SrsConfig::Docs).
#

package SrsConfig;

sub new {
    my($class, $configfile) = @_;
    my $self = {};
    bless $self, $class;
    my(%vars);
    tie %vars, 'SrsConfig::Vars', $configfile;
    $self->{vars} = \%vars;
    return $self;
}

sub get {
    my($self, $var) = @_;
    return $self->{vars}{$var};
}

1;
