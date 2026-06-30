import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface AuthState {
  isAuthenticated: boolean;
  user: any | null;
  tenant: any | null;
  platformRole: string | null;
  permissions: string[];
}

const initialState: AuthState = {
  isAuthenticated: false,
  user: null,
  tenant: null,
  platformRole: null,
  permissions: [],
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setAuth: (state, action: PayloadAction<Partial<AuthState>>) => {
      return { ...state, ...action.payload, isAuthenticated: true };
    },
    logout: () => initialState,
  },
});

export const { setAuth, logout } = authSlice.actions;
export default authSlice.reducer;
