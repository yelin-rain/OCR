import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { httpClient } from "../providers/http_provider";
import { useAuth } from "../context/AuthContext";
import { Lock, User } from "lucide-react";

const LoginPage: React.FC = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const params = new URLSearchParams();
      params.append("username", username);
      params.append("password", password);

      const response = await httpClient.post("/auth/token", params, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      // Wait for user context to update
      await login(response.data.access_token, response.data.refresh_token);
      navigate("/dashboard");
    } catch (err: any) {
      setError("Login failed. Please check your credentials.");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 text-gray-900 px-4">
      <div className="bg-white p-8 rounded-xl shadow-sm w-full max-w-md border border-gray-200">
        <h2 className="text-3xl font-bold mb-2 text-center text-gray-900">
          Login
        </h2>
        <p className="text-center text-sm text-gray-500 mb-6">使用你的账号继续</p>
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded mb-4 text-sm">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">
              Username
            </label>
            <div className="relative">
              <User className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-white border border-gray-300 rounded-lg py-2 pl-10 pr-4 focus:outline-none focus:border-blue-500 transition-colors"
                required
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-white border border-gray-300 rounded-lg py-2 pl-10 pr-4 focus:outline-none focus:border-blue-500 transition-colors"
                required
              />
            </div>
          </div>
          <button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 px-4 rounded-lg transition-colors"
          >
            Sign In
          </button>
        </form>
        <div className="mt-4 text-center text-sm text-gray-500">
          Don't have an account?{" "}
          <Link to="/register" className="text-blue-600 hover:underline">
            Register
          </Link>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
