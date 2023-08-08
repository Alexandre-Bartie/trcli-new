import json
import os
from collections import deque
from pathlib import Path
from abc import abstractmethod
import pprint
from typing import Union

from trcli.cli import Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite

class ErrorParse():

    def __init__(self, path: str, extension = 'log'):
        self.lines = []
        self.path = name = Path(path.parent, path.stem + "." + extension)
        self.__setup()

    def __setup(self):
        if os.path.exists(self.path):
            try:
                os.remove(self.path)
            except Exception as e:
                print(f"An error occurred while deleting the file: {e}")
    
    def log(self, error):
        if error is not None:
            self.lines.append(error)

    def save(self):
        directory = os.path.dirname(self.path)
        if not os.path.exists(directory):
            os.makedirs(directory)

        file = open(self.path, 'w')
        for line in self.lines:
            try:
                data = self.__format_line(line)
                file.write(data + '\n')
            except Exception as e:
                print(f"An error occurred while writing the file: {e}")

    
    def __format_line(self, data):
        # try:
        #     if isinstance(data, deque):
        #         content = list(data)
        #     else:
        #         content = json.loads(data)
        #     text = json.dumps(content, indent=4)
        #     return f"json: {text}"
        # except json.JSONDecodeError:
        return pprint.pformat(data, indent=4, compact=False, width=200)
 


class FileParser:
    """
    Each new parser should inherit from this class, to make file reading modular.
    """

    def __init__(self, environment: Environment):
        self.filepath = self.check_file(environment.file)
        self.filename = self.filepath.name
        self.env = environment
        self.error = ErrorParse(self.__error_path())
 
    @staticmethod
    def check_file(filepath: Union[str, Path]) -> Path:
        filepath = Path(filepath)
        if not filepath.is_file():
            raise FileNotFoundError("File not found.")
        return filepath

    @abstractmethod
    def parse_file(self) -> list[TestRailSuite]:
        raise NotImplementedError

    def __error_path(self) -> str:
        return self.filepath.parent / 'error' / self.filepath.name



