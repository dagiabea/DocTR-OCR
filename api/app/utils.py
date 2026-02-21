# Copyright (C) 2021-2025, Mindee.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://opensource.org/licenses/Apache-2.0> for full license details.


from typing import Any

import numpy as np
from fastapi import UploadFile

from doctr.io import DocumentFile

from app.document_converter import convert_document_to_images


def resolve_geometry(
    geom: Any,
) -> tuple[float, float, float, float] | tuple[float, float, float, float, float, float, float, float]:
    if len(geom) == 4:
        return (*geom[0], *geom[1], *geom[2], *geom[3])
    return (*geom[0], *geom[1])


async def get_documents(files: list[UploadFile]) -> tuple[list[np.ndarray], list[str]]:  # pragma: no cover
    """Convert a list of UploadFile objects to lists of numpy arrays and their corresponding filenames

    Supports:
    - Images: JPEG, PNG
    - PDF: application/pdf
    - Word Documents: DOCX (.docx), DOC (.doc) - limited support
    - Text: TXT (.txt)
    - Rich Text: RTF (.rtf)
    - OpenDocument: ODT (.odt)

    Args:
        files: list of UploadFile objects

    Returns:
        tuple[list[np.ndarray], list[str]]: list of numpy arrays and their corresponding filenames

    """
    filenames = []
    docs = []
    for file in files:
        mime_type = file.content_type or ""
        file_content = await file.read()
        filename = file.filename or ""
        
        # Handle images
        if mime_type in ["image/jpeg", "image/jpg", "image/png"]:
            docs.extend(DocumentFile.from_images([file_content]))
            filenames.append(filename)
        
        # Handle PDF
        elif mime_type == "application/pdf":
            pdf_content = DocumentFile.from_pdf(file_content)
            docs.extend(pdf_content)
            filenames.extend([filename] * len(pdf_content) if pdf_content else [filename])
        
        # Handle document formats (DOCX, DOC, TXT, RTF, ODT)
        elif mime_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
            "application/msword",  # .doc
            "text/plain",  # .txt
            "application/rtf",  # .rtf
            "application/vnd.oasis.opendocument.text",  # .odt
        ] or filename.lower().endswith(('.docx', '.doc', '.txt', '.rtf', '.odt')):
            try:
                converted_images = convert_document_to_images(file_content, mime_type, filename)
                docs.extend(converted_images)
                filenames.extend([filename] * len(converted_images) if converted_images else [filename])
            except Exception as e:
                raise ValueError(
                    f"Failed to process {filename} ({mime_type}): {str(e)}. "
                    f"Make sure required dependencies are installed. "
                    f"See error details: {str(e)}"
                )
        
        else:
            raise ValueError(
                f"Unsupported file format: {mime_type} for file {filename}. "
                f"Supported formats: PDF, JPEG, PNG, DOCX, DOC, TXT, RTF, ODT"
            )

    return docs, filenames
