import { clsx } from 'clsx'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  ArcElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  CategoryScale as CategoryScaleChart,
} from 'chart.js'
import { Bar, Line, Doughnut, Pie } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  ArcElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const defaultOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
    },
    tooltip: {
      backgroundColor: '#1e293b',
      titleColor: '#ffffff',
      bodyColor: '#ffffff',
      padding: 12,
      cornerRadius: 8,
      displayColors: false,
    },
  },
  interaction: {
    intersect: false,
    mode: 'index',
  },
}

export function ChartCard({
  title,
  subtitle,
  children,
  className = '',
  action,
  loading = false,
  error = null,
}) {
  return (
    <div className={clsx('card', className)}>
      <div className="card-header">
        <div>
          <h3 className="card-title">{title}</h3>
          {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
        </div>
        {action && <div>{action}</div>}
      </div>
      <div className="card-content">
        {loading && (
          <div className="flex items-center justify-center h-64">
            <span className="loading-spinner loading-spinner-lg" />
          </div>
        )}
        {error && (
          <div className="flex items-center justify-center h-64 text-center text-gray-500">
            <p>{error}</p>
          </div>
        )}
        {!loading && !error && children}
      </div>
    </div>
  )
}

export function BarChart({ data, options = {}, height = 300, className = '' }) {
  const chartOptions = {
    ...defaultOptions,
    ...options,
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: '#94a3b8', font: { size: 11 } },
      },
      y: {
        grid: { color: '#e2e8f0' },
        ticks: { color: '#94a3b8', font: { size: 11 } },
        beginAtZero: true,
      },
      ...options.scales,
    },
  }

  return (
    <div style={{ height }} className={className}>
      <Bar data={data} options={chartOptions} />
    </div>
  )
}

export function LineChart({ data, options = {}, height = 300, className = '' }) {
  const chartOptions = {
    ...defaultOptions,
    ...options,
    elements: {
      line: { tension: 0.4 },
      point: { radius: 0, hoverRadius: 6 },
      ...options.elements,
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: '#94a3b8', font: { size: 11 } },
      },
      y: {
        grid: { color: '#e2e8f0' },
        ticks: { color: '#94a3b8', font: { size: 11 } },
      },
      ...options.scales,
    },
  }

  return (
    <div style={{ height }} className={className}>
      <Line data={data} options={chartOptions} />
    </div>
  )
}

export function AreaChart({ data, options = {}, height = 300, className = '' }) {
  const chartOptions = {
    ...defaultOptions,
    ...options,
    elements: {
      line: { tension: 0.4 },
      point: { radius: 0, hoverRadius: 6 },
      ...options.elements,
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: '#94a3b8', font: { size: 11 } },
      },
      y: {
        grid: { color: '#e2e8f0' },
        ticks: { color: '#94a3b8', font: { size: 11 } },
      },
      ...options.scales,
    },
  }

  const filledData = {
    ...data,
    datasets: data.datasets.map((ds) => ({
      ...ds,
      fill: true,
      backgroundColor: ds.backgroundColor || ds.borderColor?.replace(')', ', 0.1)').replace('rgb', 'rgba').replace(')', ', 0.1)'),
    })),
  }

  return (
    <div style={{ height }} className={className}>
      <Line data={filledData} options={chartOptions} />
    </div>
  )
}

export function DoughnutChart({ data, options = {}, height = 300, className = '' }) {
  const chartOptions = {
    ...defaultOptions,
    ...options,
    cutout: '70%',
    plugins: {
      ...defaultOptions.plugins,
      legend: {
        position: 'bottom',
        labels: {
          usePointStyle: true,
          padding: 16,
          font: { size: 12 },
          color: '#475569',
        },
      },
      ...options.plugins,
    },
  }

  return (
    <div style={{ height }} className={className}>
      <Doughnut data={data} options={chartOptions} />
    </div>
  )
}

export function PieChart({ data, options = {}, height = 300, className = '' }) {
  const chartOptions = {
    ...defaultOptions,
    ...options,
    plugins: {
      ...defaultOptions.plugins,
      legend: {
        position: 'bottom',
        labels: {
          usePointStyle: true,
          padding: 16,
          font: { size: 12 },
          color: '#475569',
        },
      },
      ...options.plugins,
    },
  }

  return (
    <div style={{ height }} className={className}>
      <Pie data={data} options={chartOptions} />
    </div>
  )
}

export function MetricChart({ value, label, trend, trendLabel, className = '' }) {
  const isPositive = trend && !trend.startsWith('-')

  return (
    <div className={clsx('p-4', className)}>
      <div className="flex items-baseline justify-between gap-2">
        <div>
          <p className="text-3xl font-bold text-gray-900">{value}</p>
          <p className="text-sm text-gray-500 mt-1">{label}</p>
        </div>
        {trend && (
          <div className={clsx('flex items-center gap-1 text-sm font-medium', isPositive ? 'text-green-600' : 'text-red-600')}>
            <span aria-hidden="true">{isPositive ? '↑' : '↓'}</span>
            <span>{trend}</span>
            {trendLabel && <span className="text-gray-500">{trendLabel}</span>}
          </div>
        )}
      </div>
    </div>
  )
}

export default {
  ChartCard,
  BarChart,
  LineChart,
  AreaChart,
  DoughnutChart,
  PieChart,
  MetricChart,
}