from PySide6.QtCore import QThread, Signal
from core.engine import MultimodalEngine

class EngineInitWorker(QThread):
    finished = Signal(object) # Returns the engine instance or None
    error = Signal(str)
    log = Signal(str)

    def __init__(self, base_dir: str):
        super().__init__()
        self.base_dir = base_dir

    def run(self):
        try:
            self.log.emit("Начало инициализации движка...")
            engine = MultimodalEngine(
                base_dir=self.base_dir,
                log_callback=lambda msg: self.log.emit(msg)
            )
            self.finished.emit(engine)
        except Exception as e:
            self.error.emit(f"Ошибка инициализации: {str(e)}")
            self.finished.emit(None)

class SyncWorker(QThread):
    finished = Signal()
    error = Signal(str)
    log = Signal(str)
    progress = Signal(int, str)

    def __init__(self, engine: MultimodalEngine):
        super().__init__()
        self.engine = engine

    def run(self):
        try:
            self.engine.log_cb = lambda msg: self.log.emit(msg)
            self.engine.prog_cb = lambda p, m: self.progress.emit(p, m)
            self.engine.sync()
            self.finished.emit()
        except Exception as e:
            self.error.emit(f"Ошибка синхронизации: {str(e)}")
            self.finished.emit()

class RouteWorker(QThread):
    finished = Signal()
    error = Signal(str)
    log = Signal(str)
    progress = Signal(int, str)
    result = Signal(str, str, str) # filename, status, reason

    def __init__(self, engine: MultimodalEngine, target_dir: str):
        super().__init__()
        self.engine = engine
        self.target_dir = target_dir

    def run(self):
        try:
            self.engine.log_cb = lambda msg: self.log.emit(msg)
            self.engine.prog_cb = lambda p, m: self.progress.emit(p, m)
            self.engine.result_cb = lambda f, s, r: self.result.emit(f, s, r)
            self.engine.route(self.target_dir)
            self.finished.emit()
        except Exception as e:
            self.error.emit(f"Ошибка сканирования: {str(e)}")
            self.finished.emit()
