import React from "react";
import { Outlet, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  ScanText,
  User as UserIcon,
  LayoutDashboard,
  History,
} from "lucide-react";

const Layout: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50 text-gray-800 selection:bg-blue-100">
      <header className="border-b border-gray-200 sticky top-0 bg-white z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link
            to="/"
            className="flex items-center gap-3 hover:opacity-80 transition-opacity"
          >
            <div className="p-2 bg-blue-600 rounded-lg">
              <ScanText className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-xl font-bold text-gray-900">
              OCR System
            </h1>
          </Link>

          <nav className="flex items-center gap-6">
            {user ? (
              <>
                <Link
                  to="/dashboard"
                  className="flex items-center gap-2 text-gray-500 hover:text-gray-900 transition-colors"
                >
                  <LayoutDashboard className="w-4 h-4" />
                  <span>Dashboard</span>
                </Link>
                <Link
                  to="/user/history"
                  className="flex items-center gap-2 text-gray-500 hover:text-gray-900 transition-colors"
                >
                  <History className="w-4 h-4" />
                  <span>识别历史</span>
                </Link>
                <div className="flex items-center gap-2 text-gray-500">
                  <UserIcon className="w-4 h-4" />
                  <Link to="/user/profile" className="hover:text-gray-900">
                    {user.username}
                  </Link>
                </div>
              </>
            ) : (
              <Link
                to="/login"
                className="text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors"
              >
                Login
              </Link>
            )}
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;
