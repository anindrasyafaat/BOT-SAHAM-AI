import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { 
  Home, 
  TrendingUp, 
  Briefcase, 
  Search, 
  Newspaper, 
  Settings,
  Activity,
  BarChart3,
  Brain,
  Sparkles
} from 'lucide-react'

const sidebarItems = [
  {
    title: 'Dashboard',
    icon: Home,
    href: '/dashboard',
    description: 'Market overview & real-time data'
  },
  {
    title: 'Signals',
    icon: TrendingUp,
    href: '/signals',
    description: 'AI trading signals & alerts'
  },
  {
    title: 'AI Brain',
    icon: Brain,
    href: '/brain',
    description: 'Strategi yang belajar sendiri'
  },
  {
    title: 'Generate',
    icon: Sparkles,
    href: '/generate',
    description: 'Kerangka berpikir & alternatif'
  },
  {
    title: 'Portfolio',
    icon: Briefcase,
    href: '/portfolio',
    description: 'Track your positions & P&L'
  },
  {
    title: 'Screener',
    icon: Search,
    href: '/screener',
    description: 'Find trading opportunities'
  },
  {
    title: 'News',
    icon: Newspaper,
    href: '/news',
    description: 'Market news & sentiment'
  },
  {
    title: 'Settings',
    icon: Settings,
    href: '/settings',
    description: 'Configure your preferences'
  }
]

export function Sidebar() {
  const location = useLocation()
  const [isCollapsed, setIsCollapsed] = React.useState(false)

  return (
    <div className={cn(
      "flex flex-col bg-card border-r transition-all duration-300",
      isCollapsed ? "w-16" : "w-64"
    )}>
      {/* Logo */}
      <div className="flex items-center justify-between p-4 border-b">
        {!isCollapsed && (
          <div className="flex items-center space-x-2">
            <Activity className="h-6 w-6 text-primary" />
            <span className="font-bold text-lg">TCC</span>
          </div>
        )}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1 rounded hover:bg-accent"
        >
          <BarChart3 className="h-4 w-4" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
        {sidebarItems.map((item) => {
          const isActive = location.pathname === item.href
          const Icon = item.icon
          
          return (
            <Link
              key={item.href}
              to={item.href}
              className={cn(
                "flex items-center space-x-3 p-3 rounded-lg text-sm font-medium transition-colors",
                "hover:bg-accent hover:text-accent-foreground",
                isActive && "bg-primary text-primary-foreground",
                isCollapsed && "justify-center"
              )}
              title={isCollapsed ? item.title : undefined}
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              {!isCollapsed && (
                <div className="flex flex-col">
                  <span>{item.title}</span>
                  <span className="text-xs text-muted-foreground">
                    {item.description}
                  </span>
                </div>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Status */}
      <div className="p-4 border-t">
        <div className={cn(
          "flex items-center space-x-2",
          isCollapsed && "justify-center"
        )}>
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          {!isCollapsed && (
            <span className="text-xs text-muted-foreground">Live</span>
          )}
        </div>
      </div>
    </div>
  )
}