import React, { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from 'react-query'
import { Toaster } from '@/components/ui/toaster'
import { ThemeProvider } from '@/components/theme-provider'
import { WebSocketProvider } from '@/hooks/use-websocket'
import { AuthProvider } from '@/hooks/use-auth'

// Layout Components
import { Layout } from '@/components/layout/layout'
import { Sidebar } from '@/components/layout/sidebar'
import { Header } from '@/components/layout/header'

// Pages
import { DashboardPage } from '@/pages/dashboard'
import { SignalsPage } from '@/pages/signals'
import { PortfolioPage } from '@/pages/portfolio'
import { ScreenerPage } from '@/pages/screener'
import { NewsPage } from '@/pages/news'
import { SettingsPage } from '@/pages/settings'
import { BrainPage } from '@/pages/brain'

// Global styles
import './index.css'

// Create query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60000, // 1 minute
      cacheTime: 300000, // 5 minutes
      refetchOnWindowFocus: false,
    },
  },
})

function App() {
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Initialize app
    const initializeApp = async () => {
      try {
        // Check API connection
        const response = await fetch('/api/health')
        if (response.ok) {
          console.log('✅ Trading Command Center API connected')
        } else {
          console.error('❌ Failed to connect to API')
        }
      } catch (error) {
        console.error('❌ API connection error:', error)
      } finally {
        setIsLoading(false)
      }
    }

    initializeApp()
  }, [])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold text-white">Loading Trading Command Center...</h2>
          <p className="text-gray-400 mt-2">Connecting to market data services</p>
        </div>
      </div>
    )
  }

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="dark" storageKey="tcc-theme">
        <AuthProvider>
          <WebSocketProvider>
            <Router>
              <div className="min-h-screen bg-background font-sans antialiased">
                <Layout>
                  <Sidebar />
                  <div className="flex-1 flex flex-col">
                    <Header />
                    <main className="flex-1 overflow-y-auto p-6">
                      <Routes>
                        <Route path="/" element={<DashboardPage />} />
                        <Route path="/dashboard" element={<DashboardPage />} />
                        <Route path="/signals" element={<SignalsPage />} />
                        <Route path="/portfolio" element={<PortfolioPage />} />
                        <Route path="/screener" element={<ScreenerPage />} />
                        <Route path="/news" element={<NewsPage />} />
                        <Route path="/brain" element={<BrainPage />} />
                        <Route path="/settings" element={<SettingsPage />} />
                      </Routes>
                    </main>
                  </div>
                </Layout>
              </div>
            </Router>
            <Toaster />
          </WebSocketProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

export default App