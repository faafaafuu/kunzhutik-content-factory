from __future__ import annotations

import json
import logging
import time

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.models.character_profile import CharacterProfile
from app.providers.text_generation.base import TextGenerationProvider
from app.providers.text_generation.prompts import (
    build_scene_plan_system_prompt,
    build_scene_plan_user_prompt,
    build_system_prompt,
    build_user_prompt,
)
from app.providers.text_generation.schemas import GeneratedContent, GeneratedScenePlan
from app.providers.vision.schemas import VisionAnalysisResult

logger = logging.getLogger(__name__)

OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterTextGenerationProvider(TextGenerationProvider):
    provider_name = "openrouter-text-v1"

    def generate_content(
        self,
        analysis: VisionAnalysisResult,
        character_profile: CharacterProfile,
        platform: str,
        kind: str,
        context: dict | None = None,
    ) -> GeneratedContent:
        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is not configured")
        if not settings.openrouter_text_model:
            raise ValueError("OPENROUTER_TEXT_MODEL is not configured")

        started_at = time.perf_counter()
        response_payload = self._call_openrouter(
            analysis=analysis,
            character_profile=character_profile,
            platform=platform,
            kind=kind,
            context=context,
        )
        duration_ms = round((time.perf_counter() - started_at) * 1000)
        parsed = _parse_response_json(response_payload)

        try:
            result = GeneratedContent.model_validate(
                {
                    **parsed,
                    "platform": platform,
                    "kind": kind,
                    "raw_response": {
                        "provider": self.provider_name,
                        "model": settings.openrouter_text_model,
                        "duration_ms": duration_ms,
                        "response_id": response_payload.get("id"),
                        "parsed": parsed,
                    },
                }
            )
        except ValidationError:
            logger.exception(
                "OpenRouter text generation response validation failed",
                extra={"provider": self.provider_name, "model": settings.openrouter_text_model, "duration_ms": duration_ms},
            )
            raise

        logger.info(
            "Text generation provider completed",
            extra={"provider": self.provider_name, "model": settings.openrouter_text_model, "duration_ms": duration_ms},
        )
        return result

    def generate_scene_plan(
        self,
        draft_context: dict,
        character_prompt: str,
        style_prompt: str,
        scenes_count: int,
        total_duration_sec: int,
        context: dict | None = None,
    ) -> GeneratedScenePlan:
        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is not configured")
        if not settings.openrouter_text_model:
            raise ValueError("OPENROUTER_TEXT_MODEL is not configured")

        started_at = time.perf_counter()
        response_payload = self._chat(
            system_prompt=build_scene_plan_system_prompt(character_prompt, style_prompt),
            user_prompt=build_scene_plan_user_prompt(draft_context, scenes_count, total_duration_sec, context),
        )
        duration_ms = round((time.perf_counter() - started_at) * 1000)
        parsed = _parse_response_json(response_payload)
        scenes = _normalize_scenes(parsed, scenes_count, total_duration_sec)
        logger.info(
            "Scene plan generation completed",
            extra={"provider": self.provider_name, "model": settings.openrouter_text_model, "duration_ms": duration_ms, "scene_count": len(scenes)},
        )
        return GeneratedScenePlan(
            provider=self.provider_name,
            scenes=scenes,
            raw_response={
                "provider": self.provider_name,
                "model": settings.openrouter_text_model,
                "duration_ms": duration_ms,
                "response_id": response_payload.get("id"),
            },
        )

    def _call_openrouter(
        self,
        *,
        analysis: VisionAnalysisResult,
        character_profile: CharacterProfile,
        platform: str,
        kind: str,
        context: dict | None,
    ) -> dict:
        return self._chat(
            system_prompt=build_system_prompt(character_profile),
            user_prompt=build_user_prompt(analysis, platform, kind, context),
        )

    def _chat(self, *, system_prompt: str, user_prompt: str) -> dict:
        payload = {
            "model": settings.openrouter_text_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.app_base_url,
            "X-Title": settings.app_name,
        }
        with httpx.Client(timeout=settings.openrouter_timeout_seconds) as client:
            response = client.post(OPENROUTER_CHAT_COMPLETIONS_URL, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()


def _normalize_scenes(parsed: dict, scenes_count: int, total_duration_sec: int) -> list[dict]:
    raw_scenes = parsed.get("scenes") if isinstance(parsed, dict) else None
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise ValueError("OpenRouter scene plan response did not include a scenes list")
    default_duration = max(5, round(total_duration_sec / scenes_count))
    scenes = []
    for index, raw in enumerate(raw_scenes[:scenes_count]):
        if not isinstance(raw, dict) or not str(raw.get("visual_prompt") or "").strip():
            raise ValueError(f"Scene {index + 1} in OpenRouter response is missing visual_prompt")
        try:
            duration = int(raw.get("duration_sec") or default_duration)
        except (TypeError, ValueError):
            duration = default_duration
        scenes.append(
            {
                "scene_number": index + 1,
                "duration_sec": max(3, min(duration, 15)),
                "visual_prompt": str(raw["visual_prompt"]).strip(),
                "voice_text": str(raw.get("voice_text") or "").strip()[:240],
                "subtitle_text": str(raw.get("subtitle_text") or "").strip()[:90],
                "camera": str(raw.get("camera") or "").strip() or None,
                "emotion": str(raw.get("emotion") or "").strip() or None,
                "status": "queued",
            }
        )
    if len(scenes) < scenes_count:
        raise ValueError(f"OpenRouter returned {len(scenes)} scenes, expected {scenes_count}")
    return scenes


def _parse_response_json(response_payload: dict) -> dict:
    choices = response_payload.get("choices") or []
    if not choices:
        raise ValueError("OpenRouter response did not include choices")
    content = choices[0].get("message", {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("OpenRouter response did not include message content")
    return json.loads(_strip_json_fences(content.strip()))


def _strip_json_fences(content: str) -> str:
    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return content
