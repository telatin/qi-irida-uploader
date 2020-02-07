#!/usr/bin/env python3

"""
A script to upload a directory of FASTQ files to IRIDA,
sample by Sample.

Requires "upload_run.py" in path

will populate a dictionary of samples / filenames:

samples = {
	sample_1 = {
		name: sample_1
		for:  filename_R1
		rev:  filename_R2
	}

	sample_2 = {
		...
	}
}

"""


import sys
import argparse
import pprint
import os
import subprocess
from os.path import expanduser


def eprint(*args, **kwargs):
    """print to STDERR"""
    print(*args, file=sys.stderr, **kwargs)

def vprint(*args, **kwargs):
	"""print if --verbose"""
    if not opt.verbose:
        return 0 
    eprint(*args, **kwargs)
 

def validate_samples(s):
	"""
	scans a {samples} structure to check if there is the 'for' file for every file
	error if 'rev' if found without a 'for'
	"""
	paired = 0
	single = 0
	error = 0
	for sample in s:
		if 'for' in s[sample]:
			if 'rev' in s[sample]:
				paired += 1
			else:
				single += 1
		elif 'rev' in s[sample]:
			eprint("Sample {} has no valid forward file associated (only rev)".format(s['name']))
			error += 1
		else:
			eprint("Sample {} has no valid forward file associated".format(s['name']))
			error += 1

	eprint("{} paired samples; {} single end samples; {} errors".format(paired, single, error))

	if error > 0:
		eprint("Invalid samples found: aborting")
		exit()

def get_strand_and_basename(string):
    """
    input: filename
    output: [ strand, basename ]
    """
    is_for = 0
    is_rev = 0
    base = 0
    for tag in for_tags:
        if string.find(tag) != -1:
            is_for += 1
            base = string[0:string.find(tag)]
    for tag in rev_tags:
        if string.find(tag) != -1:
            is_rev += 1
            base = string[0:string.find(tag)]

    if is_for == 1 and is_rev == 0:
        return ['for', base]
    elif is_for == 0 and is_rev == 1:
        return ['rev', base]
    else:
        eprint("Ambiguos filename '{}': unable to detect strand".format(string))
        return [False, False]


def make_sample_sheet(sample, pid, output_file):
	sample_sheet = '[Data]\nSample_Name,Project_ID,File_Forward,File_Reverse\n'
	if 'rev' in sample:
		sample_sheet += '{},{},{},{}'.format(sample['name'], pid, sample['for'], sample['rev'])
	else:
		sample_sheet += '{},{},{},{}'.format(sample['name'], pid, sample['for'], sample['rev'])

	try:
		with open(output_file, 'w') as f:
			print(sample_sheet, file=f)
	except Exception as e:
		eprint("Unable to write samplesheet to {}".format(output_file))
		exit()

def scan_fastq_files(dir):
	"""
	scans the file of a directory keeping reads and sorting them in FOR/REV and keeping the basename
	i.e. the initial part of the file up to the _R1/_R2 or similar tag
	"""
	for file in os.listdir(dir):
		if file.endswith(".fq.gz") or file.endswith(".fastq.gz"):
			(strand, basename) = get_strand_and_basename(file)
			if strand != False:
				vprint("Adding sample '{1}' (strand={2}, filename={0})".format(file, strand, basename))
				if not basename in samples:
					samples[basename] = {}
					samples[basename]['name'] = basename
				samples[basename][strand] = file

			else:
				vprint("# Unable to get strand for file \"{}\"!".format(file))
				continue
		else:
			vprint("Skipping \"{0}\": not in \".fq.gz\" or \".fastq.gz\" extension".format(file))

def uploader(sample):
	"""
	Try uploading a sample
	"""

	sample_sheet = "{}/SampleList.csv".format(opt.input_dir)
	make_sample_sheet(sample, opt.project_id, sample_sheet)

	command = [opt.uploader, '--force', '-c', opt.irida_conf, '--directory', opt.input_dir]
	 
	uploaded = 0
	attempts = 0
	while uploaded < 1:
		attempts += 1
		if attempts == opt.attempts:
			eprint("Aborting after {} attempts:".format(opt.attempts))
			break
		try:
			vprint("#{}: Trying to upload {} (samplesheet = {})".format(attempts, sample['for'], sample_sheet))
			output = subprocess.check_output(
				' '.join(command),
				stderr=subprocess.STDOUT,
				shell=True)
			if not b'ERROR' in output:
				uploaded = 1
		except subprocess.CalledProcessError as e:
			eprint("Uploader error: {} returned {}\n{}".format(e.cmd, e.returncode, e.output.decode("utf-8")))

		


for_tags = ['_R1_', '_1.']
rev_tags = ['_R2_', '_2.']

opt_parser = argparse.ArgumentParser(description='Upload a directory to IRIDA, sample by sample. Allows multiple attempts.')

opt_parser.add_argument('-i', '--input-dir',
                        help='Directory containing FASTQ files')

opt_parser.add_argument('-p', '--project-id',
                        help='IRIDA project id')
 
opt_parser.add_argument('-1', '--for-tag',
                        help='Tag for R1 reads [default: _1. or _R1_]')

opt_parser.add_argument('-2', '--rev-tag',
                        help='Tag for R2 reads [default: _2. or _R2_]')

opt_parser.add_argument('-c', '--irida-conf',
						help="Path to the configuration file [~/.irida/config.conf]",
						default=expanduser("~/.irida/config.conf"))

opt_parser.add_argument('-u', '--uploader',
						help="Path to the upload_run.py script",
						default='upload_run.py')


opt_parser.add_argument('-a', '--attempts',
						type=int,
						help="Try this many times each sample",
						default=10)

opt_parser.add_argument('-v', '--verbose',
                        help='Increase output verbosity',
                        action='store_true')


opt = opt_parser.parse_args()


samples = {}

if opt.project_id == None:
	eprint("Missing project ID (-p INT)")
	exit()

if opt.input_dir == None:
	eprint("Missing input directory (-i DIR)")
	exit()

if opt.rev_tag != None:
	rev_tags = [ opt.rev_tag ]

if opt.for_tag != None:
	for_tags = [ opt.for_tag ]

if __name__ == '__main__':
	scan_fastq_files(opt.input_dir)
	validate_samples(samples)
	eprint('{} samples found'.format(len(samples)))
	for sample in sorted(samples):
		eprint('Uploading ' + sample)
		uploader(samples[sample])


