import React from 'react'
import { cn } from '@/lib/utils'

interface LayoutProps {
  children: React.ReactNode
  className?: string
}

export function Layout({ children, className }: LayoutProps) {
  return (
    <div className={cn("flex h-screen overflow-hidden bg-background", className)}>
      {children}
    </div>
  )
}