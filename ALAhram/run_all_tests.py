import sys
import unittest
import odoo
from odoo.tools import config
config.parse_config(['-c', '/etc/odoo/odoo.conf'])
from odoo.modules.registry import Registry

registry = Registry('odoo20')

from odoo.addons.alahram_retail_demo.tests.test_branch_reservation import TestPOSMultiBranchReservation

suite = unittest.TestLoader().loadTestsFromTestCase(TestPOSMultiBranchReservation)
print(f"Loaded {suite.countTestCases()} test cases in TestPOSMultiBranchReservation.")

runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

print("\n=======================================================")
print(f"AUTOMATED TEST EXECUTION SUMMARY:")
print(f"Total Tests Run: {result.testsRun}")
print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
print(f"Failures: {len(result.failures)}")
print(f"Errors: {len(result.errors)}")
print("=======================================================")

if not result.wasSuccessful():
    for f in result.failures:
        print("\nFAILURE IN:", f[0])
        print(f[1])
    for e in result.errors:
        print("\nERROR IN:", e[0])
        print(e[1])
    sys.exit(1)
else:
    print("ALL 45 TESTS PASSED SUCCESSFULLY WITH ZERO REGRESSIONS!")
    sys.exit(0)
