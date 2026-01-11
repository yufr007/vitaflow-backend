"""
VitaFlow API - Custom Exception Classes.

Exception hierarchy for application error handling.
"""

from typing import Optional


class VitaFlowException(Exception):
    """
    Base exception class for VitaFlow application.
    
    All custom exceptions should inherit from this class.
    
    Attributes:
        message: Human-readable error message.
        status_code: HTTP status code for the error.
        detail: Additional error details.
    """
    
    def __init__(
        self,
        message: str = "An error occurred",
        status_code: int = 500,
        detail: Optional[str] = None
    ):
        """
        Initialize VitaFlowException.
        
        Args:
            message: Human-readable error message.
            status_code: HTTP status code (default 500).
            detail: Additional error details.
        """
        self.message = message
        self.status_code = status_code
        self.detail = detail or message
        super().__init__(self.message)


class AuthenticationError(VitaFlowException):
    """
    Exception raised for authentication failures.
    
    Used when:
    - Invalid credentials
    - Expired tokens
    - Missing authentication
    """
    
    def __init__(
        self,
        message: str = "Authentication failed",
        detail: Optional[str] = None
    ):
        """
        Initialize AuthenticationError.
        
        Args:
            message: Error message.
            detail: Additional details.
        """
        super().__init__(
            message=message,
            status_code=401,
            detail=detail
        )


class NotFoundError(VitaFlowException):
    """
    Exception raised when a resource is not found.
    
    Used when:
    - User not found
    - Record not found
    - Resource does not exist
    """
    
    def __init__(
        self,
        message: str = "Resource not found",
        detail: Optional[str] = None
    ):
        """
        Initialize NotFoundError.
        
        Args:
            message: Error message.
            detail: Additional details.
        """
        super().__init__(
            message=message,
            status_code=404,
            detail=detail
        )


class ValidationError(VitaFlowException):
    """
    Exception raised for input validation failures.
    
    Used when:
    - Invalid input format
    - Missing required fields
    - Business rule violations
    """
    
    def __init__(
        self,
        message: str = "Validation error",
        detail: Optional[str] = None
    ):
        """
        Initialize ValidationError.
        
        Args:
            message: Error message.
            detail: Additional details.
        """
        super().__init__(
            message=message,
            status_code=400,
            detail=detail
        )


class ForbiddenError(VitaFlowException):
    """
    Exception raised for authorization failures.
    
    Used when:
    - User lacks permission
    - Access denied to resource
    """
    
    def __init__(
        self,
        message: str = "Access denied",
        detail: Optional[str] = None
    ):
        """
        Initialize ForbiddenError.
        
        Args:
            message: Error message.
            detail: Additional details.
        """
        super().__init__(
            message=message,
            status_code=403,
            detail=detail
        )


class ConflictError(VitaFlowException):
    """
    Exception raised for resource conflicts.
    
    Used when:
    - Duplicate entry
    - Resource already exists
    """
    
    def __init__(
        self,
        message: str = "Resource conflict",
        detail: Optional[str] = None
    ):
        """
        Initialize ConflictError.
        
        Args:
            message: Error message.
            detail: Additional details.
        """
        super().__init__(
            message=message,
            status_code=409,
            detail=detail
        )
