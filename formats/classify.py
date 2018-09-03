from .converter import ConversionError
from .transcriptic import Transcriptic
from .ginkgo import Ginkgo
from .biofab import Biofab


class NoClassifierError(ConversionError):
    pass

def get_converter(json_filepath):

    try:
        t = Transcriptic()
        t.validate_input(json_filepath)
        return t
    except Exception:
        pass

    try:
        g = Ginkgo()
        g.validate_input(json_filepath)
        return g
    except Exception:
        pass

    try:
        b = Biofab()
        b.validate_input(json_filepath)
        return b
    except Exception:
        pass

    raise NoClassifierError('Classification failed for {}'.format(json_filepath))

