import { clsx } from 'clsx'
import { forwardRef } from 'react'

export const Table = forwardRef(function Table({
  children,
  className = '',
  hover = true,
  striped = false,
  bordered = true,
  compact = false,
  ...props
}, ref) {
  return (
    <div className="table-container" role="region" aria-label="Data table" tabIndex={0}>
      <table
        ref={ref}
        className={clsx('table', hover && 'hover:shadow-none', className)}
        {...props}
      >
        {children}
      </table>
    </div>
  )
})

Table.displayName = 'Table'

export function TableHeader({ children, className = '', ...props }) {
  return (
    <thead className={clsx(className)} {...props}>
      {children}
    </thead>
  )
}

export function TableBody({ children, className = '', ...props }) {
  return (
    <tbody className={clsx('divide-y divide-gray-200', className)} {...props}>
      {children}
    </tbody>
  )
}

export function TableRow({ children, className = '', selected = false, clickable = false, ...props }) {
  return (
    <tr
      className={clsx(
        selected && 'bg-primary/5',
        clickable && 'cursor-pointer hover:bg-gray-50',
        className
      )}
      {...props}
    >
      {children}
    </tr>
  )
}

export function TableHead({ children, className = '', width, align = 'left', ...props }) {
  return (
    <th
      className={clsx(
        'px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider',
        align === 'center' && 'text-center',
        align === 'right' && 'text-right',
        className
      )}
      style={width ? { width } : undefined}
      {...props}
    >
      {children}
    </th>
  )
}

export function TableCell({ children, className = '', align = 'left', ...props }) {
  return (
    <td
      className={clsx(
        'px-4 py-3 text-sm text-gray-900',
        align === 'center' && 'text-center',
        align === 'right' && 'text-right',
        className
      )}
      {...props}
    >
      {children}
    </td>
  )
}

export function TablePagination({
  currentPage,
  totalPages,
  onPageChange,
  pageSize,
  totalItems,
  onPageSizeChange,
  pageSizeOptions = [10, 25, 50, 100],
  className = '',
}) {
  if (totalPages <= 1) return null

  const startItem = (currentPage - 1) * pageSize + 1
  const endItem = Math.min(currentPage * pageSize, totalItems)

  return (
    <div className={clsx('flex flex-col sm:flex-row items-center justify-between gap-4 p-4 border-t border-gray-200', className)}>
      <div className="text-sm text-gray-700">
        Showing <span className="font-medium">{startItem}</span> to{' '}
        <span className="font-medium">{endItem}</span> of{' '}
        <span className="font-medium">{totalItems}</span> results
      </div>
      <div className="flex items-center gap-4">
        <select
          value={pageSize}
          onChange={(e) => onPageSizeChange?.(Number(e.target.value))}
          className="input-field py-1.5 px-3 text-sm w-auto"
          aria-label="Items per page"
        >
          {pageSizeOptions.map((size) => (
            <option key={size} value={size}>
              {size} per page
            </option>
          ))}
        </select>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage === 1}
            className="btn btn-secondary btn-sm btn-icon"
            aria-label="Previous page"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <span className="text-sm text-gray-700">
            Page <span className="font-medium">{currentPage}</span> of <span className="font-medium">{totalPages}</span>
          </span>
          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="btn btn-secondary btn-sm btn-icon"
            aria-label="Next page"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}

export default { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TablePagination }