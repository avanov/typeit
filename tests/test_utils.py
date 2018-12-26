from typeit import utils


def test_normalization():
    name = 'abc'
    normalized = utils.normalize_name(name)
    assert normalized == name

    name = 'def'
    normalized = utils.normalize_name(name)
    assert normalized == 'overridden__def'
