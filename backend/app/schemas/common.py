from pydantic import BaseModel


class SuccessEnvelope(BaseModel):
    success: bool = True


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    success: bool = False
    error: ErrorDetail


class MessageResponse(BaseModel):
    success: bool = True
    message: str


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class PaginatedResponse(BaseModel):
    success: bool = True
    items: list
    meta: PageMeta
