import sys
from ..converter import Converter, ConversionError, ValidationError
from .runner import convert_ginkgo

class Ginkgo(Converter):
    def convert(self, input_fp, output_fp=None, verbose=True, config={}, enforce_validation=True):
        # schema_file, input_file, verbose=True, output=True, output_file=None
        passed_config = self.options
        if config != {}:
            passed_config = config
        return convert_ginkgo(self.targetschema, input_fp, verbose=verbose, config=passed_config, output_file=output_fp, enforce_validation=enforce_validation, reactor=self.reactor)
