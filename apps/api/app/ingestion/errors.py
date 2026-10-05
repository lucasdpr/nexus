class PipelineError(Exception):
    """Falha definitiva do documento (arquivo corrompido, sem texto...). Repetir não ajuda.

    A mensagem é mostrada ao usuário.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
