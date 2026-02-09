import React from 'react';
import { CheckCircle2, Clock, XCircle, FileText, Image as ImageIcon, Trash2 } from 'lucide-react';
import { cn } from '../utils/utils';
import type { Task } from '../models/task';

interface TaskListProps {
    tasks: Task[];
    selectedTask: Task | null;
    onSelectTask: (task: Task) => void;
    onStopTask: (taskId: number) => void;
    onDeleteTask: (taskId: number) => void;
}

export const TaskList: React.FC<TaskListProps> = ({
    tasks,
    selectedTask,
    onSelectTask,
    onStopTask,
    onDeleteTask
}) => {

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'COMPLETED': return <CheckCircle2 className="w-5 h-5 text-green-400" />;
            case 'FAILED': return <XCircle className="w-5 h-5 text-red-400" />;
            default: return <Clock className="w-5 h-5 text-yellow-400 animate-pulse" />;
        }
    };

    // Parse result JSON safely
    const renderResult = (resultStr: string | null) => {
        if (!resultStr) return null;
        try {
            const data = JSON.parse(resultStr);

            // Format 1: Baidu Cloud Standard (words_result)
            if (data.words_result) {
                return (
                    <div className="space-y-2">
                        {data.words_result.map((item: { words: string }, idx: number) => (
                            <div key={idx} className="bg-gray-800/50 p-2 rounded border border-gray-700 flex justify-between items-start">
                                <span className="text-gray-200">{item.words}</span>
                            </div>
                        ))}
                    </div>
                );
            }

            // Format 2: AI Studio PaddleOCR-VL (layoutParsingResults -> markdown -> text)
            const aiStudioText = data.result?.layoutParsingResults?.[0]?.markdown?.text;
            if (aiStudioText) {
                return (
                    <div className="bg-gray-800/50 p-4 rounded border border-gray-700 whitespace-pre-wrap text-gray-200 font-mono text-sm">
                        {aiStudioText}
                    </div>
                );
            }

            // Fallback for raw structure (e.g. if everything fails)
            return (
                <div className="bg-gray-900 p-4 rounded border border-red-500/20 text-xs text-gray-500 overflow-x-auto">
                    <code>{JSON.stringify(data, null, 2)}</code>
                </div>
            );
        } catch {
            return <p className="text-red-400">解析结果出错</p>;
        }
    };


    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[600px]">
            {/* List */}
            <div className="col-span-1 bg-gray-900/50 rounded-xl border border-gray-700 overflow-hidden flex flex-col">
                <div className="p-4 border-b border-gray-700 bg-gray-900/80 backdrop-blur">
                    <h2 className="text-lg font-semibold text-gray-100 flex items-center gap-2">
                        <FileText className="w-5 h-5 text-blue-400" />
                        历史任务
                    </h2>
                </div>
                <div className="flex-1 overflow-y-auto p-2 space-y-2">
                    {tasks.map((task) => (
                        <div
                            key={task.id}
                            onClick={() => onSelectTask(task)}
                            className={cn(
                                "p-3 rounded-lg cursor-pointer transition-all hover:bg-gray-800 border flex items-center justify-between group",
                                selectedTask?.id === task.id
                                    ? "bg-gray-800 border-blue-500/50 shadow-lg shadow-blue-500/10"
                                    : "bg-gray-900 border-transparent hover:border-gray-700"
                            )}
                        >
                            <div className="flex items-center gap-3 overflow-hidden">
                                <div className="p-2 rounded-lg bg-gray-950">
                                    <ImageIcon className="w-5 h-5 text-gray-400" />
                                </div>
                                <div className="min-w-0">
                                    <p className="font-medium text-gray-200 truncate">{task.filename}</p>
                                    <p className="text-xs text-gray-500">{new Date(task.created_at).toLocaleTimeString()}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                {(task.status === 'PROCESSING' || task.status === 'PENDING') && (
                                    <button
                                        onClick={(e) => { e.stopPropagation(); onStopTask(task.id); }}
                                        className="p-1 hover:bg-red-500/20 rounded text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                                        title="停止任务"
                                    >
                                        <XCircle className="w-4 h-4" />
                                    </button>
                                )}
                                <button
                                    onClick={(e) => { e.stopPropagation(); onDeleteTask(task.id); }}
                                    className="p-1 hover:bg-red-500/20 rounded text-gray-500 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                                    title="删除任务"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                                {getStatusIcon(task.status)}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Detail View */}
            <div className="col-span-1 lg:col-span-2 bg-gray-900/50 rounded-xl border border-gray-700 overflow-hidden flex flex-col">
                {selectedTask ? (
                    <div className="flex flex-col h-full">
                        <div className="p-4 border-b border-gray-700 bg-gray-900/80 backdrop-blur flex justify-between items-center">
                            <h2 className="text-lg font-semibold text-gray-100">任务 #{selectedTask.id}</h2>
                            <span className={cn(
                                "px-3 py-1 rounded-full text-xs font-medium border",
                                selectedTask.status === 'COMPLETED' ? "bg-green-500/10 text-green-400 border-green-500/20" :
                                    selectedTask.status === 'FAILED' ? "bg-red-500/10 text-red-400 border-red-500/20" :
                                        "bg-yellow-500/10 text-yellow-400 border-yellow-500/20"
                            )}>
                                {selectedTask.status}
                            </span>
                        </div>
                        <div className="flex-1 overflow-y-auto p-6">
                            <div className="grid grid-cols-1 gap-6">
                                {/* Image */}
                                {selectedTask.file_url ? (
                                    <div className="rounded-xl overflow-hidden border border-gray-700 bg-gray-950/50 p-2 flex justify-center">
                                        <img src={selectedTask.file_url} alt="Task" className="h-full w-auto object-contain max-h-[250px]" />
                                    </div>
                                ) : (
                                    <div className="rounded-xl border border-gray-700 bg-gray-950/50 h-64 flex flex-col items-center justify-center text-gray-500 gap-3">
                                        <ImageIcon className="w-12 h-12 opacity-20" />
                                        <p className="text-sm">预览图片不可用</p>
                                    </div>
                                )}

                                {/* Result */}
                                <div>
                                    <h3 className="text-sm font-medium text-gray-400 mb-3 uppercase tracking-wider">识别结果</h3>
                                    {selectedTask.result ? (
                                        renderResult(selectedTask.result)
                                    ) : (
                                        <div className="text-gray-500 italic">暂无结果...</div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-gray-500 gap-4">
                        <FileText className="w-16 h-16 opacity-20" />
                        <p>请从左侧列表选择一个任务</p>
                    </div>
                )}
            </div>
        </div>
    );
};
