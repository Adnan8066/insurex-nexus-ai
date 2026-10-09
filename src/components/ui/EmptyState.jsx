import { clsx } from 'clsx'

export function EmptyState({
  icon,
  title = 'No Data Available',
  description = 'There are no items to display at the moment.',
  action,
  className = '',
  illustration,
}) {
  return (
    <div className={clsx('flex flex-col items-center justify-center text-center py-12 px-4', className)}>
      {illustration ? (
        <div className="mb-6">{illustration}</div>
      ) : icon ? (
        <div className="mb-6 text-gray-300" aria-hidden="true">
          {icon}
        </div>
      ) : (
        <svg
          className="w-16 h-16 text-gray-300 mb-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
      )}
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-500 mb-6 max-w-md">{description}</p>
      {action && (
        <div className="mt-4">{action}</div>
      )}
    </div>
  )
}

export function EmptyStateTable({ columns = 1, ...props }) {
  return (
    <tbody>
      <tr>
        <td colSpan={columns} className="py-12 px-4">
          <EmptyState {...props} />
        </td>
      </tr>
    </tbody>
  )
}

export default { EmptyState, EmptyStateTable }