import pytest

pytestmark = pytest.mark.ui


@pytest.mark.skip(reason="UI-слой ещё не подключён: добавьте сценарии в tests/ui/")
def test_ui_layer_placeholder():
    pass
