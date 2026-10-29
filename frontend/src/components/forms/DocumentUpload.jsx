import { useId, useRef, useState } from 'react'
import { Upload } from 'lucide-react'
import { Button } from '../ui/Button'
import { formatApiError } from '../../services/api'

// Matches backend common/uploads.py DOCUMENT_EXTENSIONS and MAX_UPLOAD_BYTES.
export const DOCUMENT_ACCEPT = '.jpg,.jpeg,.png,.webp,.bmp,.pdf'
const MAX_BYTES = 25 * 1024 * 1024
const ALLOWED = /\.(jpe?g|png|webp|bmp|pdf)$/i

/**
 * Compact "choose type + file + upload" control.
 * onUpload(formData) must return a promise; formData has file, original_name and document_type.
 */
export function DocumentUpload({ documentTypes, onUpload, onUploaded }) {
  const inputId = useId()
  const inputRef = useRef(null)
  const [documentType, setDocumentType] = useState(documentTypes[0]?.value || 'other')
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  const handleFile = (event) => {
    const selected = event.target.files?.[0] || null
    setError('')
    if (selected && !ALLOWED.test(selected.name)) {
      setError('Only JPG, PNG, WEBP, BMP or PDF files can be uploaded.')
      setFile(null)
      event.target.value = ''
      return
    }
    if (selected && selected.size > MAX_BYTES) {
      setError('The file is larger than 25 MB.')
      setFile(null)
      event.target.value = ''
      return
    }
    setFile(selected)
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('original_name', file.name)
      formData.append('document_type', documentType)
      const created = await onUpload(formData)
      setFile(null)
      if (inputRef.current) inputRef.current.value = ''
      onUploaded?.(created)
    } catch (err) {
      setError(formatApiError(err, 'The file could not be uploaded.'))
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <select
          className="input-field sm:w-48"
          value={documentType}
          onChange={(event) => setDocumentType(event.target.value)}
          aria-label="Document type"
        >
          {documentTypes.map((type) => (
            <option key={type.value} value={type.value}>{type.label}</option>
          ))}
        </select>
        <label htmlFor={inputId} className="sr-only">Choose a file</label>
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept={DOCUMENT_ACCEPT}
          onChange={handleFile}
          className="min-w-0 flex-1 text-sm text-gray-600 file:mr-3 file:rounded-lg file:border-0 file:bg-gray-100 file:px-3 file:py-2 file:text-sm file:font-medium"
        />
        <Button type="button" variant="outline" size="sm" onClick={handleUpload} loading={uploading} disabled={!file || uploading}>
          <Upload className="w-4 h-4 mr-2" aria-hidden="true" />
          Upload
        </Button>
      </div>
      <p className="text-xs text-gray-500">JPG, PNG, WEBP, BMP or PDF, up to 25 MB.</p>
      {error && <p className="text-sm text-red-700" role="alert">{error}</p>}
    </div>
  )
}

export default DocumentUpload
