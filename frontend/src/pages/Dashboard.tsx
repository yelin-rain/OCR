import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { FileText, Clock, Trash2, Eye } from 'lucide-react';

interface Task {
    id: number;
    filename: string;
    status: string;
    created_at: string;
    completed_at: string | null;
    result: string | null;
    file_url: string | null;
}

const Dashboard: React.FC = () => {
    const { user } = useAuth();
    const [tasks, setTasks] = useState<Task[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchTasks = async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await axios.get('http://localhost:8000/ocr/tasks', {
                headers: { Authorization: `Bearer ${token}` }
            });
            setTasks(response.data);
        } catch (error) {
            console.error("Failed to fetch tasks", error);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm('Are you sure you want to delete this task?')) return;
        try {
            const token = localStorage.getItem('token');
            await axios.delete(`http://localhost:8000/ocr/task/${id}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setTasks(tasks.filter(t => t.id !== id));
        } catch (error) {
            console.error("Failed to delete task", error);
        }
    };

    useEffect(() => {
        fetchTasks();
        const interval = setInterval(fetchTasks, 3000); // Poll every 3 seconds
        return () => clearInterval(interval);
    }, []);

    if (loading) return <div className="text-center py-20 text-gray-500">Loading tasks...</div>;

    return (
        <div className="space-y-6">
            <header className="flex justify-between items-end pb-6 border-b border-gray-800">
                <div>
                    <h2 className="text-3xl font-bold text-white">Welcome back, {user?.username}</h2>
                    <p className="text-gray-500 mt-2">Manage your recent OCR operations</p>
                </div>
            </header>

            {tasks.length === 0 ? (
                <div className="text-center py-20 bg-gray-900/50 rounded-xl border border-gray-800">
                    <FileText className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                    <h3 className="text-xl font-medium text-gray-300">No tasks found</h3>
                    <p className="text-gray-500 mt-2">Upload a document to get started</p>
                </div>
            ) : (
                <div className="grid gap-4">
                    {tasks.map((task) => (
                        <div key={task.id} className="bg-gray-900 p-4 rounded-xl border border-gray-800 flex items-center justify-between hover:border-gray-700 transition-colors">
                            <div className="flex items-center gap-4">
                                <div className={`p-3 rounded-lg ${task.status === 'COMPLETED' ? 'bg-green-500/10 text-green-500' : 'bg-blue-500/10 text-blue-500'}`}>
                                    <FileText className="w-6 h-6" />
                                </div>
                                <div>
                                    <h4 className="font-medium text-white">{task.filename}</h4>
                                    <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                                        <span className="flex items-center gap-1">
                                            <Clock className="w-3 h-3" />
                                            {new Date(task.created_at).toLocaleDateString()}
                                        </span>
                                        <span className={`px-2 py-0.5 rounded-full text-xs ${task.status === 'COMPLETED' ? 'bg-green-500/10 text-green-500' :
                                            task.status === 'FAILED' ? 'bg-red-500/10 text-red-500' :
                                                'bg-blue-500/10 text-blue-500'
                                            }`}>
                                            {task.status}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center gap-2">
                                {task.file_url && (
                                    <a href={task.file_url} target="_blank" rel="noreferrer" className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors" title="View Source">
                                        <Eye className="w-4 h-4" />
                                    </a>
                                )}
                                <button onClick={() => handleDelete(task.id)} className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors" title="Delete">
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default Dashboard;
