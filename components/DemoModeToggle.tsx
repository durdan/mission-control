'use client';

import React from 'react';
import { useState, useEffect } from 'react';

interface DemoModeToggleProps {
  onModeChange?: (isDemoMode: boolean) => void;
}

export default function DemoModeToggle({ onModeChange }: DemoModeToggleProps) {
  const [isDemoMode, setIsDemoMode] = useState(false);

  useEffect(() => {
    // Load saved preference from localStorage
    const savedMode = localStorage.getItem('demoMode');
    if (savedMode !== null) {
      const mode = savedMode === 'true';
      setIsDemoMode(mode);
      onModeChange?.(mode);
    }
  }, []);

  const handleToggle = () => {
    const newMode = !isDemoMode;
    setIsDemoMode(newMode);
    localStorage.setItem('demoMode', String(newMode));
    onModeChange?.(newMode);
    
    // Refresh the page to reload data
    window.location.reload();
  };

  return (
    <div className="fixed top-4 right-4 z-50 flex items-center gap-3 bg-background/95 backdrop-blur-sm border rounded-lg px-4 py-2 shadow-lg">
      {isDemoMode && (
        <span className="text-xs font-semibold text-warning bg-warning/10 px-2 py-1 rounded animate-pulse">
          DEMO MODE
        </span>
      )}
      
      <label className="flex items-center cursor-pointer">
        <span className="mr-3 text-sm font-medium">
          {isDemoMode ? 'Demo Data' : 'Live Data'}
        </span>
        <div className="relative">
          <input
            type="checkbox"
            className="sr-only peer"
            checked={!isDemoMode}
            onChange={handleToggle}
          />
          <div className="w-11 h-6 bg-gray-600 rounded-full peer peer-checked:bg-success peer-focus:ring-4 peer-focus:ring-success/20 transition-colors"></div>
          <div className="absolute top-[2px] left-[2px] bg-white w-5 h-5 rounded-full transition-transform peer-checked:translate-x-5"></div>
        </div>
      </label>

      <div className="flex items-center gap-1">
        <div className={`w-2 h-2 rounded-full ${isDemoMode ? 'bg-warning' : 'bg-success animate-pulse'}`}></div>
        <span className="text-xs text-muted-foreground">
          {isDemoMode ? 'Mock' : 'OpenClaw'}
        </span>
      </div>
    </div>
  );
}