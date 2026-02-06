"""
FastAPI application entry point.
Handles PDF ingestion with strict separation of concerns:
- API validates input and dispatches
- Orchestrator makes all business decisions
- No persistence or fiscal validation at API layer
"""
from datetime import datetime
from typing import Annotated
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from rpa_config import settings
from api.schemas import ProcessResponse, HealthResponse, BusinessContext
from api.dependencies import validate_pdf_file, parse_business_context

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="RPA ETL API for fiscal document extraction and orchestration",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Returns service status and basic diagnostics.
    """
    # TODO: Add actual health checks (Redis, DB, etc.) in future milestones
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        checks={
            "api": True,
            # "redis": False,  # Will be added in Milestone 4
            # "audit_store": False,  # Will be added in Milestone 2
        }
    )


@app.post("/v1/process/pdf", response_model=ProcessResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Processing"])
async def process_pdf(
    file: Annotated[UploadFile, File(description="PDF file to process")],
    context: Annotated[BusinessContext, Depends(parse_business_context)]
):
    """
    Process a PDF document.
    
    **Request Format (multipart/form-data):**
    - `file`: PDF file (max 10MB)
    - `context`: JSON string with business context
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8000/v1/process/pdf \\
      -F "file=@invoice.pdf" \\
      -F 'context={"tenant_id":"acme-corp","pipeline":"enterprise"}'
    ```
    
    **Flow:**
    1. Validate file format and size
    2. Parse and validate business context
    3. Generate execution_id if not provided
    4. Dispatch to orchestrator (mock for Milestone 1)
    5. Return 202 Accepted immediately
    """
    try:
        # Validate file
        pdf_bytes = await validate_pdf_file(file)
        
        # TODO Milestone 3: Dispatch to Orchestrator
        # TODO Milestone 4: Dispatch to Celery if pipeline == "enterprise"
        # TODO Milestone 6: Dispatch to n8n if pipeline == "custom"
        
        # Mock response for Milestone 1
        return ProcessResponse(
            execution_id=context.execution_id,
            status="accepted",
            message=f"PDF accepted for processing (size: {len(pdf_bytes)} bytes)",
            trace_id=context.trace_id,
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal processing error: {str(e)}"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unexpected errors.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
