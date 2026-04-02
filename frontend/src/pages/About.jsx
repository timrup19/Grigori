import { Shield, Database, GitBranch, AlertTriangle, Code2, ExternalLink } from 'lucide-react'

const FEATURES = [
  {
    icon: Shield,
    title: 'Оцінка ризиків',
    desc: 'Комплексна модель на основі IsolationForest та Z-score для виявлення цінових аномалій, аналізу ставок та показників однобідерних торгів.',
  },
  {
    icon: GitBranch,
    title: 'Аналіз мережі',
    desc: 'Граф спільних торгів на основі NetworkX. Виявлення підозрілих кластерів підрядників, які систематично конкурують або уникають конкуренції.',
  },
  {
    icon: AlertTriangle,
    title: 'Автоматичні сповіщення',
    desc: 'Ризикові сигнали генеруються автоматично при синхронізації даних з Prozorro API: однобідерні торги, цінові аномалії, повторні переможці.',
  },
  {
    icon: Database,
    title: 'Дані Prozorro',
    desc: 'Всі дані отримуються з відкритого API Prozorro — офіційної системи електронних публічних закупівель України.',
  },
]

const TECH_STACK = [
  { category: 'Backend', items: ['FastAPI', 'SQLAlchemy 2.0', 'PostgreSQL', 'asyncpg', 'Alembic'] },
  { category: 'Аналіз', items: ['scikit-learn', 'NetworkX', 'pandas', 'numpy'] },
  { category: 'Frontend', items: ['React 18', 'TailwindCSS', 'Recharts', 'vis-network', 'react-simple-maps'] },
]

export default function About() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {/* Hero */}
      <div className="text-center mb-12">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-sentinel-600 rounded-2xl mb-4">
          <Shield className="w-9 h-9 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-3">Grigori</h1>
        <p className="text-gray-600 max-w-xl mx-auto">
          Відкрита платформа аналізу ризиків держзакупівель України. Допомагає журналістам,
          дослідникам та громадянському суспільству виявляти потенційні порушення у системі Prozorro.
        </p>
      </div>

      {/* Features */}
      <div className="grid sm:grid-cols-2 gap-5 mb-12">
        {FEATURES.map(({ icon: Icon, title, desc }) => (
          <div key={title} className="bg-white rounded-lg border border-gray-200 p-5">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-sentinel-50 rounded-lg">
                <Icon className="w-5 h-5 text-sentinel-600" />
              </div>
              <h3 className="font-semibold text-gray-800">{title}</h3>
            </div>
            <p className="text-sm text-gray-600">{desc}</p>
          </div>
        ))}
      </div>

      {/* Methodology */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Методологія оцінки ризику</h2>
        <div className="space-y-3">
          {[
            { label: 'Цінова аномалія (0–40 балів)', desc: 'IsolationForest по CPV-категорії + Z-score відносно медіани по регіону' },
            { label: 'Конкуренція (0–30 балів)', desc: 'Кількість учасників торгів, частка однобідерних тендерів, стандартне відхилення ставок' },
            { label: 'Мережа (0–20 балів)', desc: 'Централізованість у графі спільних торгів, участь у підозрілих кластерах' },
            { label: 'Переможність (0–10 балів)', desc: 'Концентрація перемог у одного замовника, динаміка виграшів' },
          ].map(({ label, desc }) => (
            <div key={label} className="flex gap-3">
              <span className="w-2 h-2 rounded-full bg-sentinel-500 flex-shrink-0 mt-1.5" />
              <div>
                <p className="text-sm font-medium text-gray-800">{label}</p>
                <p className="text-xs text-gray-500">{desc}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
          <strong>Застереження:</strong> Високий рівень ризику не означає факту корупції. Система виявляє
          статистичні аномалії, які потребують подальшого розслідування.
        </div>
      </div>

      {/* Tech stack */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-8">
        <div className="flex items-center gap-2 mb-4">
          <Code2 className="w-5 h-5 text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-800">Технічний стек</h2>
        </div>
        <div className="grid sm:grid-cols-3 gap-4">
          {TECH_STACK.map(({ category, items }) => (
            <div key={category}>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{category}</p>
              <ul className="space-y-1">
                {items.map(item => (
                  <li key={item} className="text-sm text-gray-600 flex items-center gap-1.5">
                    <span className="w-1 h-1 rounded-full bg-sentinel-400" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* Data source */}
      <div className="text-center text-sm text-gray-500">
        <p className="mb-2">Дані надаються відкритим API</p>
        <a
          href="https://prozorro.gov.ua"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sentinel-600 hover:underline font-medium"
        >
          prozorro.gov.ua <ExternalLink className="w-3.5 h-3.5" />
        </a>
        <p className="mt-4 text-xs text-gray-400">
          Grigori — відкрите програмне забезпечення. Дані оновлюються щодня.
        </p>
      </div>
    </div>
  )
}
