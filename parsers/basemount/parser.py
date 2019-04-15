import logging
import os
import re

import progress
from model.project import Project

from .. import exceptions
from . import sample_parser, validation
from core.api_handler import initialize_api_from_config

class Parser:

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
        global sample_file
        sample_file = os.path.join(directory, 'SampleList.csv')
        return progress.get_directory_status(directory, 'SampleList.csv')

    @staticmethod
    def _get_project_id(project_name):
        api_instance = initialize_api_from_config()
        api_instance.get_projects()
        project_ids = [x._id for x in api_instance.get_projects() if x._name == project_name]
        if len(project_ids) == 1:
            return project_ids[0]
        # Else create a project
        new_project = Project(name=project_name,
                              description='Automatically generated using uploader from basemount.')
        project_id = int(api_instance.send_project(new_project)['resource']['identifier'])
        return project_id


    @staticmethod
    def get_sample_sheet(directory):
        """
        gets the sample sheet file path from a given run directory

        :param directory:
        :return:
        """
        logging.info("Looking for sample sheet in {}".format(directory))

        # Checks if we can access to the given directory, return empty and log a warning if we cannot.
        if not os.access(directory, os.W_OK):
            logging.error(("The directory is not accessible, can not parse samples from this directory {}"
                           "".format(directory), directory))
            raise exceptions.DirectoryError("The directory is not accessible, "
                                            "can not parse samples from this directory {}".format(directory),
                                            directory)
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
            for sample in sample_paths:
                sample_dict = dict(project_id=irida_project_id)
                logging.debug('Reading folder %s' % sample)
                has_reads = False
                for read_file in os.listdir(sample):
                    read_file = os.path.join(sample, read_file)
                    sample_name_match = re.search("Samples\/(.+)\/Files", sample)
                    r1 = re.search("R1_\d+.fastq.gz", read_file)
                    if sample_name_match:
                        sample_dict['sample_name'] = sample_name_match.group(1)
                        if sample_dict['sample_name'].endswith(" (2)"):
                            has_reads = True
                            continue
                    if r1:
                        sample_dict['file_forward'] = read_file
                        has_reads = True
                        # Find r2
                        r2_path = read_file.replace('_R1_', '_R2_')
                        if os.path.exists(r2_path):
                            sample_dict['file_reverse'] = r2_path
                        sample_sheet.write("{sample_name},{project_id},{file_forward},{file_reverse}\n".format(**sample_dict))
                if not has_reads:
                    logging.warning('No Reads found in %s' % sample)
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
