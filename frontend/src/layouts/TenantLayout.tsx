import React from 'react';
import { Outlet } from 'react-router-dom';

export const TenantLayout = () => {
  return (
    <div className="tenant-layout flex">
      <aside className="w-64 min-h-screen bg-indigo-900 text-white p-4">
        <h2 className="text-xl font-bold mb-8">Tenant Dashboard</h2>
        <nav>
          <ul className="space-y-4">
            <li>Dashboard</li>
            <li>Installed Products</li>
            <li>Users</li>
            <li>Roles</li>
            <li>Security</li>
            <li>Reports</li>
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
