class FlightDelayException(Exception):
    pass

class APIException(FlightDelayException):
    pass

class APIAuthenticationError(APIException):
    pass

class APIRateLimitError(APIException):
    pass

class APITimeoutError(APIException):
    pass

class DatabaseException(FlightDelayException):
    pass

class DatabaseConnectionError(DatabaseException):
    pass

class DatabaseWriteError(DatabaseException):
    pass
