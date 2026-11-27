// Locale switcher refs:
// - Paraglide docs: https://inlang.com/m/gerre34r/library-inlang-paraglideJs
// - Router example: https://github.com/TanStack/router/tree/main/examples/react/i18n-paraglide#switching-locale
import { getLocale, locales, setLocale } from '#/paraglide/runtime'
import { m } from '#/paraglide/messages'
import { ToggleGroup, ToggleGroupItem } from '#/components/ui/toggle-group'

const ParaglideLocaleSwitcher = () => {
  const currentLocale = getLocale()

  return (
    <div className="flex items-center gap-2" aria-label={m.language_label()}>
      <span className="text-sm opacity-85">
        {m.current_locale({ locale: currentLocale })}
      </span>
      <ToggleGroup
        type="single"
        value={currentLocale}
        onValueChange={(value) => {
          if (value === 'en' || value === 'de') setLocale(value)
        }}
        variant="outline"
        size="default"
        aria-label={m.language_label()}
      >
        {locales.map((locale) => (
          <ToggleGroupItem
            key={locale}
            value={locale}
            aria-label={locale}
            className="min-h-11 min-w-11"
          >
            {locale.toUpperCase()}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </div>
  )
}

export default ParaglideLocaleSwitcher
