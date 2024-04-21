class AudioConversionError(Exception):
    """Exception raised for errors in the audio conversion process."""

    pass


class APIError(Exception):
    """Custom exception for API error handling."""

    def __init__(self, message, status_code=None, details=None):
        if details:
            super().__init__(f"{message} - Details: {details}")
        else:
            super().__init__(message)
        self.status_code = status_code
