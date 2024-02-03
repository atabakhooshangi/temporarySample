from enum import Enum

class APICallResultType(Enum):
    SUCCESSFUL = 1
    API_ERROR = 2
    EXCEPTION = 3


class HTTPMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"