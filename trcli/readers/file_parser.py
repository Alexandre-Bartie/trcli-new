import json
import os
from collections import deque
from pathlib import Path
from abc import abstractmethod
import pprint
from typing import Union

from trcli.cli import Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite

class LogParser():

    def __init__(self, environment: Environment):
        self.env = environment    
        self.lines = []
        self.path = self.env.file

    def setup(self, folder: str, extension = 'log') -> str:
        self.path = Path(self.path.parent, folder, self.path.stem + "." + extension)
        if os.path.exists(self.path):
            try:
                os.remove(self.path)
            except Exception as e:
                print(f"An error occurred while deleting the file: {e}")
    
    def add(self, error):
        if error is not None:
            self.lines.append(error)

    def save(self, title: str):
        directory = os.path.dirname(self.path)
        if not os.path.exists(directory):
            os.makedirs(directory)

        try:
            file = open(self.path, 'w')
            for line in self.lines:
                    data = self.__format_line(line)
                    file.write(data + '\n')

            self.env.log(f"{title}: The parser file was created. -path: {self.path}")

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
 


class FileParser():
    """
    Each new parser should inherit from this class, to make file reading modular.
    """
    def __init__(self, environment: Environment):
        self.filepath = self.check_file(environment.file)
        self.filename = self.filepath.name
        self.env = environment
        self.log = LogParser(environment)   

    @staticmethod
    def check_file(filepath: Union[str, Path]) -> Path:
        filepath = Path(filepath)
        if not filepath.is_file():
            raise FileNotFoundError("File not found.")
        return filepath

    @abstractmethod
    def parse_file(self) -> list[TestRailSuite]:
        raise NotImplementedError




