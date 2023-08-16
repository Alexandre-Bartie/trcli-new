import json
from pathlib import Path

import yaml

from trcli.data_classes.dataclass_testrail import (
    TestRailCase,
    TestRailSuite,
    TestRailSection,
    TestRailResult,
)
from trcli.readers.file_parser import FileParser
from openapi_spec_validator import validate_spec, openapi_v30_spec_validator, openapi_v31_spec_validator
from openapi_spec_validator.readers import read_from_filename
from prance import ResolvingParser


class OpenApiTestCase:

    def __init__(
            self,
            path: str,
            verb: str,
            response_code: str,
            response_description: str,
            operation_id: str = None,
            request_details: dict = None,
            response_details: dict = None
    ):
        self.path = path
        self.verb = verb
        self.operation_id = operation_id
        self.response_code = response_code
        self.response_description = response_description
        self.request_details = request_details
        self.response_details = response_details

    @property
    def name(self) -> str:
        name = f"{self.verb.upper()} {self.path} -> {self.response_code}"
        if self.response_description:
            name += f" ({self.response_description})"
        return name

    @property
    def unique_id(self) -> str:
        name = f"{self.path}.{self.verb.upper()}.{self.response_code}"
        return name

    @property
    def preconditions(self) -> str:
        details = self.request_details.copy()
        preconditions = ""

        key = "deprecated"
        if key in details and details[key]:
            preconditions += """
||| :WARNING
|| ENDPOINT IS DEPRECATED
"""

        key = "summary"
        if key in details and details[key]:
            preconditions += self._format_text("Summary", details[key])
            details.pop(key)

        key = "description"
        if key in details and details[key]:
            preconditions += self._format_text("Description", details[key])
            details.pop(key)

        key = "externalDocs"
        if key in details and details[key]:
            preconditions += self._format_text("External Docs", details[key])
            details.pop(key)

        return preconditions

    @property
    def steps(self) -> str:
        details = self.request_details.copy()
        steps = f"""
Request
=======
    {self.verb.upper()} {self.path}
"""

        key = "parameters"
        if key in details and details[key]:
            steps += self._format_text("Parameters", details[key])
            details.pop(key)

        key = "requestBody"
        if key in details and details[key]:
            steps += self._format_text("Request body schema", details[key])
            details.pop(key)

        key = "security"
        if key in details and details[key]:
            steps += self._format_text("Security", details[key])
            details.pop(key)

        return steps

    @property
    def expected(self) -> str:
        details = self.response_details.copy()
        expected = f"""
Response code
=======
{self.response_code} ({self.response_description})
"""
        key = "content"
        if key in details and details[key]:
            expected += self._format_text("Response content", details[key])
            details.pop(key)
        return expected

    @staticmethod
    def _format_text(title, details):
        text = f"""
{title}
=======
"""
        if type(details) is str:
            text += details
        else:
            details = yaml.dump(details, Dumper=yaml.Dumper)
            for line in details.splitlines(keepends=True):
                text += f"    {line}"
        return text


class OpenApiParser(FileParser):

    def parse_file(self, save: False) -> list[TestRailSuite]:
        self.env.log(f"Parsing OpenAPI specification.")
        spec = self.resolve_openapi_spec()

        self.log.setup("warning", "txt")

        handle = OpenAPIHandleCases(self)

        handle.getSections(spec)

        sections, case_count = handle.getTestCases(spec)
 
        test_suite = TestRailSuite(
            spec["info"]["title"],
            testsections=[section for _name, section in sections.items() if section.testcases],
            source=self.filename
        )

        self.log.save("Warning Data")
        
        if save:
            self.__save_suite(test_suite)
        
        ##
        ## Show summary of data extraction from openAPI file
        ##

        self.env.log(f"Processed {case_count} test cases based on possible responses.")       
        
        return [test_suite]

    def resolve_openapi_spec(self) -> dict:
        spec_path = self.filepath
        unresolved_spec_dict, spec_url = read_from_filename(str(spec_path.absolute()))
        try:
            parser = ResolvingParser(spec_string=json.dumps(unresolved_spec_dict), backend='openapi-spec-validator')
            spec_dictionary = parser.specification
            self.__validate_spec_version(spec_dictionary)
            return spec_dictionary
        except Exception as e:
            self.__log_error(e.args)

            raise e  # "This openapi file have internal problems."

    def __validate_spec_version(self, spec_dictionary):

        list_versions = self.__valid_versions_list()
        list_validator = self.__get_list_validator()

        for version in list_versions:
            spec_validator = list_validator[version]
            try:
                validate_spec(spec_dictionary, validator=spec_validator)
                return True
            except:
                return False

        raise "This openapi file dont have a 3.x layout version."

    def __valid_versions_list(self):
        return ["OAS 3.0", "OAS 3.1"]

    def __get_list_validator(self):
        return {
            "OAS 3.0": openapi_v30_spec_validator,
            "OAS 3.1": openapi_v31_spec_validator,
        }

    def __save_suite(self, suite: TestRailSuite):
        self.log.setup("data", "txt")

        self.log.add(suite.name, level=1)

        index_section = 0
        for section in suite.testsections:
            index_section += 1
            self.log.add(section.name, level=2, index=index_section)
            
            index_case = 0
            for case in section.testcases:
                index_case += 1
                self.log.add(case.title, level=3, index=index_case)

        self.log.save("Parser Data")
    
    def __log_error(self, error):
        self.log.setup("error")
        self.log.add(error, level=1, index=1)       
        self.log.save("Parser Error")   


class OpenAPIHandleCases():
       
    def __init__(self, parser: OpenApiParser):

        self.parser = parser
        self.log = parser.log
        self.env = parser.env

        self.sections = { "untagged": TestRailSection("untagged") }

    def getSections(self, spec: dict):

        ##
        ## Identify the tag sections in the openAPI file
        ##        
        if "tags" in spec:  
            
            for item in spec["tags"]:
                tag = item.get("name", "null")
                name = item.get("x-displayName", tag) 
                summary = item.get("description", "")                
                if tag not in self.sections:
                    self.sections[tag] = OpenAPITagSection(self.parser, name, summary)

        ##
        ## Identify group sections in the openAPI file
        ##        
        if "x-tagGroups" in spec:        
            
            for group in spec["x-tagGroups"]:
                group_name = item.get("name", "null")
                if group_name not in self.sections:
                    self.sections[group_name] = OpenAPIGroupSection(self.parser, group_name)   

                for tag in group["tags"]:
                    if tag not in self.sections:
                        self.log.add(f'Tag {tag} assigned not found!: tag-group {group_name} ')
             
        self.env.log(f'==============================================================')
           
    ##
    ## Identify the test cases in the openAPI file
    ##

    def getTestCases(self, spec: dict):

        try:
            
            case_count = 0
            for path, path_data in spec["paths"].items():

                for verb, verb_details in path_data.items():

                    key = f'{verb}:{path}'

                    if verb.lower() not in ["get", "put", "patch", "post", "delete", "options", "trace", "connect"]:
                        continue
                    if "responses" not in verb_details.keys():
                        continue
                    
                    group, name, description, operationId = self.__getDetails(verb_details, key)

                    if group not in self.sections:
                        self.sections[group] = OpenAPIShortSection(self.parser, name, description)
                    
                    for response, response_data in verb_details["responses"].items():
                        request_details = verb_details.copy()
                        request_details.pop("responses")
                        openapi_test = OpenApiTestCase(
                            path=path,
                            verb=verb,
                            operation_id=operationId,
                            request_details=request_details,
                            response_code=response,
                            response_description=response_data.get("description", None),
                            response_details=response_data
                        )
                        section: TestRailSection = self.sections[group]
                        section.testcases.append(
                            TestRailCase(
                                openapi_test.name,
                                custom_automation_id=f"{openapi_test.unique_id}",
                                result=TestRailResult(),
                                case_fields={
                                    "template_id": 1,
                                    "custom_preconds": openapi_test.preconditions,
                                    "custom_steps": openapi_test.steps,
                                    "custom_expected": openapi_test.expected
                                }
                            )
                        )

                        self.env.log(f' ... {openapi_test.name}')
                        case_count += 1
            
            return self.sections, case_count

        except Exception as e:
            self.env.log(f'Process Failure: -error: {e}')

    ##
    ## Get tag information
    ##    
    
    def __getDetails(self, verb_details, key: str):

        tag = self.__getTag(verb_details, key)
       
        ## Check missing information in openAPI file

        operationId = verb_details.get("operationId")
        summary = verb_details.get("summary", None)
        description = verb_details.get("description", None)

        if tag not in self.sections:
            self.log.add(f'Tag [{tag}] not found!: {key}')
            self.sections[tag] = OpenAPITagSection(self.parser, tag)          

        if summary is None:
            self.log.add(f'Summary not found!: {key}')

        if operationId is None:
            self.log.add(f'Operation Id not found!: {key}')

        if operationId is not None:      
            group = operationId
        else:
            group =  key

        if summary is not None:
            name = summary
        else:
            name =  group
       
        return group, name, description, operationId
       
    def __getTag(self, verb_details, key: str) -> str:

        tag = "untagged"

        if "tags" in verb_details.keys() and len(verb_details["tags"]):

            ## Identify the current API's assigned tag
            for item in verb_details["tags"]:
                if item in self.sections:
                    tag = item
                    break
            
            if tag is None:
                self.log.add(f'<Tags> list does not match!: {key}')

        else:
            self.log.add(f'<Tags> not found!: {key}')

        return tag


class OpenAPIGroupSection(TestRailSection):

    def __init__(self, parser: OpenApiParser, name: str):
        super().__init__(name)
        parser.env.log(f'Group-Section#: {name}')

class OpenAPITagSection(TestRailSection):

    def __init__(self, parser: OpenApiParser, name: str, description = None):
        super().__init__(name, description=description)
        parser.env.log(f'Tag-Section#: {name}')

class OpenAPIShortSection(TestRailSection):

    def __init__(self, parser: OpenApiParser, name: str, description: str):
        super().__init__(name, description=description)
        parser.env.log(f'Short-Section#: {name}')

