import React from 'react';
import { Outlet } from 'react-router-dom';

export const PlatformLayout = () => {
  return (
    <div className="platform-layout flex">
      <aside className="w-64 min-h-screen bg-gray-900 text-white p-4">
        <h2 className="text-xl font-bold mb-8">KAVAN Platform</h2>
        <nav>
          <ul className="space-y-4">
            <li>Dashboard</li>
            <li>Tenants</li>
            <li>Platform Users</li>
            <li>Marketplace</li>
            <li>Deployments</li>
            <li>Monitoring</li>
            <li>Operations</li>
            <li>Settings</li>
          </ul>
        </nav>
      </aside>
      <main className="flex-1 p-8">
        <Outlet />
      </main>
    </div>
  );
};
