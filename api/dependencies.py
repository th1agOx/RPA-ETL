"""
FastAPI dependency injection utilities.
Handles context generation, validation, and request processing.
"""
import uuid
from typing import Annotated
from fastapi import Form, UploadFile, File, HTTPException, status
from rpa_config import settings
from api.schemas import BusinessContext, parse_context_from_form


async def validate_pdf_file(file: UploadFile) -> bytes:
    """
    Validate uploaded PDF file.
    
    Args:
        file: Uploaded file from multipart form
        
    Returns:
        File bytes
        
    Raises:
        HTTPException: If validation fails
    """
    # Check content type
    if file.content_type not in settings.ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Invalid content type. Expected: {settings.ALLOWED_CONTENT_TYPES}"
        )
    
    # Read file
    content = await file.read()
    
    # Check size
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {settings.API_MAX_UPLOAD_SIZE_MB}MB"
        )
    
    # Basic PDF magic number check
    if not content.startswith(b'%PDF'):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid PDF file format"
        )
    
    return content


async def parse_business_context(context: Annotated[str, Form()]) -> BusinessContext:
    """
    Parse and validate business context from form data.
    
    Args:
        context: JSON string from form field
        
    Returns:
        Validated BusinessContext
        
    Raises:
        HTTPException: If parsing or validation fails
    """
    try:
        business_context = parse_context_from_form(context)
        
        # Generate IDs if not provided
        if not business_context.trace_id:
            business_context.trace_id = str(uuid.uuid4())
        
        if not business_context.execution_id:
            business_context.execution_id = f"{business_context.tenant_id}_{uuid.uuid4().hex[:12]}"
        
        return business_context
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
