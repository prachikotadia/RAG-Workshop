import { useState } from 'react';
import { LoginForm } from '../components/auth/LoginForm';
import { SignupForm } from '../components/auth/SignupForm';
import { HeroSection } from '../components/common/HeroSection';

export function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">
      <div className="hidden md:block flex-shrink-0">
        <HeroSection
          title="Prachi RAG Workspace"
          subtitle={isLogin ? 'Sign in to access your AI-powered document assistant' : 'Create an account to get started'}
          icon={
            <svg className="w-12 h-12 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          }
        />
      </div>
      <div className="flex-1 flex items-center justify-center px-4 py-6 md:py-8">
        <div className="w-full max-w-md">
          <div className="md:hidden mb-6 text-center">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Prachi RAG Workspace
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {isLogin ? 'Sign in to access your AI-powered document assistant' : 'Create an account to get started'}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg p-6 md:p-8">
            {isLogin ? (
              <LoginForm onSwitchToSignup={() => setIsLogin(false)} />
            ) : (
              <SignupForm onSwitchToLogin={() => setIsLogin(true)} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
