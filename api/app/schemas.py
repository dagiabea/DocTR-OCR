# Copyright (C) 2021-2025, Mindee.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://opensource.org/licenses/Apache-2.0> for full license details.

from typing import Any

from pydantic import BaseModel, Field


class KIEIn(BaseModel):
    det_arch: str = Field(default="db_resnet50", examples=["db_resnet50"])
    reco_arch: str = Field(default="crnn_vgg16_bn", examples=["crnn_vgg16_bn"])
    assume_straight_pages: bool = Field(default=True, examples=[True])
    preserve_aspect_ratio: bool = Field(default=True, examples=[True])
    detect_orientation: bool = Field(default=False, examples=[False])
    detect_language: bool = Field(default=False, examples=[False])
    symmetric_pad: bool = Field(default=True, examples=[True])
    straighten_pages: bool = Field(default=False, examples=[False])
    det_bs: int = Field(default=2, examples=[2])
    reco_bs: int = Field(default=128, examples=[128])
    disable_page_orientation: bool = Field(default=False, examples=[False])
    disable_crop_orientation: bool = Field(default=False, examples=[False])
    bin_thresh: float = Field(default=0.1, examples=[0.1])
    box_thresh: float = Field(default=0.1, examples=[0.1])


class OCRIn(KIEIn, BaseModel):
    resolve_lines: bool = Field(default=True, examples=[True])
    resolve_blocks: bool = Field(default=False, examples=[False])
    paragraph_break: float = Field(default=0.0035, examples=[0.0035])


class ResumeExtractionIn(BaseModel):
    use_ai: bool = Field(default=False, examples=[False], description="Use AI for extraction (more accurate but requires API key)")
    ai_provider: str = Field(default="openai", examples=["openai"], description="AI provider: 'openai' or 'anthropic'")
    ai_model: str | None = Field(default=None, examples=["gpt-4o-mini"], description="AI model name (optional, uses provider default)")
    ai_api_key: str | None = Field(default=None, examples=["sk-..."], description="AI API key (optional, can use environment variable)")


class RecognitionIn(BaseModel):
    reco_arch: str = Field(default="crnn_vgg16_bn", examples=["crnn_vgg16_bn"])
    reco_bs: int = Field(default=128, examples=[128])


class DetectionIn(BaseModel):
    det_arch: str = Field(default="db_resnet50", examples=["db_resnet50"])
    assume_straight_pages: bool = Field(default=True, examples=[True])
    preserve_aspect_ratio: bool = Field(default=True, examples=[True])
    symmetric_pad: bool = Field(default=True, examples=[True])
    det_bs: int = Field(default=2, examples=[2])
    bin_thresh: float = Field(default=0.1, examples=[0.1])
    box_thresh: float = Field(default=0.1, examples=[0.1])


class RecognitionOut(BaseModel):
    name: str = Field(..., examples=["example.jpg"])
    value: str = Field(..., examples=["Hello"])
    confidence: float = Field(..., examples=[0.99])


class DetectionOut(BaseModel):
    name: str = Field(..., examples=["example.jpg"])
    geometries: list[list[float]] = Field(..., examples=[[0.0, 0.0, 0.0, 0.0]])


class OCRWord(BaseModel):
    value: str = Field(..., examples=["example"])
    geometry: list[float] = Field(..., examples=[[0.0, 0.0, 0.0, 0.0]])
    objectness_score: float = Field(..., examples=[0.99])
    confidence: float = Field(..., examples=[0.99])
    crop_orientation: dict[str, Any] = Field(..., examples=[{"value": 0, "confidence": None}])


class OCRLine(BaseModel):
    geometry: list[float] = Field(..., examples=[[0.0, 0.0, 0.0, 0.0]])
    objectness_score: float = Field(..., examples=[0.99])
    words: list[OCRWord] = Field(
        ...,
        examples=[
            {
                "value": "example",
                "geometry": [0.0, 0.0, 0.0, 0.0],
                "objectness_score": 0.99,
                "confidence": 0.99,
                "crop_orientation": {"value": 0, "confidence": None},
            }
        ],
    )


class OCRBlock(BaseModel):
    geometry: list[float] = Field(..., examples=[[0.0, 0.0, 0.0, 0.0]])
    objectness_score: float = Field(..., examples=[0.99])
    lines: list[OCRLine] = Field(
        ...,
        examples=[
            {
                "geometry": [0.0, 0.0, 0.0, 0.0],
                "objectness_score": 0.99,
                "words": [
                    {
                        "value": "example",
                        "geometry": [0.0, 0.0, 0.0, 0.0],
                        "confidence": 0.99,
                        "crop_orientation": {"value": 0, "confidence": None},
                    }
                ],
            }
        ],
    )


class OCRPage(BaseModel):
    blocks: list[OCRBlock] = Field(
        ...,
        examples=[
            {
                "geometry": [0.0, 0.0, 0.0, 0.0],
                "objectness_score": 0.99,
                "lines": [
                    {
                        "geometry": [0.0, 0.0, 0.0, 0.0],
                        "objectness_score": 0.99,
                        "words": [
                            {
                                "value": "example",
                                "geometry": [0.0, 0.0, 0.0, 0.0],
                                "objectness_score": 0.99,
                                "confidence": 0.99,
                                "crop_orientation": {"value": 0, "confidence": None},
                            }
                        ],
                    }
                ],
            }
        ],
    )


class OCROut(BaseModel):
    name: str = Field(..., examples=["example.jpg"])
    orientation: dict[str, float | None] = Field(..., examples=[{"value": 0.0, "confidence": 0.99}])
    language: dict[str, str | float | None] = Field(..., examples=[{"value": "en", "confidence": 0.99}])
    dimensions: tuple[int, int] = Field(..., examples=[(100, 100)])
    items: list[OCRPage] = Field(...)


class DocumentTextOut(BaseModel):
    name: str = Field(..., examples=["example.pdf"])
    text: str = Field(..., examples=["Example extracted text"])


class KIEElement(BaseModel):
    class_name: str = Field(..., examples=["example"])
    items: list[dict[str, str | list[float] | float | dict[str, Any]]] = Field(
        ...,
        examples=[
            {
                "value": "example",
                "geometry": [0.0, 0.0, 0.0, 0.0],
                "objectness_score": 0.99,
                "confidence": 0.99,
                "crop_orientation": {"value": 0, "confidence": None},
            }
        ],
    )


class KIEOut(BaseModel):
    name: str = Field(..., examples=["example.jpg"])
    orientation: dict[str, float | None] = Field(..., examples=[{"value": 0.0, "confidence": 0.99}])
    language: dict[str, str | float | None] = Field(..., examples=[{"value": "en", "confidence": 0.99}])
    dimensions: tuple[int, int] = Field(..., examples=[(100, 100)])
    predictions: list[KIEElement]


class ResumeField(BaseModel):
    value: str | None = Field(None, examples=["John Doe"])
    confidence: float = Field(0.0, ge=0.0, le=1.0, examples=[0.95])
    is_missing: bool = Field(False, examples=[False])


class ResumeExtractionOut(BaseModel):
    name: str = Field(..., examples=["resume.pdf"])
    name_field: ResumeField = Field(..., examples=[{"value": "John Doe", "confidence": 0.9, "is_missing": False}])
    email: ResumeField = Field(..., examples=[{"value": "john@example.com", "confidence": 1.0, "is_missing": False}])
    phone: ResumeField = Field(..., examples=[{"value": "+1234567890", "confidence": 0.95, "is_missing": False}])
    skills: ResumeField = Field(..., examples=[{"value": "Python, JavaScript, React", "confidence": 0.8, "is_missing": False}])
    experience: list[ResumeField] = Field(
        default_factory=list,
        examples=[[{"value": "Software Engineer at Company X (2020-2023)", "confidence": 0.85, "is_missing": False}]]
    )
    education: ResumeField = Field(..., examples=[{"value": "BS Computer Science, University Y (2016-2020)", "confidence": 0.9, "is_missing": False}])
    raw_text: str = Field(..., examples=["Full extracted text from OCR..."])
    extraction_errors: list[str] = Field(default_factory=list, examples=[["Could not parse experience section"]])
