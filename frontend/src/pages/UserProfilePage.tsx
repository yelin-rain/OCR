import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { message } from "antd";

import { httpClient } from "../providers/http_provider";
import { useAuth } from "../context/AuthContext";

const UserProfilePage: React.FC = () => {
  const { user, logout, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState(user?.username ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [successText, setSuccessText] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const isDirty = useMemo(() => {
    return (
      username !== (user?.username ?? "") ||
      email !== (user?.email ?? "") ||
      currentPassword.length > 0 ||
      newPassword.length > 0
    );
  }, [username, email, currentPassword, newPassword, user?.username, user?.email]);

  useEffect(() => {
    const beforeUnload = (e: BeforeUnloadEvent) => {
      if (!isDirty) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", beforeUnload);
    return () => window.removeEventListener("beforeunload", beforeUnload);
  }, [isDirty]);

  const saveProfile = async () => {
    setError("");
    setSuccessText("");
    try {
      setSaving(true);
      await httpClient.put("/auth/me", {
        username,
        email,
        current_password: currentPassword || undefined,
        new_password: newPassword || undefined,
      });
      await refreshUser();
      setCurrentPassword("");
      setNewPassword("");
      setSuccessText("用户信息更新成功");
      message.success("用户信息已保存");
    } catch (e: any) {
      const detail = e?.response?.data?.detail || "更新失败";
      setError(detail);
      message.error(detail);
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    if (isDirty && !window.confirm("你有未保存的修改，确定要退出登录吗？")) {
      return;
    }
    logout();
    navigate("/login");
  };

  return (
    <div className="max-w-2xl mx-auto bg-white border border-gray-200 rounded-xl p-6 space-y-5">
      <h2 className="text-2xl font-semibold text-gray-900">用户信息管理</h2>
      <p className="text-sm text-gray-500">在这里查看和修改你的个人信息。</p>

      {error && <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded">{error}</div>}
      {successText && <div className="bg-green-50 border border-green-200 text-green-700 p-3 rounded">{successText}</div>}

      <div className="grid grid-cols-1 gap-4">
        <div>
          <label className="block text-sm text-gray-600 mb-1">用户名</label>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2"
          />
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">邮箱</label>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2"
          />
        </div>
      </div>

      <div className="border-t border-gray-200 pt-4 space-y-4">
        <h3 className="text-base font-medium text-gray-800">修改密码（可选）</h3>
        <div>
          <label className="block text-sm text-gray-600 mb-1">当前密码</label>
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2"
          />
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">新密码</label>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2"
          />
        </div>
      </div>

      <div className="flex gap-3">
        <button
          onClick={saveProfile}
          disabled={saving}
          className="px-4 py-2 rounded bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50"
        >
          {saving ? "保存中..." : "保存修改"}
        </button>
        <button
          onClick={handleLogout}
          className="px-4 py-2 rounded bg-red-600 hover:bg-red-700 text-white"
        >
          退出登录
        </button>
      </div>
    </div>
  );
};

export default UserProfilePage;
