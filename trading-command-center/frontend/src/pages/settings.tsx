import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Configure your trading preferences and notifications
        </p>
      </div>

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Trading Preferences</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-muted-foreground">
              Configure your risk tolerance, preferred markets, and trading parameters.
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Notifications</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-muted-foreground">
              Set up alerts for trading signals, price movements, and market events.
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>API Configuration</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-muted-foreground">
              Manage your API keys and data source connections.
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}