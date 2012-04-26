'''
Created on Apr 23, 2012

@author: clay
'''
import unittest
import sys
import argparse
import os
import tempfile
import errno
from mockito import mock, when

class Preferences(object):
    _DEFAULT_CONFIG_DIR_NAME = ".coggrinder"

    def __init__(self):
        # Where configuration files are held.
        self.config_dir_path = None

    def parse_cli_arguments(self):
        # Parse command line arguments.
        parser = argparse.ArgumentParser(description="Desktop interface for Google Tasks.")
        parser.add_argument("--config-dir",
            default=os.path.expanduser(Preferences._DEFAULT_CONFIG_DIR_NAME))

        # Parsing the arguments will cause a SystemExit error to be raised if there
        # are any errors in the provided arguments. Despite the lack of arguments,
        # this call defaults to reading the command line variables from sys.argv.
        cli_options = parser.parse_args()

        self.config_dir_path = os.path.realpath(cli_options.config_dir)

        # Create the config directory.
        try:
            os.mkdir(self.config_dir_path)
        except OSError as error:
            if error.errno != errno.EEXIST:
                # If the error _wasn't_ raised because the file already exists,
                # then re-raise the error. If the directory already exists, 
                # then simply ignore this error.
                raise error

class PreferencesTest(unittest.TestCase):
    def setUp(self):
        self.preferences = Preferences()

    def tearDown(self):
        del self.preferences
        sys.argv = []

        try:
            os.rmdir(self.expected_config_dir_path)
        except OSError as error:
            if error.errno == errno.ENOENT:
                # That's fine, just means the directory didn't exist.
                pass
            else:
                # Unsure about source of error, so re-raise it.
                raise error

    def test_no_arguments(self):
        sys.argv = ['']

        self.expected_config_dir_path = os.path.expanduser(
            Preferences._DEFAULT_CONFIG_DIR_NAME)

        self.preferences.parse_cli_arguments()

        self.assertTrue(os.path.exists(self.expected_config_dir_path))

    def test_new_custom_config_dir(self):
        """Test configuring Preferences with an new custom config dir.

        Arrange:
            Set the expected config dir path to point to the new directory that
            resides in the system temp directoy.
            Set up fake CLI arguments with config-dir pointing to the expected
            config dir path.
        Act: 
            Configure the Preferences instance from the fake CLI arguments.
        Assert:
            That the custom config directory has been created.
        """
        ### Arrange ###
        self.expected_config_dir_path = os.path.join(tempfile.gettempdir(),
            "custom_config")
        sys.argv = ['', "--config-dir=" + self.expected_config_dir_path]

        ### Act ###
        self.preferences.parse_cli_arguments()

        ### Assert ###
        self.assertTrue(os.path.exists(self.expected_config_dir_path))

    def test_existing_custom_config_dir(self):
        """Test configuring Preferences with an existing custom config dir.

        Arrange:
            Set the expected config dir path to point to a new directory in 
            the system temp directory.
            Create the new directory.
            Set up fake CLI arguments with config-dir pointing to the expected
            config dir path.
        Assert:
            Configuring Preferences against a new config directory doesn't
            raise an error.
        """
        ### Arrange ###        
        self.expected_config_dir_path = os.path.join(tempfile.gettempdir(),
            "custom_config")
        os.mkdir(self.expected_config_dir_path)
        sys.argv = ['', "--config-dir=" + self.expected_config_dir_path]
        
        ### Assert ###
        try:
            self.preferences.parse_cli_arguments()
        except BaseException as error:
            self.fail(
                "Configuring against an existing directory unexpectedly raised an error: {0}".format(error))
#------------------------------------------------------------------------------ 
