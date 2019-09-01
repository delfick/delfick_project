from delfick_error import DelfickErrorTestMixin
from unittest import TestCase

import uuid

class TestCase(TestCase, DelfickErrorTestMixin):
    def unique_value(self):
        return str(uuid.uuid1())
