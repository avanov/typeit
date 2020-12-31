from pathlib import Path

TESTS_ROOT = Path(__file__).parent.absolute()
VCR_FIXTURES_PATH = TESTS_ROOT / "vcr"

PETSTORE_SPEC = TESTS_ROOT / 'petstore.json'