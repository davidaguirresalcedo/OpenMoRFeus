"""Device-level exceptions for OpenMoRFeus."""


class OpenMoRFeusError(Exception):
    """Base exception for OpenMoRFeus."""


class DeviceError(OpenMoRFeusError):
    """Base exception for device-access failures."""


class DeviceNotFoundError(DeviceError):
    """Raised when no compatible moRFeus device is found."""


class DeviceResponseError(DeviceError):
    """Raised when the device returns a textual error message."""


class UnexpectedResponseError(DeviceError):
    """Raised when the response does not match the request."""


class UnsupportedValueError(DeviceError):
    """Raised when the device returns an undocumented value."""



class VerificationError(DeviceError):
    """Raised when read-back does not confirm a written value."""



class ResponseTimeoutError(DeviceError):
    """Raised when no matching response arrives before timeout."""
