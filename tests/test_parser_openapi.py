from dataclasses import asdict
from pathlib import Path

import pytest

from trcli.cli import Environment
from trcli.data_classes.data_parsers import MatchersParser
from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.readers.openapi import OpenApiParser


class TestOpenApiParser:

    @pytest.mark.parse_openapi
    @pytest.mark.parametrize(
        "data_flow",
        [
            {"file_name": "authz_v1_swagger.json", "compatible": True},
            {"file_name": "authz_v2_swagger.json", "compatible": True},
            {"file_name": "authz_v3_swagger.json", "compatible": True}
        ],
        ids=[
            "Authv1",
            "Authv2",
            "Authv3",
        ],
    )
    def test_openapi_parser_section(self, data_flow):
        self.__parser_check(data_flow, type="section")

    @pytest.mark.parametrize(
        "data_flow",
        [
            {"file_name": "openapi_20.json", "compatible": False},
            {"file_name": "openapi_30.json", "compatible": True},
            {"file_name": "openapi_31.json", "compatible": True}
        ],
        ids=[
            "layout 2.0 - NOT Compatible",
            "layout 3.0 - Compatible",
            "layout 3.1 - Compatible"],
    )
    def test_openapi_parser_layout(self, data_flow):
        self.__parser_check(data_flow, type="layout")

    @pytest.mark.parse_openapi
    @pytest.mark.parametrize(
        "data_flow",
        [
            {"file_name": "authz_v1_swagger.json", "compatible": True},
            {"file_name": "authz_v2_swagger.json", "compatible": True}
        ],
        ids=[
            "Authv1",
            "Authv2",
        ],
    )
    def test_openapi_parser_version(self, data_flow):
        self.__parser_check(data_flow, type="version")

    @pytest.mark.parse_openapi
    @pytest.mark.parametrize(
        "data_flow",
        [                  
            {"file_name": "authz_swagger.json", "compatible": True},
            {"file_name": "authn_swagger.json", "compatible": True},
            {"file_name": "cust_user_mgmt_swagger.json", "compatible": True},
            {"file_name": "ui_doorway_swagger.json", "compatible": True},
        ],
        ids=[
            "Authv",
            "Authn",
            "AccountManagement",
            "UI-Doorway"
        ],
    )
    def test_openapi_parser_system(self, data_flow):
        self.__parser_check(data_flow, type="system")

    def __parser_check(self, data: {"file_name": str, "compatible": bool}, type: str):

        file_name = data["file_name"]
        compatible = data["compatible"]
        env = Environment()
        env.case_matcher = MatchersParser.AUTO
        env.file = Path(__file__).parent / f"test_data/openapi/{type}" / file_name
        file_input = OpenApiParser(env)
        success = False
        try:
            parse_content = file_input.parse_file(save = True)[0]
            success = True

            read_input = self.__clear_unparsable_openapi_elements(parse_content)
            parsing_result = asdict(read_input)

            env.log(f'==> IS compatible: {file_name}!')

        except:
            env.log(f'==> NOT compatible: {file_name}!')

        # path_new = Path(__file__).parent / "test_data/openapi/result" / file_name
        # if self.__save_file(path_new, parsing_result):
        #     file_output = open(path_new)
        #     expected_result = json.load(file_output)
        #     assert DeepDiff(parsing_result, expected_result) == {}, \
        #         f"Result of parsing OpenApi is different than expected \n{DeepDiff(parsing_result, expected_result)}"
        assert success == compatible, "Bad Result"   
    
    def __clear_unparsable_openapi_elements(self, suite: TestRailSuite) -> TestRailSuite:
        for section in suite.testsections:
            for testcase in section.testcases:
                testcase.result.junit_result_unparsed = []

        return suite
