class DocumentProcessingError(Exception):

    def __init__(
        self,
        message: str,
        status: str,
        stage: str,
        retryable: bool = False
    ):

        super().__init__(message)

        self.message = message
        self.status = status
        self.stage = stage
        self.retryable = retryable