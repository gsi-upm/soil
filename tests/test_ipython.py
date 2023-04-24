from unittest import TestCase
import os
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

ROOT = os.path.abspath(os.path.dirname(__file__))

class TestNotebooks(TestCase):
    def test_tutorial(self):
        notebook = os.path.join(ROOT, "../docs/tutorial/soil_tutorial.ipynb")
        with open(notebook) as f:
            nb = nbformat.read(f, as_version=4)
            ep = ExecutePreprocessor(timeout=60000)
            try:
                assert ep.preprocess(nb) is not None, f"Got empty notebook for {notebook}"
            except Exception:
                assert False, f"Failed executing {notebook}"

