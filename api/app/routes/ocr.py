# Copyright (C) 2021-2025, Mindee.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://opensource.org/licenses/Apache-2.0> for full license details.


from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.docx_extractor import extract_text_from_docx
from app.schemas import DocumentTextOut, OCRBlock, OCRIn, OCRLine, OCROut, OCRPage, OCRWord
from app.utils import get_documents, resolve_geometry
from app.vision import init_predictor

router = APIRouter()


@router.post("/", response_model=list[OCROut], status_code=status.HTTP_200_OK, summary="Perform OCR")
async def perform_ocr(request: OCRIn = Depends(), files: list[UploadFile] = [File(...)]):
    """Runs docTR OCR model to analyze the input image"""
    try:
        # generator object to list
        content, filenames = await get_documents(files)
        predictor = init_predictor(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    out = predictor(content)

    results = [
        OCROut(
            name=filenames[i],
            orientation=page.orientation,
            language=page.language,
            dimensions=page.dimensions,
            items=[
                OCRPage(
                    blocks=[
                        OCRBlock(
                            geometry=resolve_geometry(block.geometry),
                            objectness_score=round(block.objectness_score, 2),
                            lines=[
                                OCRLine(
                                    geometry=resolve_geometry(line.geometry),
                                    objectness_score=round(line.objectness_score, 2),
                                    words=[
                                        OCRWord(
                                            value=word.value,
                                            geometry=resolve_geometry(word.geometry),
                                            objectness_score=round(word.objectness_score, 2),
                                            confidence=round(word.confidence, 2),
                                            crop_orientation=word.crop_orientation,
                                        )
                                        for word in line.words
                                    ],
                                )
                                for line in block.lines
                            ],
                        )
                        for block in page.blocks
                    ]
                )
            ],
        )
        for i, page in enumerate(out.pages)
    ]

    return results


@router.post(
    "/text",
    response_model=list[DocumentTextOut],
    status_code=status.HTTP_200_OK,
    summary="Extract plain text from documents using OCR",
)
async def extract_text(request: OCRIn = Depends(), files: list[UploadFile] = [File(...)]):
    """Runs docTR OCR model and returns flattened text for each page of each input document."""
    try:
        content, filenames = await get_documents(files)
        predictor = init_predictor(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    out = predictor(content)

    results: list[DocumentTextOut] = []
    for i, page in enumerate(out.pages):
        lines: list[str] = []
        for block in page.blocks:
            for line in block.lines:
                line_text = " ".join(word.value for word in line.words if word.value)
                if line_text.strip():
                    lines.append(line_text.strip())
        results.append(DocumentTextOut(name=filenames[i], text="\n".join(lines)))

    return results


@router.post(
    "/extract-resume",
    response_model=list[DocumentTextOut],
    status_code=status.HTTP_200_OK,
    summary="Extract raw text from documents (PDF, DOCX, etc.)",
)
async def extract_resume(
    request: OCRIn = Depends(),
    files: list[UploadFile] = [File(...)]
):
    """
    Extracts raw text from documents (PDF, DOCX, DOC, TXT, RTF, ODT, images).
    Returns plain text without any structured parsing.
    
    For DOCX files, text is extracted directly (bypassing OCR) for better accuracy.
    For other formats (PDF, images), OCR is used.
    """
    results: list[DocumentTextOut] = []
    
    for file in files:
        mime_type = file.content_type or ""
        filename = file.filename or ""
        file_content = await file.read()
        
        # For DOCX files, extract text directly (bypass OCR)
        if (mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or 
            filename.lower().endswith('.docx')):
            try:
                full_text = extract_text_from_docx(file_content)
                results.append(DocumentTextOut(name=filename, text=full_text))
                continue
            except ValueError as e:
                # If direct extraction fails, fall back to OCR
                error_msg = str(e)
                if "empty" in error_msg.lower() or "no extractable text" in error_msg.lower():
                    # Fall back to OCR conversion method
                    try:
                        from fastapi import UploadFile as FastAPIUploadFile
                        from io import BytesIO
                        
                        headers = dict(file.headers) if file.headers else {}
                        if mime_type:
                            headers['content-type'] = mime_type
                        
                        file_obj = FastAPIUploadFile(
                            filename=filename,
                            file=BytesIO(file_content),
                            headers=headers
                        )
                        
                        content, filenames = await get_documents([file_obj])
                        predictor = init_predictor(request)
                        out = predictor(content)
                        
                        for i, page in enumerate(out.pages):
                            lines: list[str] = []
                            for block in page.blocks:
                                for line in block.lines:
                                    line_text = " ".join(word.value for word in line.words if word.value)
                                    if line_text.strip():
                                        lines.append(line_text.strip())
                            
                            full_text = "\n".join(lines)
                            results.append(
                                DocumentTextOut(
                                    name=filenames[i] if i < len(filenames) else filename,
                                    text=full_text
                                )
                            )
                        continue
                    except Exception as ocr_error:
                        raise HTTPException(
                            status_code=400, 
                            detail=f"Failed to process {filename}: {str(e)} | OCR error: {str(ocr_error)}"
                        )
                else:
                    raise HTTPException(status_code=400, detail=f"Failed to process {filename}: {str(e)}")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to process {filename}: {str(e)}")
        
        # For other formats (PDF, images, etc.), use OCR
        try:
            from fastapi import UploadFile as FastAPIUploadFile
            from io import BytesIO
            
            headers = dict(file.headers) if file.headers else {}
            if mime_type:
                headers['content-type'] = mime_type
            
            file_obj = FastAPIUploadFile(
                filename=filename,
                file=BytesIO(file_content),
                headers=headers
            )
            
            content, filenames = await get_documents([file_obj])
            predictor = init_predictor(request)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        out = predictor(content)

        for i, page in enumerate(out.pages):
            lines: list[str] = []
            for block in page.blocks:
                for line in block.lines:
                    line_text = " ".join(word.value for word in line.words if word.value)
                    if line_text.strip():
                        lines.append(line_text.strip())
            
            full_text = "\n".join(lines)
            results.append(
                DocumentTextOut(
                    name=filenames[i] if i < len(filenames) else filename,
                    text=full_text
                )
            )

    return results
