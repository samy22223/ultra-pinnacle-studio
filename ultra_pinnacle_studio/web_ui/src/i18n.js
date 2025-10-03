import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import Backend from 'i18next-http-backend';

i18n
  .use(Backend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'en',
    debug: process.env.NODE_ENV === 'development',

    interpolation: {
      escapeValue: false, // React already escapes values
    },

    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
    },

    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
    },

    // ICU message format support
    i18nFormat: {
      localeData: null,
      formats: {},
      pluralResolver: null,
      ordinalPluralResolver: null,
    },

    // Supported languages
    supportedLngs: ['en', 'es', 'fr', 'de', 'ar', 'zh'],

    // Fallback languages
    fallbackLng: {
      'en-US': ['en'],
      'zh-CN': ['zh'],
      'zh-TW': ['zh'],
      'pt-BR': ['pt'],
      'default': ['en']
    },

    // React options
    react: {
      useSuspense: false,
    },

    // Missing key handler
    saveMissing: true,
    missingKeyHandler: (lngs, namespace, key, fallbackValue) => {
      // Report missing translations to backend
      if (process.env.NODE_ENV === 'development') {
        console.warn(`Missing translation: ${namespace}:${key} for languages: ${lngs.join(', ')}`);
      }

      // Send to backend for tracking
      fetch('/api/translations/missing', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ lngs, namespace, key }),
      }).catch(err => console.error('Failed to report missing translation:', err));
    },
  });

export default i18n;