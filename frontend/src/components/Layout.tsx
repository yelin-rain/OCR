import React from 'react';
import { Outlet, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ScanText, Github, LogOut, User as UserIcon, LayoutDashboard } from 'lucide-react';

const Layout: React.FC = () => {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    return (
        <div className="min-h-screen bg-[#0a0a0a] text-gray-100 selection:bg-blue-500/30">
            {/* Background Gradients */}
            <div className="fixed inset-0 pointer-events-none -z-10">
                <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-500/10 rounded-full blur-[128px]" />
                <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-500/10 rounded-full blur-[128px]" />
            </div>

            <header className="border-b border-gray-800 sticky top-0 bg-[#0a0a0a]/80 backdrop-blur-md z-50">
                <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                    <Link to="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
                        <div className="p-2 bg-blue-600 rounded-lg shadow-lg shadow-blue-600/20">
                            <ScanText className="w-6 h-6 text-white" />
                        </div>
                        <h1 className="text-xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
                            OCR System
                        </h1>
                    </Link>

                    <nav className="flex items-center gap-6">
                        {user ? (
                            <>
                                <Link to="/dashboard" className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors">
                                    <LayoutDashboard className="w-4 h-4" />
                                    <span>Dashboard</span>
                                </Link>
                                <div className="flex items-center gap-2 text-gray-400">
                                    <UserIcon className="w-4 h-4" />
                                    <span>{user.username}</span>
                                </div>
                                <button onClick={handleLogout} className="p-2 text-gray-400 hover:text-red-400 transition-colors" title="Logout">
                                    <LogOut className="w-5 h-5" />
                                </button>
                            </>
                        ) : (
                            <Link to="/login" className="text-sm font-medium text-blue-400 hover:text-blue-300 transition-colors">
                                Login
                            </Link>
                        )}
                        <a href="#" className="text-gray-400 hover:text-white transition-colors">
                            <Github className="w-5 h-5" />
                        </a>
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
