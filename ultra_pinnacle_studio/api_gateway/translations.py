import gettext
import os
from typing import Optional
from pathlib import Path

# Translation domain
DOMAIN = 'ultra_pinnacle'

# Get the directory where this file is located
BASE_DIR = Path(__file__).parent
LOCALE_DIR = BASE_DIR / 'locale'

def setup_translations(language: str = 'en') -> None:
    """Setup translations for the given language"""
    try:
        # Set the LANGUAGE environment variable
        os.environ['LANGUAGE'] = language

        # Bind the text domain
        gettext.bindtextdomain(DOMAIN, str(LOCALE_DIR))
        gettext.textdomain(DOMAIN)

        # Install the translation
        trans = gettext.translation(DOMAIN, str(LOCALE_DIR), languages=[language], fallback=True)
        trans.install()

    except Exception as e:
        # Fallback to default if translation fails
        print(f"Warning: Could not load translations for {language}: {e}")
        gettext.install(DOMAIN)

def get_translator(language: str = 'en'):
    """Get a translator object for the given language"""
    try:
        return gettext.translation(DOMAIN, str(LOCALE_DIR), languages=[language], fallback=True)
    except Exception:
        return None

def _(message: str) -> str:
    """Translate a message"""
    return gettext.gettext(message)

def ngettext(singular: str, plural: str, n: int) -> str:
    """Translate a plural message"""
    return gettext.ngettext(singular, plural, n)

# Initialize with default language
setup_translations('en')