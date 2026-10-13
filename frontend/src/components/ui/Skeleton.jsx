import { clsx } from 'clsx'

export function Skeleton({ className = '', variant = 'text', width, height, ...props }) {
  const baseStyles = 'animate-pulse bg-gray-200 rounded'
  
  return (
    <div
      className={clsx(baseStyles, className)}
      style={{
        width: width || (variant === 'circular' ? height : undefined),
        height: height || (variant === 'circular' ? width : undefined),
        borderRadius: variant === 'circular' ? '50%' : '0.375rem',
      }}
      {...props}
    />
  )
}

export function SkeletonText({ lines = 3, className = '', ...props }) {
  return (
    <div className={clsx('space-y-2', className)} {...props}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} variant="text" width={{ 0: '100%', 1: '80%', 2: '60%' }[i] || '100%' } height="1rem" />
      ))}
    </div>
  )
}

export function SkeletonCard({ className = '', variant = 'default', ...props }) {
  const variants = {
    default: (
      <div className={clsx('card p-6', className)} {...props}>
        <Skeleton variant="text" width="3/4" height="1rem" className="mb-2" />
        <Skeleton variant="text" width="1/2" height="1.5rem" className="mb-4" />
        <Skeleton variant="text" width="full" height="1rem" className="mb-2" />
        <Skeleton variant="text" width="3/4" height="1rem" />
      </div>
    ),
    metric: (
      <div className={clsx('card p-6', className)} {...props}>
        <Skeleton variant="text" width="3/4" height="0.875rem" className="mb-2" />
        <Skeleton variant="text" width="1/2" height="2rem" className="mb-2" />
        <Skeleton variant="text" width="1/3" height="0.875rem" />
      </div>
    ),
    chart: (
      <div className={clsx('card', className)} {...props}>
        <div className="card-header p-4">
          <Skeleton variant="text" width="1/2" height="1rem" className="mb-1" />
          <Skeleton variant="text" width="3/4" height="0.875rem" />
        </div>
        <div className="card-content p-4">
          <Skeleton variant="rectangular" width="full" height="300" />
        </div>
      </div>
    ),
    tableRow: (
      <div className={clsx('flex items-center gap-4 p-4', className)} {...props}>
        <Skeleton variant="text" width="2rem" height="1rem" />
        <Skeleton variant="text" width="4rem" height="1rem" className="flex-1" />
        <Skeleton variant="text" width="2rem" height="1rem" />
        <Skeleton variant="text" width="3rem" height="1rem" />
        <Skeleton variant="text" width="2rem" height="1rem" />
      </div>
    ),
    listItem: (
      <div className={clsx('flex items-start gap-4 p-4', className)} {...props}>
        <Skeleton variant="circular" width="48" height="48" className="flex-shrink-0" />
        <div className="flex-1 min-w-0 space-y-2">
          <Skeleton variant="text" width="1/3" height="1rem" />
          <Skeleton variant="text" width="1/2" height="0.875rem" />
          <Skeleton variant="text" width="2/3" height="0.75rem" />
        </div>
      </div>
    ),
  }

  return variants[variant] || variants.default
}

export function DashboardSkeleton({ metricCount = 4, chartCount = 3, tableRows = 5 }) {
  return (
    <div className="page animate-pulse">
      <div className="mb-8">
        <Skeleton variant="text" width="1/3" height="1.5rem" className="mb-1" />
        <Skeleton variant="text" width="1/2" height="1rem" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {Array.from({ length: metricCount }).map((_, i) => (
          <SkeletonCard key={i} variant="metric" />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <SkeletonCard variant="chart" />
        <div className="grid grid-cols-1 gap-6">
          <SkeletonCard variant="chart" className="h-[calc(300px+2rem)]" />
          <SkeletonCard variant="chart" className="h-[calc(300px+2rem)]" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2">
          <div className="card">
            <div className="card-header p-4">
              <Skeleton variant="text" width="1/3" height="1rem" className="mb-1" />
              <Skeleton variant="text" width="1/2" height="0.875rem" />
            </div>
            <div className="card-content p-0">
              <div className="divide-y divide-gray-200">
                {Array.from({ length: tableRows }).map((_, i) => (
                  <SkeletonCard key={i} variant="tableRow" className="m-0" />
                ))}
              </div>
            </div>
          </div>
        </div>
        <div>
          <div className="card">
            <div className="card-header p-4">
              <Skeleton variant="text" width="1/3" height="1rem" className="mb-1" />
              <Skeleton variant="text" width="1/2" height="0.875rem" />
            </div>
            <div className="card-content p-0">
              <div className="divide-y divide-gray-200">
                {Array.from({ length: 5 }).map((_, i) => (
                  <SkeletonCard key={i} variant="listItem" className="m-0" />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="card p-6 animate-pulse">
            <Skeleton variant="circular" width="56" height="56" className="mx-auto mb-4" />
            <Skeleton variant="text" width="1/2" height="1rem" className="mx-auto" />
          </div>
        ))}
      </div>
    </div>
  )
}

export function ChartSkeleton({ height = 300, className = '' }) {
  return (
    <div className={clsx('card', className)}>
      <div className="card-header p-4">
        <Skeleton variant="text" width="1/3" height="1rem" className="mb-1" />
        <Skeleton variant="text" width="1/2" height="0.875rem" />
      </div>
      <div className="card-content p-4">
        <Skeleton variant="rectangular" width="full" height={height} />
      </div>
    </div>
  )
}

export function TableSkeleton({ columns = 6, rows = 5, className = '' }) {
  return (
    <div className={clsx('card', className)}>
      <div className="card-header p-4">
        <Skeleton variant="text" width="1/3" height="1rem" />
      </div>
      <div className="card-content p-0">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                {Array.from({ length: columns }).map((_, i) => (
                  <th key={i} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <Skeleton variant="text" width="80%" height="0.75rem" />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {Array.from({ length: rows }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: columns }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <Skeleton variant="text" width="80%" height="1rem" />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default Skeleton