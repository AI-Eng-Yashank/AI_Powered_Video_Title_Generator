import os
import uuid
import aiofiles
from pathlib import Path
from fastapi import UploadFile, HTTPException
from typing import Optional

from app.config import get_settings


class VideoUploadModule:
    """
    Handles video file uploads with validation and storage.
    
    Responsibilities:
    - Validate file format and size
    - Generate unique filenames
    - Store files securely
    - Clean up temporary files
    """
    
    def __init__(self, upload_dir: Optional[str] = None):
        settings = get_settings()
        self.upload_dir = Path(upload_dir or settings.upload_dir)
        self.allowed_extensions = settings.allowed_extensions_list
        self.max_size_bytes = settings.max_upload_size_bytes
        
        # Ensure upload directory exists
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def _validate_extension(self, filename: str) -> str:
        """Validate file extension and return it."""
        if not filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        
        if ext not in self.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file format. Allowed: {', '.join(self.allowed_extensions)}"
            )
        return ext
    
    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate a unique filename preserving the original extension."""
        ext = self._validate_extension(original_filename)
        unique_id = uuid.uuid4().hex[:12]
        return f"{unique_id}.{ext}"
    
    async def save_upload(self, file: UploadFile) -> Path:
        """
        Save uploaded file to disk with validation.
        
        Args:
            file: The uploaded file from FastAPI
            
        Returns:
            Path to the saved file
            
        Raises:
            HTTPException: If validation fails
        """
        # Validate extension
        self._validate_extension(file.filename or "")
        
        # Generate unique filename
        unique_filename = self._generate_unique_filename(file.filename or "video.mp4")
        file_path = self.upload_dir / unique_filename
        
        # Stream file to disk with size validation
        total_size = 0
        
        async with aiofiles.open(file_path, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                total_size += len(chunk)
                
                if total_size > self.max_size_bytes:
                    # Clean up partial file
                    await out_file.close()
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size: {self.max_size_bytes // (1024*1024)}MB"
                    )
                
                await out_file.write(chunk)
        
        return file_path
    
    async def cleanup(self, file_path: Path) -> None:
        """Remove a file from storage."""
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass  # Best effort cleanup
    
    def get_file_info(self, file_path: Path) -> dict:
        """Get information about a stored file."""
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        stat = file_path.stat()
        return {
            "filename": file_path.name,
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "path": str(file_path),
        }
