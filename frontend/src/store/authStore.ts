import { create } from 'zustand';

const SESSION_KEY = 'greengovrag_admin_session';

interface AuthStore {
  isAdmin: boolean;
  login: (password: string) => boolean;
  logout: () => void;
}

// Restore from sessionStorage on module load
const restoredAdmin = sessionStorage.getItem(SESSION_KEY) === 'true';

export const useAuthStore = create<AuthStore>(() => ({
  isAdmin: restoredAdmin,

  login: (password: string): boolean => {
    const adminPassword = import.meta.env.VITE_ADMIN_PASSWORD;
    if (!adminPassword || password !== adminPassword) return false;
    sessionStorage.setItem(SESSION_KEY, 'true');
    useAuthStore.setState({ isAdmin: true });
    return true;
  },

  logout: () => {
    sessionStorage.removeItem(SESSION_KEY);
    useAuthStore.setState({ isAdmin: false });
  },
}));
