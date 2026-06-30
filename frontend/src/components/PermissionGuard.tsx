import React from 'react';
import { useSelector } from 'react-redux';
import { Navigate } from 'react-router-dom';
import { RootState } from '../store';

interface Props {
  permission: string;
  children: React.ReactNode;
}

export const PermissionGuard: React.FC<Props> = ({ permission, children }) => {
  const permissions = useSelector((state: RootState) => state.auth.permissions);
  const platformRole = useSelector((state: RootState) => state.auth.platformRole);

  // Implicit Super Admin override
  if (platformRole === 'SUPER_ADMIN') {
    return <>{children}</>;
  }

  // Exact permission match
  if (permissions.includes(permission)) {
    return <>{children}</>;
  }

  // Denied
  return <Navigate to="/403" replace />;
};
