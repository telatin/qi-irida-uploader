import logging
import os
import re

import progress
from model.project import Project
import subprocess
from .. import exceptions
from . import sample_parser, validation
from core.api_handler import initialize_api_from_config, _get_api_instance

class Parser:

    sample_file = None

    @staticmethod
    def _find_directory_list(directory):
        """Find and return all directories in the specified directory.

        Arguments:
        directory -- the directory to find directories in

        Returns: a list of directories including current directory
        """

        # Checks if we can access to the given directory, return empty and log a warning if we cannot.
        if not os.access(directory, os.W_OK):
            raise exceptions.DirectoryError("The directory is not writeable, "
                                            "can not upload samples from this directory {}".format(directory),
                                            directory)

        dir_list = next(os.walk(directory))[1]  # Gets the list of directories in the directory
        full_dir_list = []
        for d in dir_list:
            full_dir_list.append(os.path.join(directory, d))
        return full_dir_list

    @staticmethod
    def find_runs(directory):
        """
        find a list of run directories in the directory given

        :param directory:
        :return: list of DirectoryStatus objects
        """
        logging.info("looking for runs in {}".format(directory))

        runs = []
        directory_list = Parser._find_directory_list(directory)
        for d in directory_list:
            runs.append(progress.get_directory_status(d, 'SampleList.csv'))

        return runs

    @staticmethod
    def find_single_run(directory):
        """
        Find a run in the base directory given

        :param directory:
        :return: DirectoryStatus object
        """
        logging.info("looking for run in {}".format(directory))
        sample_file = Parser.get_sample_sheet(directory)
        return progress.get_directory_status(os.path.dirname(sample_file), [os.path.basename(sample_file)])

    @staticmethod
    def _get_project_id(project_name):
        api_instance = initialize_api_from_config()
        api_instance.get_projects()
        if project_name.endswith(' (2)'):
            project_name = project_name[:-4]
        project_ids = [x._id for x in api_instance.get_projects() if x._name == project_name]
        if len(project_ids) == 1:
            return project_ids[0]
        # Else create a project
        new_project = Project(name=project_name,
                              description='Automatically generated using uploader from basemount.')
        project_id = int(api_instance.send_project(new_project)['resource']['identifier'])
        return project_id


    @staticmethod
    def get_subreads(directory, r):
        return sorted(['"' + os.path.join(directory, x) + '"' for x in os.listdir(directory)
                           if x.endswith(r + '_001.fastq.gz')])

    @staticmethod
    def merge_reads(directory, sample_name, temp_dir='/tmp/irida/'):
        if not os.path.exists('/tmp/irida'):
            os.mkdir('/tmp/irida')
        merged_reads_r1 = os.path.join(temp_dir, sample_name + '_R1.fastq.gz')
        merged_reads_r2 = os.path.join(temp_dir, sample_name + '_R2.fastq.gz')
        if not os.path.exists(merged_reads_r1) or not os.path.exists(merged_reads_r2):
            read_dir = os.path.join(directory, 'Samples', sample_name, 'Files')
            r1_list = Parser.get_subreads(read_dir, 'R1')
            r2_list = Parser.get_subreads(read_dir, 'R2')
            if len(r1_list) == 4:
                subprocess.call('cat {} > {}'.format(' '.join(r1_list),
                                                     merged_reads_r1), shell=True)
                subprocess.call('cat {} > {}'.format(' '.join(r2_list),
                                                     merged_reads_r2), shell=True)
        return merged_reads_r1, merged_reads_r2

    @staticmethod
    def get_sample_sheet(directory):
        """
        gets the sample sheet file path from a given run directory

        :param directory:
        :return:
        """
        if directory.endswith('/'):
            directory = directory[:-1]
        logging.info("Looking for sample sheet in {}".format(directory))
        # Handle samples
        project_name = 'Basespace-' + os.path.basename(directory)
        sample_sheet_path = '/tmp/%s-Samplesheet.csv' % project_name
        with open(sample_sheet_path, "w") as sample_sheet:
            sample_sheet.write("[Data]\n")
            sample_sheet.write("Sample_Name,Project_ID,File_Forward,File_Reverse\n")
            sample_directory = os.path.join(directory, 'Samples')
            sample_paths = [os.path.join(sample_directory, x, "Files") for x in os.listdir(sample_directory) if
                            not x.startswith('.')]
            irida_project_id = Parser._get_project_id(project_name)
            existing_samples = [x.sample_name for x in _get_api_instance().get_samples(irida_project_id)]
            for sample in sample_paths:
                sample_dict = dict(project_id=irida_project_id)
                logging.debug('Reading folder %s' % sample)
                sample_dict['sample_name'] = re.search("Samples\/(.+)\/Files", sample).group(1)
                if not sample_dict['sample_name'] in existing_samples:
                    r1, r2 = Parser.merge_reads(directory, sample_dict['sample_name'], temp_dir='/tmp/irida/')
                    if len(sample_dict['sample_name']) < 4:
                        sample_dict['sample_name'] = project_name + '-' + sample_dict['sample_name']
                    sample_dict['file_forward'] = r1
                    sample_dict['file_reverse'] = r2
                    sample_sheet.write("{sample_name},{project_id},{file_forward},{file_reverse}\n".format(**sample_dict))
        return sample_sheet_path

    @staticmethod
    def get_sample_sheet_file_name():
        global sample_file
        return sample_file


    @staticmethod
    def get_sequencing_run(sample_sheet):
        """
        Does local validation on the integrity of the run directory / sample sheet

        Throws a ValidationError with a validation result attached if it cannot make a sequencing run

        :param sample_sheet:
        :return: SequencingRun
        """

        # Try to get the sample sheet, validate that the sample sheet is valid
        validation_result = validation.validate_sample_sheet(sample_sheet)
        if not validation_result.is_valid():
            logging.error("Errors occurred while getting sample sheet")
            raise exceptions.ValidationError("Errors occurred while getting sample sheet", validation_result)

        # Try to build sequencing run from sample sheet & meta data, raise validation error if errors occur
        try:
            sequencing_run = sample_parser.build_sequencing_run_from_samples(sample_sheet)
        except exceptions.SequenceFileError as error:
            validation_result.add_error(error)
            logging.error("Errors occurred while building sequence run from sample sheet")
            raise exceptions.ValidationError("Errors occurred while building sequence run from sample sheet",
                                             validation_result)

        return sequencing_run
