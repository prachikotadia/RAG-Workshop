import { useState } from 'react';
import { LoginForm } from '../components/auth/LoginForm';
import { SignupForm } from '../components/auth/SignupForm';
import { HeroSection } from '../components/common/HeroSection';

export function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);

  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden">
      {/* Minimal gradient background */}
      <div className="fixed inset-0 bg-gradient-to-br from-gray-50 to-white dark:from-gray-900 dark:to-gray-950 -z-10" />
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(59,130,246,0.03),transparent_70%)] dark:bg-[radial-gradient(circle_at_50%_50%,rgba(96,165,250,0.05),transparent_70%)] -z-10" />
      
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
      <div className="flex-1 flex items-center justify-center px-4 py-6 md:py-8 relative z-10">
        <div className="w-full max-w-md animate-fade-in">
          <div className="md:hidden mb-8 text-center">
            <div className="mb-4 hover-lift">
              <div className="glass-strong dark:glass-strong backdrop-blur-xl rounded-full p-4 w-20 h-20 mx-auto flex items-center justify-center shadow-strong border-2 border-blue-200/50 dark:border-blue-700/50">
                <svg className="w-10 h-10 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
            </div>
            <h1 className="text-3xl font-bold gradient-text mb-3">
              Prachi RAG Workspace
            </h1>
            <p className="text-base text-gray-600 dark:text-gray-400 font-medium">
              {isLogin ? 'Sign in to access your AI-powered document assistant' : 'Create an account to get started'}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 shadow-soft border border-gray-200 dark:border-gray-700 rounded-2xl p-6 md:p-8">
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
