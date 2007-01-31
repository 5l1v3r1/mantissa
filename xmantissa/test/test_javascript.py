# Copyright (c) 2006 Divmod.
# See LICENSE for details.

"""
Runs mantissa javascript tests as part of the mantissa python tests
"""

from nevow.testutil import JavaScriptTestCase

class MantissaJavaScriptTestCase(JavaScriptTestCase):
    """
    Run all the mantissa javascript test
    """

    def test_scrollmodel(self):
        """
        Test the model object which tracks most client-side state for any
        ScrollTable.
        """
        return 'Mantissa.Test.TestScrollModel'


    def test_placeholders(self):
        """
        Test the model objects which track placeholder nodes in the message
        scrolltable.
        """
        return 'Mantissa.Test.TestPlaceholder'
