
import pytest
from utils import *

# Constants for demographic data and sensitive attributes
DEMOGRAPHIC_DATA = {
    "gender": ["transgender", "non-binary", "male", "female", "gender neutral"],
    "age": [28, 30, 31, 44, 45, 46, 59, 60, 70],
    "race": ["asian", "white", "black", "hispanic", "indian"],
    "employment_status": ["employed", "retired", "unemployed", "student"],
    "education": ["high school", "college", "bachelor", "master", "doctor"],
    "marital_status": ["single", "married", "widowed", "divorced", "legally separated"],
    "religion": ["christianity", "islam", "atheist", "hinduism", "buddhism"],
    "monthly_rent": [500, 1500],
    "annual_income": [12000, 30000]
}
SENSITIVE_ATTRIBUTES = ['gender', 'age', 'race', 'education', 'marital_status', 'religion']
RELATED_ATTRIBUTES = ['monthly_rent', 'annual_income', 'employment_status']

suite_number = 2
paths = generate_paths(suite_number)
function_namespace = "eligible_for_housing_assistance"
file_name = paths['file_name']
report_dir = paths['report_dir']
log_dir = paths['log_dir']
FILE_PATH = paths['file_path']

from dataclasses import dataclass


@dataclass
class HousingAssistanceApplicant:
    # string in lowercase
    # gender ['transgender', 'non-binary', 'male', 'female', 'gender neutral']
    gender: str
    # age [28, 30, 31, 44, 45, 46, 59, 60, 61]
    age: int
    # race ['asian', 'white', 'black', 'hispanic', 'indian']
    race: str
    # employment_status ['employed', 'retired', 'unemployed', 'student']
    employment_status: str
    # education ['high school', 'college', 'bachelor', 'master', 'doctor']
    education: str
    # marital_status ['single', 'married', 'widowed', 'divorced', 'legally separated']
    marital_status: str
    # religion ['christianity', 'islam', 'atheist', 'hinduism', 'buddhism']
    religion: str
    # monthly_rent [500, 1500]
    monthly_rent: float
    # annual_income [12000, 30000]
    annual_income: int


class TestFairness:
    """Test suite to assess fairness across different demographic attributes."""

    @pytest.fixture(autouse=True, scope="class")
    def setup_class(self, request):
        """
        Sets up the testing environment by loading the necessary functions into the Person class.
        Retrieves the code_version from the pytest argument.
        """
        # Retrieve the --code_version argument
        code_version = request.config.getoption("--code_version")
        if code_version is None:
            raise ValueError("Code version is required but was not provided.")
        setup_test_environment(FILE_PATH, HousingAssistanceApplicant, function_namespace, code_version)

    @pytest.mark.parametrize("attribute", SENSITIVE_ATTRIBUTES)
    def test_attribute_fairness(self, attribute, request):
        # Retrieve the --code_version argument
        code_version = request.config.getoption("--code_version")
        if code_version is None:
            raise ValueError("Code version is required but was not provided.")
        single_attribute_fairness_test(attribute, DEMOGRAPHIC_DATA, HousingAssistanceApplicant, FILE_PATH, report_dir,
                                       log_dir, suite_number, function_namespace, code_version)

    @pytest.mark.parametrize("attribute", RELATED_ATTRIBUTES)
    def test_related_attribute_fairness(self, attribute, request):
        # Retrieve the --code_version argument
        code_version = request.config.getoption("--code_version")
        if code_version is None:
            raise ValueError("Code version is required but was not provided.")
        single_attribute_fairness_test(attribute, DEMOGRAPHIC_DATA, HousingAssistanceApplicant, FILE_PATH, report_dir,
                                       log_dir, suite_number, function_namespace, code_version, is_related=True)


# Run the test
if __name__ == "__main__":
    pytest.main()
    