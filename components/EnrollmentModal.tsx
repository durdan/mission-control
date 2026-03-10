'use client';

import { useState } from 'react';
import { FiKey, FiX, FiAlertCircle, FiCheckCircle } from 'react-icons/fi';

interface EnrollmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onEnroll: (token: string) => Promise<void>;
  currentStatus?: string;
}

export default function EnrollmentModal({ isOpen, onClose, onEnroll, currentStatus }: EnrollmentModalProps) {
  const [token, setToken] = useState('');
  const [isEnrolling, setIsEnrolling] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);
    
    if (!token.trim()) {
      setError('Please enter a gateway token');
      return;
    }

    setIsEnrolling(true);
    
    try {
      await onEnroll(token.trim());
      setSuccess(true);
      setTimeout(() => {
        onClose();
        setToken('');
        setSuccess(false);
      }, 2000);
    } catch (err: any) {
      setError(err.message || 'Failed to enroll with token');
    } finally {
      setIsEnrolling(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-secondary rounded-lg p-6 max-w-md w-full mx-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-primary flex items-center gap-2">
            <FiKey className="w-5 h-5" />
            OpenClaw Gateway Enrollment
          </h2>
          <button
            onClick={onClose}
            className="text-tertiary hover:text-primary transition-colors"
          >
            <FiX className="w-5 h-5" />
          </button>
        </div>

        {currentStatus && (
          <div className="mb-4 p-3 bg-tertiary rounded-lg">
            <p className="text-sm text-secondary">Current Status:</p>
            <p className="text-xs font-mono text-primary mt-1 break-all">
              {currentStatus}
            </p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="token" className="block text-sm font-medium text-secondary mb-2">
              Gateway Token
            </label>
            <input
              id="token"
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Enter your OpenClaw gateway token"
              className="w-full px-3 py-2 bg-primary border border-gray-700 rounded-lg text-primary placeholder-tertiary focus:outline-none focus:border-blue-500"
              disabled={isEnrolling}
            />
            <p className="text-xs text-tertiary mt-2">
              The token is used to authenticate with your OpenClaw gateway.
              You can generate a new token using: <code className="bg-tertiary px-1 rounded">openclaw gateway token --new</code>
            </p>
          </div>

          {error && (
            <div className="flex items-start gap-2 p-3 bg-red-900 bg-opacity-30 border border-red-700 rounded-lg">
              <FiAlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}

          {success && (
            <div className="flex items-start gap-2 p-3 bg-green-900 bg-opacity-30 border border-green-700 rounded-lg">
              <FiCheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-green-300">Successfully enrolled! Reconnecting...</p>
            </div>
          )}

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={isEnrolling}
              className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
                isEnrolling
                  ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              {isEnrolling ? 'Enrolling...' : 'Enroll'}
            </button>
            <button
              type="button"
              onClick={onClose}
              disabled={isEnrolling}
              className="px-4 py-2 bg-tertiary hover:bg-gray-700 text-primary rounded-lg font-medium transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>

        <div className="mt-6 pt-4 border-t border-gray-700">
          <h3 className="text-sm font-semibold text-secondary mb-2">Need Help?</h3>
          <div className="space-y-2 text-xs text-tertiary">
            <p>1. Check gateway status: <code className="bg-tertiary px-1 rounded">openclaw gateway status</code></p>
            <p>2. Generate new token: <code className="bg-tertiary px-1 rounded">openclaw gateway token --new</code></p>
            <p>3. Restart gateway: <code className="bg-tertiary px-1 rounded">openclaw gateway restart</code></p>
          </div>
        </div>
      </div>
    </div>
  );
}