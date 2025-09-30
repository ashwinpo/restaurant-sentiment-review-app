import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';

interface LayoutProps {
  children: ReactNode;
}

const Layout = ({ children }: LayoutProps) => {
  const location = useLocation();

  const getActiveTab = () => {
    const params = new URLSearchParams(location.search);
    const tab = params.get('tab');
    if (tab) return tab;
    if (location.pathname.startsWith('/review/')) return 'random_sample';
    return 'random_sample';
  };

  const activeTab = getActiveTab();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-20">
            {/* Logo and Title */}
            <div className="flex items-center space-x-4">
              <Link to="/" className="flex items-center space-x-4">
                <img 
                  src="/bloomin-logo.png" 
                  alt="Bloomin Brands" 
                  className="h-20 w-auto"
                  onError={(e) => {
                    // Fallback to JPG if PNG fails
                    e.currentTarget.src = '/bloomin-logo.jpg';
                    e.currentTarget.className = 'h-12 w-12 rounded';
                  }}
                />
                <div>
                  <h1 className="text-xl font-bold text-bloomin-red">
                    Review Validation
                  </h1>
                  <p className="text-sm text-gray-500">
                    Bloomin' Brands Sentiment Analysis
                  </p>
                </div>
              </Link>
            </div>
          </div>

          {/* Tab Navigation */}
          <nav className="flex space-x-8 -mb-px">
            <Link
              to="/?tab=random_sample"
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'random_sample'
                  ? 'border-bloomin-red text-bloomin-red'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Random Sample
            </Link>
            <Link
              to="/?tab=completed"
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'completed'
                  ? 'border-bloomin-red text-bloomin-red'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Completed
            </Link>
            <Link
              to="/?tab=recommended"
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'recommended'
                  ? 'border-bloomin-red text-bloomin-red'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Recommended
            </Link>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
};

export default Layout;
