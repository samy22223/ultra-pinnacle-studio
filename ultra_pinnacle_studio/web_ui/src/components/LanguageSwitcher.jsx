import React, { useEffect } from 'react'
import { useTranslation } from 'react-i18next'

const LanguageSwitcher = () => {
  const { i18n, t } = useTranslation('common')
  const languages = ['en', 'es', 'fr', 'de', 'ar', 'zh']
  const rtlLanguages = ['ar']

  const handleLanguageChange = (language) => {
    i18n.changeLanguage(language)
    localStorage.setItem('i18nextLng', language)

    // Set document direction for RTL languages
    const isRTL = rtlLanguages.includes(language)
    document.documentElement.dir = isRTL ? 'rtl' : 'ltr'
    document.documentElement.lang = language
  }

  // Set initial direction on mount
  useEffect(() => {
    const currentLang = i18n.language
    const isRTL = rtlLanguages.includes(currentLang)
    document.documentElement.dir = isRTL ? 'rtl' : 'ltr'
    document.documentElement.lang = currentLang
  }, [i18n.language])

  return (
    <div className="language-switcher">
      <select
        value={i18n.language}
        onChange={(e) => handleLanguageChange(e.target.value)}
        className="language-select"
      >
        {languages.map(lang => (
          <option key={lang} value={lang}>
            {t(`languages.${lang}`)}
          </option>
        ))}
      </select>
    </div>
  )
}

export default LanguageSwitcher