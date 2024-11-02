import json
import unittest
from contextlib import contextmanager

from django.db import connections
from django.test.utils import CaptureQueriesContext


class AssertNumQueriesLessThanMixin(unittest.TestCase):
    @contextmanager
    def assertNumQueriesLessThan(self, value, using='default', verbose=False):
        with CaptureQueriesContext(connections[using]) as context:
            yield  # your test will be run here
        if verbose:
            msg = "\r\n%s" % json.dumps(context.captured_queries, indent=4)
        else:
            msg = None
        self.assertLess(len(context.captured_queries), value, msg=msg)
