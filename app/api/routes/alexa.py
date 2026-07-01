"""Alexa webhook routes."""

from fastapi import APIRouter, Depends, Request

from app.clients.openai_client import AIClient, get_ai_client
from app.models.alexa import AlexaRequestEnvelope, AlexaResponseEnvelope
from app.services.conversation_service import ConversationService
from app.services.memory_service import ConversationMemory, get_memory_provider
from app.services.tool_service import ToolRegistry, get_tool_registry
from app.validators.alexa import AlexaRequestValidator, get_alexa_request_validator

router = APIRouter(prefix="/alexa", tags=["alexa"])


@router.post("/webhook", response_model=AlexaResponseEnvelope)
async def alexa_webhook(
    envelope: AlexaRequestEnvelope,
    request: Request,
    validator: AlexaRequestValidator = Depends(get_alexa_request_validator),
    memory: ConversationMemory = Depends(get_memory_provider),
    ai_client: AIClient = Depends(get_ai_client),
    tool_registry: ToolRegistry = Depends(get_tool_registry),
) -> AlexaResponseEnvelope:
    """Validate and process Alexa skill requests."""
    await validator.validate(request, envelope)
    service = ConversationService(
        memory=memory,
        ai_client=ai_client,
        tool_registry=tool_registry,
        base_url=str(request.base_url)
    )
    return await service.handle_alexa_request(envelope)
