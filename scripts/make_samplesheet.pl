#!/usr/bin/env perl

use 5.018;
use Getopt::Long::Descriptive;
use Data::Dumper;
my $counters;
my $reads;
my $output;
my $samplesheet = "[Data]
Sample_Name,Project_ID,File_Forward,File_Reverse\n";


my ($opt, $usage) = describe_options(
        'dir_to_samplesheet.pl %o',
        [
                'inputdir|i=s',
                'Input directory containing the FASTQ files',
                { required => 1},
        ],
        [
                'project|p=s',
                'IRIDA Project ID',
                { required => 1},
        ],
        [
                'force|f',
                'Overwrite samplesheet if output is found',
        ],
        [
                'output|o=s',
                'filename for the samplesheet (default: SampleList.csv in inputdir)',
                {},
        ],
        [
                'verbose|v',
                'print extra runtime information'
        ],
        [
                'help|h',
                'print help message',
                { shortcircuit => 1 },
        ],

);


print( $usage->text ), exit if $opt->help;

if ( ! -d $opt->inputdir ) {
        die "FATAL ERROR:\n Input <" . $opt->inputdir . "> should be a directory (-i, --inputdir)\n";
}

$output = $opt->inputdir . '/SampleList.csv';
$output = $opt->output if (defined $opt->{output});
opendir my $dir, $opt->inputdir || die " FATAL ERROR:\n Unable to read input directory\n";

if (-e "$output" and !$opt->force) {
        die "FATAL ERROR:\n Samplesheet <$output> already found. Try --force to ignore this warning.\n";
}
if (! -e "$output" ) {
        die "FATAL ERROR:\n Samplesheet <$output> is not writable\n";
}
while (my $file = readdir($dir) ) {
        $counters->{total_files}++;
        if ( -d $file) {
                say STDERR "Warning: Skipping \"$file\": is a directory" if $opt->verbose;
                $counters->{skip_dir}++;
                next;
        }
        if ( $file =~/^\./ ) {
                say STDERR "Warning: Skipping \"$file\": is a hidden file" if $opt->verbose;
                $counters->{skip_hidden}++;
                next;
        }

        if ( $file !~/(fastq|fq)/ ) {
                say STDERR "WARNING! \"$file\" has not a <fastq|fq> extension (skipping)"; # always warn!
                next;
        }
        my $samplename;
        my $pairtag;
        my $strand;
        if ($file =~/(_R[12]|_[12])[^A-Za-z0-9]/) {
                $pairtag = $1;
                $strand = 'for';
                $strand = 'rev' if ( $pairtag =~/2/ );
                ($samplename) = split /$pairtag/, $file;

                # Hoping it's a standard Illumina file:
                $samplename =~s/_S\d+_L\d+//;
                say STDERR "$samplename -> $strand\t$file [$pairtag]" if $opt->verbose;

                $reads->{$samplename}->{$strand} = $file;
        } else {
                say STDERR "WARNING! Expecting _R1/_R2 or _1/_2 strand identifier in $file (skipping)";
        }

}

foreach my $sample (sort keys %{ $reads } ) {
        next unless $reads->{$sample}->{for};
        $samplesheet .= qq($sample,$opt->{project},$reads->{$sample}->{for},$reads->{$sample}->{rev}\n);
}

say STDERR "Saving samplesheet to <$output>" if $opt->verbose;
open my $OUT, '>', $output or
        die "\nFATAL ERROR:\nUnable to write output file <$output>. This is the samplesheet:\n\n$samplesheet\n";

print {$OUT} $samplesheet;


