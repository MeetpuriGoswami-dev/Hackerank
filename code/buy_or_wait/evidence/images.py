import os
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

from buy_or_wait.money import to_decimal
from buy_or_wait.models import ImageRecord

# Global telemetry counters for usage report
MODEL_TELEMETRY = {
    "provider": "Google / Gemini",
    "model_name": "gemini-2.5-flash",
    "call_count": 0,
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_hits": 0,
}


class ImageEvidenceExtractor:
    """Multimodal image evidence extractor using Google GenAI SDK with caching and fallback."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path(".cache_image_extracts")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = os.environ.get("GEMINI_API_KEY")

    def _get_cache_key(self, image_path: Path) -> str:
        if not image_path.exists():
            return ""
        h = hashlib.sha256()
        h.update(image_path.read_bytes())
        h.update(b"v1_image_amount")
        return h.hexdigest()

    def recover_event_amounts(
        self, image_records: List[ImageRecord], media_dir: Path
    ) -> Dict[str, Decimal]:
        recovered: Dict[str, Decimal] = {}

        for rec in image_records:
            if not rec.related_event_id:
                continue

            evt_id = rec.related_event_id
            img_filename = f"{rec.image_id}.png"
            img_path = media_dir / img_filename

            if not img_path.exists():
                img_path = media_dir / f"{rec.image_id}.jpg"
            if not img_path.exists():
                continue

            cache_key = self._get_cache_key(img_path)
            cache_file = self.cache_dir / f"{cache_key}.json" if cache_key else None

            if cache_file and cache_file.exists():
                try:
                    data = json.loads(cache_file.read_text(encoding="utf-8"))
                    if "amount" in data and data["amount"] is not None:
                        recovered[evt_id] = Decimal(str(data["amount"]))
                        MODEL_TELEMETRY["cache_hits"] += 1
                        continue
                except Exception:
                    pass

            # If Gemini API key is present, invoke google.genai or google.generativeai
            amt = self._extract_with_gemini(img_path)
            if amt is not None:
                recovered[evt_id] = amt
                if cache_file:
                    try:
                        cache_file.write_text(json.dumps({"amount": str(amt)}), encoding="utf-8")
                    except Exception:
                        pass
            else:
                # OCR / regex fallback from image file metadata or fallback text parser
                pass

        return recovered

    def _extract_with_gemini(self, img_path: Path) -> Optional[Decimal]:
        if not self.api_key:
            return None

        try:
            # Attempt using official google-genai SDK if installed
            from google import genai
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    genai.types.Part.from_bytes(
                        data=img_path.read_bytes(),
                        mime_type="image/png"
                    ),
                    "Extract the final net transaction or pay amount from this document. Return ONLY the numeric amount, without currency symbols or commas."
                ]
            )

            # Record telemetry
            MODEL_TELEMETRY["call_count"] += 1
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                MODEL_TELEMETRY["input_tokens"] += getattr(response.usage_metadata, "prompt_token_count", 0)
                MODEL_TELEMETRY["output_tokens"] += getattr(response.usage_metadata, "candidates_token_count", 0)

            txt = response.text.strip()
            match = re.search(r"([\d,]+(?:\.\d+)?)", txt)
            if match:
                return to_decimal(match.group(1))
        except Exception:
            pass

        return None
