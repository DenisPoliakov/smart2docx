"""HTTP-интерфейс модуля smart2docx."""

from __future__ import annotations

import json
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError

from smart2docx import __version__
from smart2docx.builder.docx_builder import DOCX_MEDIA_TYPE
from smart2docx.errors import DocumentParseError, Smart2DocxError, TemplateNotFoundError
from smart2docx.parsers import parse_document
from smart2docx.schemas.generation import GenerationOptions, GenerationRequest
from smart2docx.schemas.smart_document import SmartDocument
from smart2docx.semantic.mock_provider import MockSemanticProvider
from smart2docx.semantic.provider import SemanticModelProvider
from smart2docx.service import GeneratedDocument, generate_document
from smart2docx.templates.registry import TemplateRegistry

MAX_UPLOAD_BYTES = 5 * 1024 * 1024

_TRUE_VALUES = {"1", "true", "yes", "да"}
_FALSE_VALUES = {"0", "false", "no", "нет"}


def create_app(
    provider: SemanticModelProvider | None = None,
    registry: TemplateRegistry | None = None,
) -> FastAPI:
    """Создаёт приложение FastAPI.

    Поставщик текста и реестр шаблонов можно подменить в тестах
    и при встраивании модуля.
    """
    app = FastAPI(
        title="smart2docx",
        version=__version__,
        summary="Формирование документов DOCX по ГОСТ на основе smart-документов",
    )
    app.state.provider = provider or MockSemanticProvider()
    app.state.registry = registry or TemplateRegistry()

    @app.exception_handler(TemplateNotFoundError)
    async def _template_not_found(_request: Request, exc: TemplateNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(DocumentParseError)
    async def _parse_error(_request: Request, exc: DocumentParseError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.get("/health")
    def health() -> dict[str, str]:
        """Проверка доступности модуля."""
        return {"status": "ok", "service": "smart2docx", "version": __version__}

    @app.get("/api/v1/templates")
    def list_templates() -> list[dict[str, object]]:
        """Возвращает зарегистрированные профили шаблонов ГОСТ."""
        profiles = app.state.registry.list()
        return [
            {
                "id": profile.id,
                "title": profile.title,
                "document_kind": profile.document_kind,
                "summary": profile.summary,
                "normative_basis": list(profile.normative_basis),
                "sections": [slot.title for slot in profile.sections],
            }
            for profile in profiles
        ]

    @app.post("/api/v1/generate")
    async def generate(request: Request) -> Response:
        """Формирует файл DOCX.

        JSON (`Content-Type: application/json`):
        объект `{ "template_id", "document", "options" }` либо сам smart-документ.
        Во втором случае `template_id` передаётся параметром запроса.

        Multipart (`multipart/form-data`):
        поле `template_id`, поле `file` с JSON или XML и необязательное поле
        `include_title_page` (`true` или `false`).
        """
        media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if media_type == "application/json":
            generated = await _from_json(request)
        elif media_type == "multipart/form-data":
            generated = await _from_multipart(request)
        else:
            raise HTTPException(
                status_code=415,
                detail="Ожидается application/json или multipart/form-data.",
            )
        return Response(
            content=generated.content,
            media_type=DOCX_MEDIA_TYPE,
            headers={"Content-Disposition": content_disposition(generated.filename)},
        )

    return app


app = create_app()


def run() -> None:
    """Запускает HTTP-сервис на локальном интерфейсе."""
    import uvicorn

    uvicorn.run("smart2docx.main:app", host="127.0.0.1", port=8000)


async def _from_json(request: Request) -> GeneratedDocument:
    raw = await request.body()
    if not raw:
        raise HTTPException(status_code=422, detail="Тело запроса пустое.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Тело запроса превышает допустимый размер.")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"JSON не разобран: {exc.msg}.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="JSON должен быть объектом.")
    if "document" in payload:
        try:
            model = GenerationRequest.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=_validation_detail(exc)) from exc
        return _generate(request, model.document, model.template_id, model.options)
    template_id = request.query_params.get("template_id", "").strip()
    if not template_id:
        raise HTTPException(
            status_code=422,
            detail="Укажите template_id в теле запроса или в параметре запроса.",
        )
    try:
        document = SmartDocument.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_validation_detail(exc)) from exc
    options = GenerationOptions(include_title_page=_flag(request.query_params.get("include_title_page"), True))
    return _generate(request, document, template_id, options)


async def _from_multipart(request: Request) -> GeneratedDocument:
    form = await request.form()
    template_id = form.get("template_id")
    if not isinstance(template_id, str) or not template_id.strip():
        raise HTTPException(status_code=422, detail="Поле template_id обязательно.")
    upload = form.get("file")
    if upload is None or not hasattr(upload, "read"):
        raise HTTPException(status_code=422, detail="Поле file должно содержать JSON или XML.")
    raw = await upload.read()
    if not raw:
        raise HTTPException(status_code=422, detail="Файл smart-документа пуст.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Файл превышает допустимый размер.")
    filename = getattr(upload, "filename", None)
    content_type = getattr(upload, "content_type", None)
    try:
        document = parse_document(raw, filename=filename, content_type=content_type)
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="Файл должен быть в кодировке UTF-8.") from exc
    include_title_page = _flag(form.get("include_title_page"), True)
    return _generate(
        request,
        document,
        template_id.strip(),
        GenerationOptions(include_title_page=include_title_page),
    )


def _generate(
    request: Request,
    document: SmartDocument,
    template_id: str,
    options: GenerationOptions,
) -> GeneratedDocument:
    try:
        return generate_document(
            document,
            template_id,
            provider=request.app.state.provider,
            registry=request.app.state.registry,
            options=options,
        )
    except TemplateNotFoundError:
        raise
    except Smart2DocxError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _flag(value: object, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, str):
        raise HTTPException(status_code=422, detail="Поле include_title_page должно быть строкой.")
    normalized = value.strip().lower()
    if not normalized:
        return default
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise HTTPException(
        status_code=422,
        detail="Поле include_title_page принимает значения true или false.",
    )


def _validation_detail(exc: ValidationError) -> list[dict[str, str]]:
    return [
        {
            "loc": ".".join(str(item) for item in error["loc"]) or "<корень>",
            "msg": str(error["msg"]),
        }
        for error in exc.errors()
    ]


def content_disposition(filename: str) -> str:
    """Формирует заголовок Content-Disposition с ASCII-именем и UTF-8-именем."""
    try:
        filename.encode("ascii")
        ascii_name = filename.replace("\\", "").replace('"', "")
    except UnicodeEncodeError:
        ascii_name = "document.docx"
    encoded = quote(filename)
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded}"
