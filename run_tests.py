#!/usr/bin/env python
# Run selected tests with environment variables for configuration
#
# Usage:
#   # Create a .env file or export environment variables:
#   export WEBULL_APP_KEY="your_app_key"
#   export WEBULL_APP_SECRET="your_app_secret"
#   export WEBULL_REGION_ID="your_region_id"
#   export WEBULL_API_ENDPOINT="your_api_endpoint"
#   export WEBULL_ACCOUNT_ID="your_account_id"
#
#   python run_tests.py --tests data,trade,api
#   python run_tests.py --tests data
#   python run_tests.py --tests all

import argparse
import importlib
import importlib.util
import os
import sys
import types
import unittest
from dotenv import load_dotenv

load_dotenv()

# Get configuration from environment variables
ENV_CONFIG = {
    'optional_api_endpoint': os.getenv('WEBULL_API_ENDPOINT', 'api.sandbox.webull.hk'),
    'your_app_key': os.getenv('WEBULL_APP_KEY', '<your_app_key>'),
    'your_app_secret': os.getenv('WEBULL_APP_SECRET', '<your_app_secret>'),
    'region_id': os.getenv('WEBULL_REGION_ID', '<region_id>'),
    'account_id': os.getenv('WEBULL_ACCOUNT_ID', '<your_account_id>'),
}

# Available test modules mapping
TEST_MODULES = {
    'api': 'tests.core.api.test_api',
    'data': 'tests.data.test_data_client',
    'data_streaming': 'tests.data.test_data_streaming_client',
    'trade': 'tests.trade.test_trade_client',
    'trade_v2': 'tests.trade.test_trade_client_v2',
    'trade_event': 'tests.trade.test_trade_event_client',
}


def get_module_path(module_name):
    """Convert module name to file path."""
    return module_name.replace('.', '/') + '.py'


def load_module_with_replaced_variables(module_name):
    """
    Load a module after replacing placeholder variables in its source code.
    This allows us to inject environment variables before the module-level code runs.
    """
    module_path = get_module_path(module_name)

    # Read the original source
    with open(module_path, 'r') as f:
        source = f.read()

    # Replace placeholder variables with actual values
    replacements = {
        '"<api_endpoint>"': f'"{ENV_CONFIG["optional_api_endpoint"]}"',
        "'<api_endpoint>'": f'"{ENV_CONFIG["optional_api_endpoint"]}"',
        '"<your_app_key>"': f'"{ENV_CONFIG["your_app_key"]}"',
        "'<your_app_key>'": f'"{ENV_CONFIG["your_app_key"]}"',
        '"<your_app_secret>"': f'"{ENV_CONFIG["your_app_secret"]}"',
        "'<your_app_secret>'": f'"{ENV_CONFIG["your_app_secret"]}"',
        '"<region_id>"': f'"{ENV_CONFIG["region_id"]}"',
        "'<region_id>'": f'"{ENV_CONFIG["region_id"]}"',
        '"<your_account_id>"': f'"{ENV_CONFIG["account_id"]}"',
        "'<your_account_id>'": f'"{ENV_CONFIG["account_id"]}"',
    }

    modified_source = source
    for old, new in replacements.items():
        modified_source = modified_source.replace(old, new)

    # Create a new module from the modified source
    spec = importlib.util.spec_from_loader(module_name, loader=None)
    module = types.ModuleType(spec.name)
    module.__file__ = module_path
    module.__loader__ = None
    module.__spec__ = spec

    # Add the module to sys.modules before executing (needed for relative imports)
    sys.modules[module_name] = module

    # Execute the modified source in the module's namespace
    exec(compile(modified_source, module_path, 'exec'), module.__dict__)

    return module


def load_tests_from_module(module_name):
    """Load tests from a module with replaced environment variables."""
    try:
        module = load_module_with_replaced_variables(module_name)
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(module)
        return suite
    except Exception as e:
        print(f"Warning: Could not load tests from {module_name}: {e}")
        import traceback
        traceback.print_exc()
        return unittest.TestSuite()


def main():
    parser = argparse.ArgumentParser(description='Run Webull API tests with environment variables')
    parser.add_argument(
        '--tests', '-t',
        type=str,
        default='all',
        help=f'Comma-separated list of tests to run. Available: {", ".join(TEST_MODULES.keys())}, all'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List available test modules'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    if args.list:
        print("Available test modules:")
        for name, module in TEST_MODULES.items():
            print(f"  {name}: {module}")
        return 0

    # Determine which tests to run
    if args.tests.lower() == 'all':
        selected_tests = list(TEST_MODULES.keys())
    else:
        selected_tests = [t.strip() for t in args.tests.split(',')]

    # Validate test names
    for test_name in selected_tests:
        if test_name not in TEST_MODULES:
            print(f"Error: Unknown test '{test_name}'")
            print(f"Available tests: {', '.join(TEST_MODULES.keys())}")
            return 1

    print(f"Running tests: {', '.join(selected_tests)}")
    print(f"Using config from environment variables:")
    for key, value in ENV_CONFIG.items():
        # Mask secrets
        if 'secret' in key.lower() or 'key' in key.lower():
            display_value = value[:4] + '****' if len(value) > 4 else '****'
        else:
            display_value = value
        print(f"  {key}: {display_value}")
    print()

    # Create test suite
    suite = unittest.TestSuite()

    for test_name in selected_tests:
        module_name = TEST_MODULES[test_name]
        print(f"Loading tests from: {module_name}")
        suite.addTests(load_tests_from_module(module_name))

    # Run tests
    verbosity = 2 if args.verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())

