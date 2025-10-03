from typing import Optional, Dict, Any, List
import logging
from .models_safe import ModelManager
from .database import get_db
from sqlalchemy.orm import Session
from .logging_config import logger

class TranslationService:
    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        self.logger = logging.getLogger(__name__)

    async def translate_content(
        self,
        content: str,
        from_lang: str,
        to_lang: str,
        content_type: str = "general"
    ) -> str:
        """
        Translate content from one language to another using AI.

        Args:
            content: The content to translate
            from_lang: Source language code (e.g., 'en', 'es')
            to_lang: Target language code (e.g., 'fr', 'de')
            content_type: Type of content (affects translation style)

        Returns:
            Translated content
        """
        try:
            # Get language names for better prompts
            lang_names = {
                'en': 'English',
                'es': 'Spanish',
                'fr': 'French',
                'de': 'German',
                'ar': 'Arabic',
                'zh': 'Chinese'
            }

            from_lang_name = lang_names.get(from_lang, from_lang)
            to_lang_name = lang_names.get(to_lang, to_lang)

            # Create translation prompt based on content type
            if content_type == "ui":
                prompt = f"Translate this UI text from {from_lang_name} to {to_lang_name}. Maintain the same tone and keep it concise:\n\n{content}"
            elif content_type == "technical":
                prompt = f"Translate this technical content from {from_lang_name} to {to_lang_name}. Preserve technical terms and accuracy:\n\n{content}"
            elif content_type == "creative":
                prompt = f"Translate this creative content from {from_lang_name} to {to_lang_name}. Maintain the artistic style and tone:\n\n{content}"
            else:
                prompt = f"Translate this text from {from_lang_name} to {to_lang_name}:\n\n{content}"

            # Use AI model for translation
            translated = self.model_manager.generate_text(
                model_name="gpt-4",  # Prefer GPT-4 for translation quality
                prompt=prompt,
                max_tokens=len(content.split()) * 2,  # Estimate token count
                temperature=0.3  # Lower temperature for more accurate translation
            )

            self.logger.info(f"Translated content from {from_lang} to {to_lang}")
            return translated.strip()

        except Exception as e:
            self.logger.error(f"Error translating content: {e}")
            # Fallback: return original content with a note
            return f"[Translation failed] {content}"

    async def detect_language(self, content: str) -> str:
        """
        Detect the language of the given content.

        Args:
            content: The content to analyze

        Returns:
            Language code (e.g., 'en', 'es', 'fr')
        """
        try:
            prompt = f"""Detect the language of this text and return only the ISO language code (e.g., 'en', 'es', 'fr', 'de', 'ar', 'zh'):

Text: {content[:500]}...

Language code:"""

            detected_lang = self.model_manager.generate_text(
                model_name="gpt-4",
                prompt=prompt,
                max_tokens=10,
                temperature=0.1
            ).strip().lower()

            # Validate the detected language
            supported_langs = ['en', 'es', 'fr', 'de', 'ar', 'zh']
            if detected_lang in supported_langs:
                return detected_lang
            else:
                # Default to English if detection fails
                self.logger.warning(f"Unsupported language detected: {detected_lang}, defaulting to 'en'")
                return 'en'

        except Exception as e:
            self.logger.error(f"Error detecting language: {e}")
            return 'en'  # Default fallback

    async def suggest_translations(
        self,
        content: str,
        source_lang: str,
        target_langs: List[str],
        content_type: str = "general"
    ) -> Dict[str, str]:
        """
        Generate translation suggestions for multiple target languages.

        Args:
            content: Original content
            source_lang: Source language code
            target_langs: List of target language codes
            content_type: Type of content

        Returns:
            Dictionary mapping language codes to translated content
        """
        suggestions = {}

        for target_lang in target_langs:
            if target_lang != source_lang:  # Don't translate to same language
                translated = await self.translate_content(
                    content, source_lang, target_lang, content_type
                )
                suggestions[target_lang] = translated

        return suggestions

    async def validate_translation_quality(
        self,
        original: str,
        translated: str,
        source_lang: str,
        target_lang: str
    ) -> Dict[str, Any]:
        """
        Validate the quality of a translation using AI.

        Args:
            original: Original content
            translated: Translated content
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            Quality assessment with score and feedback
        """
        try:
            prompt = f"""Evaluate the quality of this translation from {source_lang} to {target_lang}.

Original: {original}

Translation: {translated}

Rate the translation quality on a scale of 1-10 and provide brief feedback.
Format: Score: X/10
Feedback: [your feedback]"""

            assessment = self.model_manager.generate_text(
                model_name="gpt-4",
                prompt=prompt,
                max_tokens=200,
                temperature=0.2
            )

            # Parse the assessment
            lines = assessment.strip().split('\n')
            score = 5  # Default
            feedback = assessment

            for line in lines:
                if line.startswith('Score:'):
                    try:
                        score_text = line.split('/')[0].replace('Score:', '').strip()
                        score = int(score_text)
                    except:
                        pass
                elif line.startswith('Feedback:'):
                    feedback = line.replace('Feedback:', '').strip()

            return {
                "score": min(max(score, 1), 10),  # Ensure score is between 1-10
                "feedback": feedback,
                "assessment": assessment
            }

        except Exception as e:
            self.logger.error(f"Error validating translation quality: {e}")
            return {
                "score": 5,
                "feedback": "Quality assessment failed",
                "assessment": str(e)
            }

# Global translation service instance
translation_service = None

def get_translation_service(model_manager: ModelManager) -> TranslationService:
    """Get or create the global translation service instance."""
    global translation_service
    if translation_service is None:
        translation_service = TranslationService(model_manager)
    return translation_service