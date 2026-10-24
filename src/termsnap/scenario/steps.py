"""
Шаги сценария и момент снимка экрана.
"""

from dataclasses import dataclass

from termsnap.scenario.keys import Keys


@dataclass(frozen=True, slots=True)
class Pause:
    """
    Подождать ``seconds`` секунд, прежде чем двигаться дальше.
    """

    seconds: float


#: Шаг сценария: строка (печатается с Enter), клавиши как есть (без Enter) или пауза.
type Step = str | Keys | Pause


@dataclass(frozen=True, slots=True)
class Snapshot:
    """
    Когда снимать экран у программы, которая сама не завершается (``htop``, ``top``, ``nvtop``), и остановить ее.

    Экран снимается, когда выполнены все условия: ``input`` напечатан целиком, ``when`` (регулярное выражение)
    нашлось в тексте экрана, прошло ``after`` секунд с последнего из этих событий. Если указано только ``after``,
    отсчет идет от запуска (или от последней напечатанной строки). Не дождались - ``RunTimeout`` по общему
    времени ``timeout``.
    """

    after: float = 0.0
    when: str | None = None
